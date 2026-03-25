from __future__ import annotations

import ast
import json
import logging
import operator
from typing import Any

from flask import Flask, jsonify, render_template, request


app = Flask(__name__, static_folder="static", template_folder="templates")
logging.basicConfig(level=logging.INFO)


ALLOWED_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

ALLOWED_UNARYOPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def safe_eval_expr(expr: str) -> int | float:
    """
    Evaluate a simple arithmetic expression made of numbers only.
    Function calls, variables, attributes, and other AST nodes are rejected.
    """
    node = ast.parse(expr, mode="eval")

    def _eval(current: ast.AST) -> int | float:
        if isinstance(current, ast.Expression):
            return _eval(current.body)

        if isinstance(current, ast.Constant) and isinstance(current.value, (int, float)):
            return current.value

        if isinstance(current, ast.UnaryOp) and type(current.op) in ALLOWED_UNARYOPS:
            return ALLOWED_UNARYOPS[type(current.op)](_eval(current.operand))

        if isinstance(current, ast.BinOp) and type(current.op) in ALLOWED_BINOPS:
            left = _eval(current.left)
            right = _eval(current.right)
            return ALLOWED_BINOPS[type(current.op)](left, right)

        raise ValueError("Unsupported expression")

    return _eval(node)


def determine_env_var_type(var_value: str) -> tuple[str, Any, str | None]:
    """
    Infer the most likely runtime type from a string input.
    """
    if not isinstance(var_value, str) or not var_value.strip():
        return "Empty/None", None, "Empty input"

    value = var_value.strip()
    lowered = value.lower()

    try:
        int_value = int(value)
        return "Integer", int_value, None
    except ValueError:
        pass

    try:
        float_value = float(value)
        return "Float", float_value, None
    except ValueError:
        pass

    if lowered in ("true", "yes", "on"):
        return "Boolean", True, None
    if lowered in ("false", "no", "off"):
        return "Boolean", False, None

    try:
        expr_value = safe_eval_expr(value)
        inferred_type = "Float" if isinstance(expr_value, float) else "Integer"
        return inferred_type, expr_value, "Evaluated as arithmetic expression"
    except Exception:
        pass

    try:
        json_value = json.loads(value)
        return type(json_value).__name__.capitalize(), json_value, "Parsed as JSON"
    except (ValueError, TypeError):
        pass

    try:
        literal_value = ast.literal_eval(value)
        return (
            type(literal_value).__name__.capitalize(),
            literal_value,
            "Parsed with ast.literal_eval",
        )
    except (ValueError, SyntaxError):
        pass

    return "String", var_value, None


@app.route("/")
def index() -> str:
    return render_template("index.html")


@app.route("/api/analyze", methods=["POST"])
def analyze_variable():
    try:
        data = request.get_json(silent=True)
        if not data or "variable_value" not in data:
            return jsonify({"error": "Missing 'variable_value' in request"}), 400

        raw_value = data["variable_value"]
        inferred_type, parsed_value, warning = determine_env_var_type(raw_value)

        response = {
            "original_input": raw_value,
            "inferred_type": inferred_type,
            "parsed_value": parsed_value,
        }
        if warning:
            response["warning"] = warning

        return jsonify(response), 200
    except Exception:
        logging.exception("Unexpected error in /api/analyze")
        return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
