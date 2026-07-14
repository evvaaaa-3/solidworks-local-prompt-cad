# Stage 5A Assembly Manual Test

Run the desktop popup:

```powershell
.\venv\Scripts\Activate.ps1
python -m desktop_ui.app
```

Open SolidWorks 2022 before running real assembly creation.

## Prompts To Try

```text
Create an assembly with a base plate and two cylinders
Create an assembly with a tube and two end discs
Create an assembly with a shaft and two wheels
```

## Expected Output Folder

```text
Documents\MCP SolidWorks\Outputs\Assemblies
```

## Visual Confirmation In SolidWorks

- A new assembly document is created.
- Required component part files are created under `Documents\MCP SolidWorks\Outputs\Parts`.
- The final `.SLDASM` file is saved under `Documents\MCP SolidWorks\Outputs\Assemblies`.
- Base plate assembly: one base plate and two cylindrical posts are inserted symmetrically.
- Tube assembly: one tube and two end discs/caps are inserted at opposite ends.
- Shaft assembly: one shaft and two wheels are inserted near the ends.

## Current Limitation

Stage 5A uses deterministic component placement with simple coordinates. Depending on SolidWorks document templates and default part orientation, a user may need to inspect orientation visually. Advanced mates and automatic orientation repair are planned for a later stage.

## Generic Assembly Planner

Stage 5B backs these templates with a reusable component-feature-constraint plan instead of isolated one-off assembly functions.

Each supported assembly is represented as:

- Component specs, such as plate, tube, shaft, wheel, cylinder, or disc.
- Optional feature specs, such as holes or through-holes.
- Component instances with deterministic positions and rotations.
- Constraint specs, such as fixed, concentric, coincident, distance, parallel, and coordinate placement.

Future assemblies should be added by composing components and constraints into an `AssemblyPlan`, then passing that plan through the generic component factory and assembly executor.

Current mate execution may still use coordinate placement fallback where SolidWorks COM mate behavior is not reliable enough yet. The planner still records intended constraints so mate execution can improve later without replacing the assembly architecture.
