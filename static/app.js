const form = document.getElementById("analyzer-form");
const input = document.getElementById("variable-input");
const fillExampleButton = document.getElementById("fill-example");
const reflectionForm = document.getElementById("reflection-form");
const codeInput = document.getElementById("code-input");
const variableNameInput = document.getElementById("variable-name-input");
const fillCodeExampleButton = document.getElementById("fill-code-example");

const statusBadge = document.getElementById("status-badge");
const resultType = document.getElementById("result-type");
const resultValue = document.getElementById("result-value");
const resultInput = document.getElementById("result-input");
const resultNormalizedInput = document.getElementById("result-normalized-input");
const resultWarning = document.getElementById("result-warning");
const resultDetails = document.getElementById("result-details");
const reflectionStatusBadge = document.getElementById("reflection-status-badge");
const reflectionVariableName = document.getElementById("reflection-variable-name");
const reflectionType = document.getElementById("reflection-type");
const reflectionValue = document.getElementById("reflection-value");
const reflectionDetails = document.getElementById("reflection-details");
const reflectionError = document.getElementById("reflection-error");

const exampleValue = '{"enabled":"true","port":"5001","rate":"0.75","servers":["1","2","3"]}';
const exampleCode = `port = "5001"
enabled = "true"
config = {
    "port": port,
    "enabled": enabled,
    "servers": ["1", "2", "3"]
}`;

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

fillCodeExampleButton.addEventListener("click", () => {
    codeInput.value = exampleCode;
    variableNameInput.value = "config";
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
    resultNormalizedInput.textContent = "-";
    resultWarning.textContent = "-";
    resultDetails.textContent = "-";

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
        resultNormalizedInput.textContent = payload.normalized_input ?? "-";
        resultWarning.textContent = payload.warning ?? "No additional note";
        resultDetails.textContent = renderJson(payload.type_details);
        setStatus("Completed", "success");
    } catch (error) {
        resultType.textContent = "Error";
        resultValue.textContent = "-";
        resultNormalizedInput.textContent = "-";
        resultWarning.textContent = error.message;
        resultDetails.textContent = "-";
        setStatus("Failed", "error");
    }
});

reflectionForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const code = codeInput.value.trim();
    const variableName = variableNameInput.value.trim();
    if (!code || !variableName) {
        setStatus("Input required", "error");
        reflectionStatusBadge.textContent = "Input required";
        reflectionStatusBadge.className = "status-badge error";
        return;
    }

    reflectionStatusBadge.textContent = "Analyzing";
    reflectionStatusBadge.className = "status-badge";
    reflectionVariableName.textContent = variableName;
    reflectionType.textContent = "-";
    reflectionValue.textContent = "-";
    reflectionDetails.textContent = "-";
    reflectionError.textContent = "-";

    try {
        const response = await fetch("/api/reflect-variable", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                code,
                variable_name: variableName,
            }),
        });

        const payload = await response.json();
        if (!response.ok) {
            throw new Error(payload.error || "Request failed");
        }

        reflectionVariableName.textContent = payload.variable_name ?? variableName;
        reflectionType.textContent = payload.inferred_type ?? "-";
        reflectionValue.textContent = renderJson(payload.parsed_value);
        reflectionDetails.textContent = renderJson(payload.type_details);
        reflectionError.textContent = "No error";
        reflectionStatusBadge.textContent = "Completed";
        reflectionStatusBadge.className = "status-badge success";
    } catch (error) {
        reflectionType.textContent = "Error";
        reflectionError.textContent = error.message;
        reflectionStatusBadge.textContent = "Failed";
        reflectionStatusBadge.className = "status-badge error";
    }
});
