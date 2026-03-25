const form = document.getElementById("analyzer-form");
const input = document.getElementById("variable-input");
const fillExampleButton = document.getElementById("fill-example");

const statusBadge = document.getElementById("status-badge");
const resultType = document.getElementById("result-type");
const resultValue = document.getElementById("result-value");
const resultInput = document.getElementById("result-input");
const resultWarning = document.getElementById("result-warning");

const exampleValue = '{"enabled": true, "port": 5001, "rate": 0.75}';

function setStatus(text, kind = "") {
    statusBadge.textContent = text;
    statusBadge.className = `status-badge${kind ? ` ${kind}` : ""}`;
}

function renderJson(value) {
    if (typeof value === "string") {
        return value;
    }

    try {
        return JSON.stringify(value, null, 2);
    } catch (error) {
        return String(value);
    }
}

fillExampleButton.addEventListener("click", () => {
    input.value = exampleValue;
});

form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const variableValue = input.value.trim();
    if (!variableValue) {
        setStatus("Input required", "error");
        return;
    }

    setStatus("Analyzing");
    resultType.textContent = "-";
    resultValue.textContent = "-";
    resultInput.textContent = variableValue;
    resultWarning.textContent = "-";

    try {
        const response = await fetch("/api/analyze", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ variable_value: variableValue }),
        });

        const payload = await response.json();
        if (!response.ok) {
            throw new Error(payload.error || "Request failed");
        }

        resultType.textContent = payload.inferred_type ?? "-";
        resultValue.textContent = renderJson(payload.parsed_value);
        resultInput.textContent = payload.original_input ?? "-";
        resultWarning.textContent = payload.warning ?? "No additional note";
        setStatus("Completed", "success");
    } catch (error) {
        resultType.textContent = "Error";
        resultValue.textContent = "-";
        resultWarning.textContent = error.message;
        setStatus("Failed", "error");
    }
});
