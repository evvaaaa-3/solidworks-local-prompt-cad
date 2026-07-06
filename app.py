"""Terminal CLI for the SolidWorks Local Prompt-to-CAD prototype."""

from __future__ import annotations

import json
from typing import Any


WELCOME_MESSAGE = """SolidWorks Local Prompt-to-CAD
Current mode: DRY-RUN
Type `help` for commands.
"""

HELP_MESSAGE = """
Mode commands:
- mode        Show current mode
- dry         Switch to dry-run mode
- real        Switch to real SolidWorks mode
- solidworks  Alias for real mode
- status      Show current execution status
- help        Show this help message
- exit        Quit the app
- quit        Quit the app

Shape examples:
- create a 50 mm cube
- create a block 100 by 60 by 20 mm
- create cylinder diameter 30 mm height 80 mm
- create disc diameter 50 mm thickness 5 mm
- create plate 100 by 60 by 5 mm
- create tube outer diameter 50 mm inner diameter 30 mm height 80 mm
- create plate 100 by 60 by 5 mm with hole diameter 20 mm
- create cone base diameter 50 mm height 80 mm
- create sphere diameter 50 mm
- create torus major diameter 80 mm minor diameter 20 mm
- export step as cube.step
"""


def _mode_label(dry_run: bool) -> str:
    return "DRY-RUN" if dry_run else "REAL SolidWorks"


def _print_help() -> None:
    print(HELP_MESSAGE)


def _print_status(dry_run: bool) -> None:
    print(f"Current mode: {_mode_label(dry_run)}")
    if dry_run:
        print("No SolidWorks calls will be made.")
    else:
        print("Real mode will open/control SolidWorks and create files locally.")


def _confirm_real_mode() -> bool:
    print("Real SolidWorks mode will open/control SolidWorks and create files locally.")
    print("Make sure SolidWorks 2022 is installed and preferably already open.")
    confirmation = input("Switch to real SolidWorks mode? [y/n]: ").strip().lower()
    return confirmation in {"y", "yes"}


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
            confirmation = input(f"Proceed in {_mode_label(dry_run)} mode? [y/n]: ").strip().lower()
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
        _print_help()
    except Exception as exc:
        print(f"Unexpected error: {exc}")


def handle_command(command: str, dry_run: bool) -> tuple[bool, bool]:
    normalized = command.strip().lower()

    if normalized in {"exit", "quit"}:
        print("Goodbye.")
        return dry_run, True

    if normalized == "help":
        _print_help()
        return dry_run, False

    if normalized == "mode":
        print(f"Current mode: {_mode_label(dry_run)}")
        return dry_run, False

    if normalized == "status":
        _print_status(dry_run)
        return dry_run, False

    if normalized == "dry":
        print("Switched to DRY-RUN mode. No SolidWorks calls will be made.")
        return True, False

    if normalized in {"real", "solidworks"}:
        if _confirm_real_mode():
            print("Switched to REAL SolidWorks mode.")
            return False, False
        print(f"Stayed in {_mode_label(dry_run)} mode.")
        return dry_run, False

    return dry_run, False


def main() -> None:
    print(WELCOME_MESSAGE)
    dry_run = True

    while True:
        try:
            prompt = input("Enter prompt:\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not prompt:
            continue

        if prompt.lower() in {
            "mode",
            "dry",
            "real",
            "solidworks",
            "status",
            "help",
            "exit",
            "quit",
        }:
            dry_run, should_exit = handle_command(prompt, dry_run)
            if should_exit:
                break
            continue

        process_prompt(prompt, dry_run=dry_run)


if __name__ == "__main__":
    main()
