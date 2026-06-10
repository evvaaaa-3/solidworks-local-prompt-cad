"""Terminal CLI for the SolidWorks Local Prompt-to-CAD Stage 1 prototype."""

from __future__ import annotations

import json
from typing import Any


WELCOME_MESSAGE = """SolidWorks Local Prompt-to-CAD
Type `help` for examples or `exit` to quit.
"""

HELP_MESSAGE = """
Supported examples:
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
"""


def _print_supported_examples() -> None:
    print(HELP_MESSAGE)


def _to_jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    return value


def process_prompt(prompt: str, ask_confirmation: bool = True, dry_run: bool = True) -> None:
    try:
        from parser.rule_parser import parse_prompt_rule_based
        from router.tool_router import route_intent
        from validator.validate_intent import validate_intent
    except ImportError as exc:
        print("Pipeline modules could not be imported.")
        print(f"Import detail: {exc}")
        return

    try:
        parsed_intent = parse_prompt_rule_based(prompt)
        print("Parsed intent:")
        print(json.dumps(_to_jsonable(parsed_intent), indent=2))

        validated_intent = validate_intent(parsed_intent)
        print("Validated intent:")
        print(validated_intent)

        if ask_confirmation:
            confirmation = input("Proceed? [y/n]: ").strip().lower()
            if confirmation not in {"y", "yes"}:
                print("Cancelled.")
                return

        result = route_intent(validated_intent, dry_run=dry_run)
        if result is not None:
            print("Tool result:")
            print(json.dumps(_to_jsonable(result), indent=2))
    except NotImplementedError as exc:
        print("This pipeline step is not implemented yet. It will be added in a later stage.")
        if str(exc):
            print(f"Detail: {exc}")
    except ValueError as exc:
        print(f"Input error: {exc}")
        _print_supported_examples()
    except Exception as exc:
        print(f"Unexpected error: {exc}")


def main() -> None:
    print(WELCOME_MESSAGE)
    mode = input("Run mode:\n[1] Dry run\n[2] Real SolidWorks\n> ").strip()
    dry_run = mode != "2"
    if dry_run:
        print("Running in dry-run mode. SolidWorks will not be opened.")
    else:
        print("Real SolidWorks mode will open/control SolidWorks and create files locally.")

    while True:
        try:
            prompt = input("Enter prompt:\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not prompt:
            continue

        if prompt.lower() in {"exit", "quit"}:
            print("Goodbye.")
            break

        if prompt.lower() == "help":
            _print_supported_examples()
            continue

        process_prompt(prompt, dry_run=dry_run)


if __name__ == "__main__":
    main()
