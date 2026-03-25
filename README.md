# System Variable Type Analyzer

System Variable Type Analyzer is a small Software Engineering course project with a Flask backend and a browser-based frontend. It accepts a system-related variable value, analyzes the input, and infers the most likely runtime type.

## Features

- Analyze plain text input through a web interface
- Normalize mildly malformed user input before parsing
- Infer common types such as Integer, Float, Boolean, String, List, Dictionary, and more
- Recursively analyze nested fields inside composite values
- Reflect the type of a named variable from a small Python code snippet
- Parse JSON values when possible
- Parse Python literals with `ast.literal_eval`
- Safely evaluate simple arithmetic expressions such as `8 * (2 + 1)`
- Return clear API responses in JSON format

## Project Structure

```text
.
|-- app.py
|-- requirements.txt
|-- README.md
|-- static
|   |-- app.js
|   `-- styles.css
`-- templates
    `-- index.html
```

## Requirements

- Python 3.10+
- `pip`

## Installation

```bash
pip install -r requirements.txt
```

## Run The Project

```bash
python app.py
```

After the server starts, open [http://127.0.0.1:5001](http://127.0.0.1:5001).

## How It Works

The backend checks the input in the following order:

1. Empty input
2. Input normalization
3. Integer
4. Float
5. Boolean
6. Arithmetic expression
7. JSON
8. Python literal
9. Fallback to String

This order helps the tool produce predictable type inference results for common configuration values.

## API

### `POST /api/analyze`

Request body:

```json
{
  "variable_value": "true"
}
```

### `POST /api/reflect-variable`

Request body:

```json
{
  "code": "port = \"5001\"\nenabled = \"true\"\nconfig = {\"port\": port, \"enabled\": enabled}",
  "variable_name": "config"
}
```

Example success response:

```json
{
  "variable_name": "config",
  "inferred_type": "Dict",
  "parsed_value": {
    "port": "5001",
    "enabled": "true"
  },
  "type_details": {
    "type": "Dict",
    "fields": {
      "port": {
        "type": "Integer",
        "value": 5001
      },
      "enabled": {
        "type": "Boolean",
        "value": true
      }
    },
    "value": {
      "port": "5001",
      "enabled": "true"
    }
  }
}
```

Example success response:

```json
{
  "original_input": "{\"port\":\"5001\",\"enabled\":\"true\"}",
  "normalized_input": "{\"port\":\"5001\",\"enabled\":\"true\"}",
  "inferred_type": "Dict",
  "parsed_value": {
    "port": "5001",
    "enabled": "true"
  },
  "type_details": {
    "type": "Dict",
    "fields": {
      "port": {
        "type": "Integer",
        "value": 5001
      },
      "enabled": {
        "type": "Boolean",
        "value": true
      }
    },
    "value": {
      "port": "5001",
      "enabled": "true"
    }
  }
}
```

Example response for an arithmetic expression:

```json
{
  "original_input": "8 * (2 + 1)",
  "inferred_type": "Integer",
  "parsed_value": 24,
  "warning": "Evaluated as arithmetic expression"
}
```

## Example Inputs

- `42`
- `3.14159`
- `true`
- `{"name": "demo", "debug": false}`
- `[1, 2, 3]`
- `("a", "b", "c")`
- `8 * (2 + 1)`
- `port = "5001"\nenabled = "true"\nconfig = {"port": port, "enabled": enabled}`

## Notes

- The tool is intended for learning and demonstration purposes.
- Arithmetic evaluation is intentionally limited to simple numeric expressions for safety.
- Composite values keep their original parsed structure while nested members get their own inferred type details.
- This project focuses on determining the type of a given system variable, which matches the course requirement.
