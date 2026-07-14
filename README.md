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

## Stage 2A Extruded Primitive Expansion

Stage 2A completes the parser-validator-router-CAD path for extrusion-based primitives while preserving dry-run mode and keeping normal tests independent of SolidWorks.

Supported tools:

- `create_cube`
- `create_block`
- `create_cylinder`
- `create_disc`
- `create_plate`
- `create_tube`
- `create_plate_with_hole`
- `export_step`

Dry-run testing:

```powershell
python app.py
# starts in DRY-RUN mode
python -m pytest
```

Real SolidWorks testing:

```powershell
python app.py
# type: real
# confirm the warning prompt
```

The CLI supports runtime mode switching during the same session:

- `mode` shows the current mode.
- `dry` switches immediately to dry-run mode.
- `real` switches to real SolidWorks mode after confirmation.
- `solidworks` is an alias for `real`.
- `status` shows whether SolidWorks will be controlled.

Manual real-mode scripts:

```powershell
python manual_tests/test_solidworks_connection.py
python manual_tests/test_front_plane_selection.py
python manual_tests/test_create_cube_real.py
python manual_tests/test_create_block_real.py
python manual_tests/test_create_cylinder_real.py
python manual_tests/test_create_extruded_primitives_real.py
```

Example prompts:

- create a 50 mm cube
- create a block 100 by 60 by 20 mm
- create cylinder diameter 30 mm height 80 mm
- create disc diameter 50 mm thickness 5 mm
- create plate 100 by 60 by 5 mm
- create tube outer diameter 50 mm inner diameter 30 mm height 80 mm
- create plate 100 by 60 by 5 mm with hole diameter 20 mm
- export step as cube.step

Expected output files:

- `.SLDPRT` files are saved under `outputs/parts/`.
- `.step` and `.stp` files are saved under `outputs/exports/`.
- Existing files are not silently overwritten; incremented filenames are generated.

Screenshot checklist for reports:

- CLI run mode selection.
- Parsed intent and validated intent.
- SolidWorks Part document after sketch creation.
- Final extruded model.
- Saved file visible under `outputs/parts/`.

Known limitations:

- No cone, sphere, torus, revolve, sweep, or loft tools yet.
- No assemblies yet.
- No bolts, nuts, bearings, or gears yet.
- No Ollama parser yet.
- No MCP wrapper yet.

Next stage:

- Add the local Ollama JSON-intent parser after Stage 2A is stable.

## Stage 2B: Revolve-Based Primitives

Stage 2B adds revolve-based primitive workflows to the existing local parser-validator-router-CAD pipeline. Cone, sphere, and torus prompts now route through deterministic CAD functions with dry-run and real SolidWorks modes.

Supported revolve tools:

- `create_cone`
- `create_sphere`
- `create_torus`

The real SolidWorks workflow creates a sketch on the Front Plane, draws a centerline revolve axis, draws the profile geometry, exits sketch mode, and creates a 360-degree boss revolve. User dimensions remain in millimeters and are converted to meters internally for SolidWorks API calls.

Example prompts:

- create cone base diameter 50 mm height 80 mm
- create a cone with base diameter 50 mm and height 80 mm
- make cone diameter 50 mm height 80 mm
- create sphere diameter 50 mm
- create a sphere of diameter 50 mm
- make a ball of diameter 50 mm
- create torus major diameter 80 mm minor diameter 20 mm
- create a torus with major diameter 80 mm and tube diameter 20 mm

Real-mode tests:

```powershell
python manual_tests/test_create_cone_real.py
python manual_tests/test_create_sphere_real.py
python manual_tests/test_create_torus_real.py
```

Normal automated tests should not open SolidWorks:

```powershell
python -m pytest
```

Known limitations:

- Torus revolve may be experimental if SolidWorks COM contour or revolve-axis behavior varies by session.
- No sweep, loft, or advanced surface features yet.
- No assemblies yet.
- No Ollama parser yet.
- No MCP wrapper yet.

Screenshot checklist:

- Cone terminal success.
- Cone visible in SolidWorks.
- Sphere terminal success.
- Sphere visible in SolidWorks.
- Torus result or failure diagnostic.
- Generated files visible in `outputs/parts/`.

## Stage 4A: MCP SolidWorks Desktop Popup

Stage 4A adds a native Windows desktop popup for end users working beside SolidWorks. The popup uses the existing local Python pipeline directly: prompt interpretation, validation, routing, CAD tools, SolidWorks COM automation, and local output files. It does not require the FastAPI development server to be running.

Run the desktop popup:

```powershell
.\venv\Scripts\Activate.ps1
python -m desktop_ui.app
```

Install or update dependencies first:

```powershell
pip install -r requirements.txt
```

Future Ollama integration will happen behind the prompt interpretation function: a local Ollama parser can be tried first for more flexible natural-language interpretation, then fall back to the existing deterministic rule parser.

## Default Output Location

Generated CAD files are saved by default in the current Windows user's Documents folder:

```text
Documents\MCP SolidWorks\Outputs\Parts
Documents\MCP SolidWorks\Outputs\Exports
```

The application creates these folders automatically. Advanced users and tests can override the output root with:

```powershell
$env:MCP_SOLIDWORKS_OUTPUT_ROOT = "D:\Some\Other\Output\Folder"
```

## Assembly Creation

Stage 5A adds deterministic assembly creation through the same local parser, validator, router, CAD tools, and SolidWorks COM layers. No Ollama or external AI is required for assembly support.

Supported assembly templates:

- `base_plate_with_cylinders`: base plate with two cylindrical posts.
- `tube_with_two_end_discs`: tube with two circular end caps.
- `simple_shaft_with_two_wheels`: shaft with two wheels near the ends.

Example prompts:

```text
Create an assembly with a base plate and two cylinders
Create an assembly with a tube and two end discs
Create an assembly with a shaft and two wheels
```

Assembly files are saved to:

```text
Documents\MCP SolidWorks\Outputs\Assemblies
```

Component parts are saved to:

```text
Documents\MCP SolidWorks\Outputs\Parts
```

Current limitations:

- Assembly creation uses deterministic coordinates rather than advanced SolidWorks mates.
- Component orientation can depend on SolidWorks templates and the existing primitive orientation.
- The rule parser supports only the listed assembly templates in this stage.
- Unit tests do not open SolidWorks; real assembly verification is manual.

## Generic Assembly Planning Architecture

Stage 5B refactors assembly creation into a reusable planning architecture. The project is no longer only a fixed-template generator: the existing templates are now examples of a generic component, feature, instance, and constraint plan.

Core planning objects:

- `ComponentSpec`: describes a reusable part such as a plate, tube, disc, shaft, wheel, cylinder, pin, or plate with hole.
- `FeatureSpec`: describes part-level features such as holes and through-holes.
- `ComponentInstanceSpec`: describes a placed instance of a component in the assembly.
- `ConstraintSpec`: describes intended relationships such as fixed, coincident, concentric, distance, parallel, or coordinate placement.
- `AssemblyPlan`: contains all components, instances, constraints, output filename, and metadata for one assembly.

Execution layers:

- Component factory: translates `ComponentSpec` objects into existing primitive part creation calls.
- Generic executor: creates/reuses component parts, opens a SolidWorks assembly, inserts instances, applies available constraints, uses coordinate placement fallback where needed, and saves a verified `.SLDASM`.

Current behavior uses coordinate placement as the reliable fallback while preserving planned mate constraints in the result object. Future mate execution can improve the executor without changing parser prompts or the high-level assembly plan structure.
