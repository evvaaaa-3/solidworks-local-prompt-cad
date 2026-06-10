# SolidWorks Local Prompt-to-CAD Prototype

Phase 1 is a local Python CLI prototype that turns simple natural language CAD prompts into structured intent, validates that intent, routes it to deterministic CAD tools, and returns dry-run CAD results. It does not connect to SolidWorks yet.

## What Phase 1 Does

- Runs as a local command-line application.
- Supports a small fixed set of CAD operations: `create_cube`, `create_block`, `create_cylinder`, and `export_step`.
- Uses rule-based parsing, Pydantic validation, deterministic routing, and dry-run CAD tool functions.
- Prints and returns structured dry-run results.
- Keeps user-facing dimensions in millimeters. Meter conversion is available in config for later SolidWorks API work.

## What Phase 1 Does Not Do

- Does not use cloud APIs, cloud LLMs, remote services, or internet-based inference.
- Does not build MCP, a frontend, or Streamlit.
- Does not implement Ollama yet beyond a future placeholder module.
- Does not call SolidWorks or use COM automation yet.
- Does not generate arbitrary SolidWorks code from prompts.
- Does not allow arbitrary code execution from prompts.

## Local-Only Architecture

```text
User prompt
-> CLI app
-> rule-based parser
-> structured intent JSON
-> Pydantic validation
-> tool router
-> dry-run CAD tool function
-> structured dry-run result
```

Everything runs locally through the terminal with `python app.py`.

## Requirements

- Python 3.10 or newer
- Python packages listed in `requirements.txt`

## Setup

Create and activate a virtual environment if desired, then install dependencies:

```bash
pip install -r requirements.txt
```

## How to Run

```bash
python app.py
```

## Supported Prompts

- Create a cube of side 50 mm
- Create a cube 40 mm
- Create a block of length 100 mm width 60 mm height 20 mm
- Create a block 100 by 60 by 20 mm
- Create a cylinder of diameter 30 mm and height 80 mm
- Create a cylinder 30 80
- Export current model as STEP

## Troubleshooting

- If a prompt cannot be parsed, use one of the supported prompt formats listed above.
- If a dimension is missing, invalid, zero, or negative, the request will be rejected safely.

## Future Phases

- Stage 2: SolidWorks COM automation after Stage 1 tests pass.
- Stage 3: Ollama parser integration after the backend and SolidWorks function layer are stable.
- Later: MCP integration only after the local backend and CAD layers are stable.

## Stage 1 Backend Dry Run

Stage 1 extends the existing Stage 0 scaffold with local backend logic only. It builds the deterministic path from natural language prompt to structured CAD intent, Pydantic validation, routing, and dry-run CAD tool functions.

Current Stage 1 flow:

```text
Prompt
-> rule parser
-> JSON-like intent dict
-> Pydantic validation
-> confirmation
-> router
-> dry-run CAD tool function
```

Setup and run:

```powershell
cd existing-project-folder
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
pytest
```

Example prompts:

- create a 50 mm cube
- create cube 50 mm
- make a cube of side 50 mm
- create a block 100 by 60 by 20 mm
- create block length 100 width 60 height 20 mm
- create cylinder diameter 30 mm height 80 mm
- create a cylinder of diameter 30 mm and height 80 mm
- export step as test.step
- export as test.step
- save step as cube.step

Intentionally not implemented in Stage 1:

- No SolidWorks COM automation calls.
- No MCP integration.
- No GUI.
- No Ollama execution.
- No raw SolidWorks code generation or execution from prompts.

## Stage 2 SolidWorks COM Automation

Stage 2 adds real SolidWorks COM automation behind the existing deterministic CAD functions while preserving Stage 1 dry-run behavior. The parser, schema, validator, and router intent shape remain stable.

Run the app:

```powershell
python app.py
```

At startup choose:

```text
[1] Dry run
[2] Real SolidWorks
```

Press Enter for dry-run mode. Dry-run mode does not open SolidWorks and does not make COM calls.

Real SolidWorks mode controls SolidWorks and creates files locally. Use it only on a Windows machine with SolidWorks 2022 installed and licensed.

Example prompts:

- create a 50 mm cube
- create a block 100 by 60 by 20 mm
- create cylinder diameter 30 mm height 80 mm
- export step as cube.step

Expected output files:

- Parts are saved under `outputs/parts/` as `.SLDPRT`.
- STEP exports are saved under `outputs/exports/` as `.step` or `.stp`.
- Existing files are not silently overwritten; incremented filenames are generated.

Manual SolidWorks connection check:

```powershell
python manual_tests/test_solidworks_connection.py
```

Troubleshooting:

- COM dispatch failure: confirm `pywin32` is installed and SolidWorks can be launched by the current Windows user.
- SolidWorks not installed: install and license SolidWorks Desktop 2022 before using real mode.
- SolidWorks not opening: start SolidWorks manually once, accept any first-run prompts, then retry.
- Template path issue: configure a valid SolidWorks part template path if blank part creation fails.
- Memory warning: close unused SolidWorks documents and restart SolidWorks before retrying.
- Permission issue: confirm the project folder and `outputs/` folders are writable.
