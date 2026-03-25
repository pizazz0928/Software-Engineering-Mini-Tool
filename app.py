from __future__ import annotations

import ast
import json
import logging
import os
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

MAX_INPUT_LENGTH = 5000
COMPOSITE_TYPES = {"Dict", "List", "Tuple", "Set"}


def type_name(value: Any) -> str:
    if value is None:
        return "None"
    if isinstance(value, bool):
        return "Boolean"
    if isinstance(value, int):
        return "Integer"
    if isinstance(value, float):
        return "Float"
    if isinstance(value, str):
        return "String"
    if isinstance(value, dict):
        return "Dict"
    if isinstance(value, list):
        return "List"
    if isinstance(value, tuple):
        return "Tuple"
    if isinstance(value, set):
        return "Set"
    return type(value).__name__.capitalize()


def normalize_user_input(raw_value: str) -> tuple[str, list[str]]:
    """
    Normalize punctuation and whitespace so mildly malformed input is easier to parse.
    """
    normalized = raw_value.replace("\r\n", "\n").replace("\r", "\n").strip()
    replacements = {
        "“": '"',
        "”": '"',
        "‘": "'",
        "’": "'",
        "，": ",",
        "：": ":",
        "；": ";",
        "（": "(",
        "）": ")",
        "【": "[",
        "】": "]",
        "｛": "{",
        "｝": "}",
    }
    notes: list[str] = []

    updated = normalized
    for source, target in replacements.items():
        updated = updated.replace(source, target)

    if updated != normalized:
        notes.append("Normalized quotes or punctuation in user input")

    cleaned = "".join(ch for ch in updated if ch not in {"\u200b", "\ufeff"})
    if cleaned != updated:
        notes.append("Removed invisible characters from user input")

    return cleaned, notes


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

    bracket_pairs = {"{": "}", "[": "]", "(": ")"}
    for opening, closing in bracket_pairs.items():
        if value.count(opening) != value.count(closing):
            return "String", var_value, "Input looks malformed: unmatched brackets"

    return "String", var_value, None


def build_type_details(value: Any, parse_nested_strings: bool = True) -> dict[str, Any]:
    """
    Recursively describe composite values and infer nested member types.
    """
    if isinstance(value, str) and parse_nested_strings:
        inferred_type, parsed_value, warning = determine_env_var_type(value)
        details: dict[str, Any] = {
            "type": inferred_type,
            "value": parsed_value,
        }
        if warning:
            details["note"] = warning
        if inferred_type in COMPOSITE_TYPES:
            nested = build_type_details(parsed_value, parse_nested_strings=True)
            if "fields" in nested:
                details["fields"] = nested["fields"]
            if "items" in nested:
                details["items"] = nested["items"]
        return details

    current_type = type_name(value)
    details = {"type": current_type}

    if isinstance(value, dict):
        details["fields"] = {
            str(key): build_type_details(item, parse_nested_strings=True)
            for key, item in value.items()
        }
        details["value"] = value
        return details

    if isinstance(value, (list, tuple, set)):
        items = list(value) if not isinstance(value, set) else sorted(value, key=repr)
        details["items"] = [build_type_details(item, parse_nested_strings=True) for item in items]
        details["value"] = list(value) if not isinstance(value, tuple) else list(value)
        return details

    details["value"] = value
    return details


def to_json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): to_json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_json_safe(item) for item in value]
    if isinstance(value, set):
        return [to_json_safe(item) for item in sorted(value, key=repr)]
    return value


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
        if not isinstance(raw_value, str):
            return jsonify({"error": "'variable_value' must be a string"}), 400

        if len(raw_value) > MAX_INPUT_LENGTH:
            return jsonify({"error": f"Input is too long. Limit is {MAX_INPUT_LENGTH} characters"}), 400

        normalized_input, normalization_notes = normalize_user_input(raw_value)
        inferred_type, parsed_value, warning = determine_env_var_type(normalized_input)
        type_details = build_type_details(parsed_value, parse_nested_strings=True)

        response = {
            "original_input": raw_value,
            "normalized_input": normalized_input,
            "inferred_type": inferred_type,
            "parsed_value": to_json_safe(parsed_value),
            "type_details": to_json_safe(type_details),
        }
        warnings = [*normalization_notes]
        if warning:
            warnings.append(warning)
        if warnings:
            response["warning"] = " | ".join(warnings)

        return jsonify(response), 200
    except Exception:
        logging.exception("Unexpected error in /api/analyze")
        return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    debug_enabled = os.getenv("FLASK_DEBUG", "0").lower() in {"1", "true", "yes", "on"}
    app.run(host="0.0.0.0", port=5001, debug=debug_enabled)
