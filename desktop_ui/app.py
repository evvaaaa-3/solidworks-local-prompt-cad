"""CustomTkinter desktop popup for local SolidWorks Prompt-to-CAD."""

from __future__ import annotations

import os
import queue
import threading
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import pythoncom

try:
    import customtkinter as ctk
    from tkinter import messagebox
except ModuleNotFoundError:
    ctk = None  # type: ignore[assignment]
    messagebox = None  # type: ignore[assignment]

from parser.rule_parser import parse_prompt
from router.tool_router import route_intent
from utils.output_paths import (
    ensure_output_dirs,
    get_assemblies_output_dir,
    get_user_output_root,
    is_safe_output_path,
)
from validator.validate_intent import validate_intent


APP_TITLE = "MCP SolidWorks"
DEFAULT_PROMPT = "Create a sphere with diameter 50 mm"
PART_EXAMPLES = [
    "Create a cube with side 50 mm",
    "Create a cylinder with diameter 30 mm and height 80 mm",
    "Create a hollow tube with outer diameter 50 mm, inner diameter 30 mm, and height 80 mm",
    "Create a plate 100 by 60 by 5 mm with hole diameter 20 mm",
    "Create a cone with base diameter 50 mm and height 80 mm",
    "Create a sphere with diameter 50 mm",
    "Create a torus with major diameter 80 mm and minor diameter 20 mm",
]
ASSEMBLY_EXAMPLES = [
    "Create an assembly with a base plate and two cylinders",
    "Create an assembly with a tube and two end discs",
    "Create an assembly with a shaft and two wheels",
    "Create a flanged shaft assembly",
]


def interpret_prompt(prompt: str) -> tuple[dict[str, Any], str]:
    """Interpret a user prompt into the existing internal intent shape."""

    # Future: call local Ollama first for flexible natural-language interpretation.
    # If Ollama is unavailable or returns invalid structured intent,
    # fall back to the existing deterministic parser.
    return parse_prompt(prompt), "rule_parser"


def _now() -> str:
    return datetime.now().strftime("%H:%M:%S")


def _tool_label(tool_name: str) -> str:
    labels = {
        "create_cube": "Cube",
        "create_block": "Block",
        "create_cylinder": "Cylinder",
        "create_disc": "Disc",
        "create_plate": "Plate",
        "create_tube": "Tube",
        "create_plate_with_hole": "Plate with hole",
        "create_cone": "Cone",
        "create_sphere": "Sphere",
        "create_torus": "Torus",
        "create_assembly": "Assembly",
        "export_step": "STEP export",
    }
    return labels.get(tool_name, "Model")


def _dimension_summary(validated_intent: Any) -> str:
    if validated_intent.tool_name == "create_assembly":
        assembly_type = validated_intent.parameters.assembly_type.replace("_", " ")
        return f"Assembly detected: {assembly_type}"

    values = validated_intent.parameters.model_dump()
    readable = []
    for key, value in values.items():
        name = key.replace("_mm", "").replace("_", " ")
        if isinstance(value, (int, float)):
            readable.append(f"{name} {value:g} mm")
        else:
            readable.append(f"{name} {value}")
    return f"{_tool_label(validated_intent.tool_name)} detected: " + ", ".join(readable)


def _friendly_error(exc: Exception) -> str:
    text = str(exc).lower()
    if "file was not saved successfully" in text:
        return (
            "The model was created in SolidWorks, but the file was not saved successfully.\n"
            "Please check the output folder or try saving manually."
        )
    if "could not connect to solidworks" in text or "com automation" in text:
        return "SolidWorks is not running. Please open SolidWorks and try again."
    if "unsupported cad prompt" in text or "missing" in text or "need" in text:
        return "I could not understand that request. Open Help & Examples for supported commands."
    if "invalid cad intent" in text or "greater than 0" in text or "positive" in text:
        return "The dimensions are not valid. Please use positive values."
    if "save" in text or "output" in text or "filepath" in text:
        return "The model could not be saved. Please check the output folder."
    return "The model could not be created. Please check SolidWorks and try again."


def _attach_running_solidworks() -> Any:
    try:
        import win32com.client
    except ImportError as exc:
        raise RuntimeError("pywin32 is not installed.") from exc

    try:
        return win32com.client.GetActiveObject("SldWorks.Application")
    except Exception as exc:
        raise RuntimeError("SolidWorks is not running.") from exc


def _initialize_com_for_worker() -> bool:
    pythoncom.CoInitialize()
    return True


def _release_com_for_worker(initialized: bool) -> None:
    if initialized:
        pythoncom.CoUninitialize()


_UI_BASE = ctk.CTk if ctk is not None else object


class MpcSolidWorksApp(_UI_BASE):
    def __init__(self) -> None:
        if ctk is None or messagebox is None:
            raise RuntimeError(
                "customtkinter is required for the desktop popup. "
                "Install dependencies with 'pip install -r requirements.txt'."
            )
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1100x720")
        self.minsize(850, 560)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.events: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.is_running = False
        self.last_output_path: Path | None = None
        self.connection_status = ctk.StringVar(value="SolidWorks: Checking...")
        self.progress_status = ctk.StringVar(value="Ready")
        self.result_title = ctk.StringVar(value="No model created yet.")
        self.result_detail = ctk.StringVar(value="")
        ensure_output_dirs()

        self._build_ui()
        self.after(100, self._poll_events)
        self.refresh_connection()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, corner_radius=0, fg_color="#101820")
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        title_block = ctk.CTkFrame(header, fg_color="transparent")
        title_block.grid(row=0, column=0, padx=22, pady=16, sticky="w")
        ctk.CTkLabel(
            title_block,
            text=APP_TITLE,
            font=ctk.CTkFont(size=26, weight="bold"),
            text_color="#f8fafc",
        ).pack(anchor="w")
        ctk.CTkLabel(
            title_block,
            text="Local SolidWorks Prompt-to-CAD",
            font=ctk.CTkFont(size=13),
            text_color="#9fb0c3",
        ).pack(anchor="w", pady=(2, 0))

        status_block = ctk.CTkFrame(header, fg_color="transparent")
        status_block.grid(row=0, column=1, padx=22, pady=16, sticky="e")
        self.status_badge = ctk.CTkLabel(
            status_block,
            textvariable=self.connection_status,
            fg_color="#334155",
            text_color="#dbeafe",
            corner_radius=18,
            padx=14,
            pady=7,
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.status_badge.pack(side="left", padx=(0, 10))
        self.refresh_button = ctk.CTkButton(
            status_block,
            text="Refresh Connection",
            width=150,
            command=self.refresh_connection,
        )
        self.refresh_button.pack(side="left")

        body = ctk.CTkFrame(self, fg_color="#0b1117", corner_radius=0)
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(0, weight=1)

        prompt_panel = ctk.CTkFrame(body, fg_color="#111a23", corner_radius=10)
        prompt_panel.grid(row=0, column=0, padx=(22, 11), pady=22, sticky="nsew")
        prompt_panel.grid_columnconfigure(0, weight=1)
        prompt_panel.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            prompt_panel,
            text="What would you like to create?",
            font=ctk.CTkFont(size=17, weight="bold"),
            text_color="#f8fafc",
        ).grid(row=0, column=0, padx=18, pady=(18, 8), sticky="w")

        self.prompt_box = ctk.CTkTextbox(
            prompt_panel,
            height=250,
            fg_color="#071018",
            border_width=1,
            border_color="#263544",
            text_color="#f8fafc",
            font=ctk.CTkFont(size=16),
            wrap="word",
        )
        self.prompt_box.grid(row=1, column=0, padx=18, pady=(0, 14), sticky="nsew")
        self.prompt_box.insert("1.0", DEFAULT_PROMPT)

        action_row = ctk.CTkFrame(prompt_panel, fg_color="transparent")
        action_row.grid(row=2, column=0, padx=18, pady=(0, 18), sticky="ew")
        action_row.grid_columnconfigure(0, weight=1)
        self.create_button = ctk.CTkButton(
            action_row,
            text="Create Model",
            height=44,
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self.create_model,
        )
        self.create_button.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.help_button = ctk.CTkButton(
            action_row,
            text="Help & Examples",
            height=44,
            fg_color="#263544",
            hover_color="#334155",
            command=self.open_help,
        )
        self.help_button.grid(row=0, column=1, sticky="e")

        progress_panel = ctk.CTkFrame(prompt_panel, fg_color="#0d151d", corner_radius=8)
        progress_panel.grid(row=3, column=0, padx=18, pady=(0, 18), sticky="ew")
        ctk.CTkLabel(
            progress_panel,
            textvariable=self.progress_status,
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#bae6fd",
        ).pack(anchor="w", padx=14, pady=(12, 4))
        self.activity_log = ctk.CTkTextbox(
            progress_panel,
            height=150,
            fg_color="#071018",
            border_width=1,
            border_color="#263544",
            text_color="#cbd5e1",
            font=ctk.CTkFont(size=13),
            wrap="word",
        )
        self.activity_log.pack(fill="both", expand=True, padx=14, pady=(4, 14))
        self.activity_log.insert("1.0", f"[{_now()}] Ready\n")
        self.activity_log.configure(state="disabled")

        result_panel = ctk.CTkFrame(body, fg_color="#111a23", corner_radius=10)
        result_panel.grid(row=0, column=1, padx=(11, 22), pady=22, sticky="nsew")
        result_panel.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            result_panel,
            text="Result",
            font=ctk.CTkFont(size=17, weight="bold"),
            text_color="#f8fafc",
        ).grid(row=0, column=0, padx=18, pady=(18, 8), sticky="w")

        result_card = ctk.CTkFrame(result_panel, fg_color="#0d151d", corner_radius=8)
        result_card.grid(row=1, column=0, padx=18, pady=(0, 14), sticky="ew")
        ctk.CTkLabel(
            result_card,
            textvariable=self.result_title,
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#f8fafc",
            wraplength=340,
            justify="left",
        ).pack(anchor="w", padx=16, pady=(16, 6))
        ctk.CTkLabel(
            result_card,
            textvariable=self.result_detail,
            font=ctk.CTkFont(size=13),
            text_color="#9fb0c3",
            wraplength=340,
            justify="left",
        ).pack(anchor="w", padx=16, pady=(0, 16))

        self.show_file_button = ctk.CTkButton(
            result_panel,
            text="Show File",
            height=38,
            command=self.show_file,
            state="disabled",
        )
        self.show_file_button.grid(row=2, column=0, padx=18, pady=(0, 10), sticky="ew")

        self.open_folder_button = ctk.CTkButton(
            result_panel,
            text="Open Output Folder",
            height=38,
            fg_color="#263544",
            hover_color="#334155",
            command=self.open_output_folder,
        )
        self.open_folder_button.grid(row=3, column=0, padx=18, pady=(0, 18), sticky="ew")

        ctk.CTkLabel(
            result_panel,
            text=(
                f"Output folder: {get_user_output_root()}\n"
                f"Assembly folder: {get_assemblies_output_dir()}"
            ),
            text_color="#9fb0c3",
            wraplength=340,
            justify="left",
        ).grid(row=4, column=0, padx=18, pady=(0, 12), sticky="w")

        ctk.CTkLabel(
            result_panel,
            text="This popup creates real SolidWorks models. Keep SolidWorks open and save your work before creating a new model.",
            text_color="#94a3b8",
            wraplength=340,
            justify="left",
        ).grid(row=5, column=0, padx=18, pady=(0, 18), sticky="sw")

    def refresh_connection(self) -> None:
        self.connection_status.set("SolidWorks: Checking...")
        self._set_status_color("checking")
        self.refresh_button.configure(state="disabled")
        threading.Thread(target=self._check_connection_worker, daemon=True).start()

    def _check_connection_worker(self) -> None:
        com_initialized = False
        try:
            com_initialized = _initialize_com_for_worker()
            _attach_running_solidworks()
        except Exception:
            print("SolidWorks connection check failed:")
            traceback.print_exc()
            self.events.put(("connection", False))
        else:
            self.events.put(("connection", True))
        finally:
            _release_com_for_worker(com_initialized)

    def create_model(self) -> None:
        if self.is_running:
            return
        prompt = self.prompt_box.get("1.0", "end").strip()
        if not prompt:
            messagebox.showinfo(APP_TITLE, "Please enter a model request.")
            return
        confirmed = messagebox.askyesno(
            APP_TITLE,
            "SolidWorks will create and save a local model.\nContinue?",
        )
        if not confirmed:
            self._log("Ready")
            return

        self.is_running = True
        self.create_button.configure(state="disabled", text="Creating...")
        self.help_button.configure(state="disabled")
        self.last_output_path = None
        self.show_file_button.configure(state="disabled")
        self.result_title.set("Creating model...")
        self.result_detail.set("")
        threading.Thread(target=self._create_worker, args=(prompt,), daemon=True).start()

    def _create_worker(self, prompt: str) -> None:
        com_initialized = False
        try:
            com_initialized = _initialize_com_for_worker()
            self.events.put(("progress", "Understanding your request"))
            intent_dict, _parser_label = interpret_prompt(prompt)

            is_assembly = intent_dict.get("tool_name") == "create_assembly"
            check_message = "Checking assembly components" if is_assembly else "Checking dimensions"
            self.events.put(("progress", check_message))
            validated = validate_intent(intent_dict)
            self.events.put(("log", _dimension_summary(validated)))

            self.events.put(("progress", "Connecting to SolidWorks"))
            _attach_running_solidworks()
            self.events.put(("log", "Connected to SolidWorks"))

            if is_assembly:
                self.events.put(("progress", "Creating component parts"))
                self.events.put(("progress", "Opening SolidWorks assembly document"))
                self.events.put(("progress", "Inserting components"))
                self.events.put(("progress", "Positioning components"))
            else:
                self.events.put(("progress", "Creating model"))
            result = route_intent(validated, dry_run=False)

            self.events.put(("progress", "Saving assembly" if is_assembly else "Saving file"))
            filepath = Path(result.get("filepath", "")).resolve()
            filename = filepath.name if filepath.name else "local model"
            self.events.put(("log", result.get("message") or "Model created successfully"))
            if filepath.name:
                self.events.put(("log", f"Saved: {filename}"))
            self.events.put(("success", result))
        except Exception as exc:
            print("Desktop model creation failed:")
            traceback.print_exc()
            self.events.put(("failure", _friendly_error(exc)))
        finally:
            _release_com_for_worker(com_initialized)

    def open_help(self) -> None:
        dialog = ctk.CTkToplevel(self)
        dialog.title("Help & Examples")
        dialog.geometry("560x430")
        dialog.minsize(500, 360)
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(
            dialog,
            text="Supported examples",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(anchor="w", padx=18, pady=(18, 8))

        frame = ctk.CTkScrollableFrame(dialog, fg_color="#101820")
        frame.pack(fill="both", expand=True, padx=18, pady=(0, 18))

        self._add_help_section(frame, "Part examples", PART_EXAMPLES)
        self._add_help_section(frame, "Assembly examples", ASSEMBLY_EXAMPLES)

    def _add_help_section(
        self,
        frame: ctk.CTkScrollableFrame,
        title: str,
        examples: list[str],
    ) -> None:
        ctk.CTkLabel(
            frame,
            text=title,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#bae6fd",
        ).pack(anchor="w", padx=8, pady=(10, 4))
        for example in examples:
            button = ctk.CTkButton(
                frame,
                text=example,
                anchor="w",
                height=38,
                fg_color="#1f2a36",
                hover_color="#334155",
                command=lambda value=example, popup=dialog: self._use_example(value, popup),
            )
            button.pack(fill="x", padx=8, pady=6)

    def _use_example(self, example: str, dialog: ctk.CTkToplevel) -> None:
        self.prompt_box.delete("1.0", "end")
        self.prompt_box.insert("1.0", example)
        dialog.destroy()

    def show_file(self) -> None:
        if self.last_output_path is None:
            return
        if not is_safe_output_path(self.last_output_path):
            messagebox.showwarning(APP_TITLE, "That file is outside the safe output folders.")
            return
        if self.last_output_path.exists():
            os.startfile(self.last_output_path)
        else:
            messagebox.showwarning(APP_TITLE, "The saved file could not be found.")

    def open_output_folder(self) -> None:
        output_dir = get_user_output_root()
        if is_safe_output_path(output_dir):
            ensure_output_dirs()
            os.startfile(output_dir)

    def _poll_events(self) -> None:
        handlers: dict[str, Callable[[Any], None]] = {
            "connection": self._handle_connection,
            "progress": self._handle_progress,
            "log": self._log,
            "success": self._handle_success,
            "failure": self._handle_failure,
        }
        while True:
            try:
                event, payload = self.events.get_nowait()
            except queue.Empty:
                break
            handler = handlers.get(event)
            if handler:
                handler(payload)
        self.after(100, self._poll_events)

    def _handle_connection(self, connected: bool) -> None:
        if connected:
            self.connection_status.set("SolidWorks: Connected")
            self._set_status_color("connected")
            self._log("Connected to SolidWorks")
        else:
            self.connection_status.set("SolidWorks: Not Running")
            self._set_status_color("not_running")
            self._log("SolidWorks is not running")
        self.refresh_button.configure(state="normal")

    def _handle_progress(self, status: str) -> None:
        self.progress_status.set(status)
        self._log(status)

    def _handle_success(self, result: dict[str, Any]) -> None:
        filepath = Path(result.get("filepath", "")).resolve()
        self.last_output_path = filepath if filepath.name else None
        self.progress_status.set("Complete")
        self._log("Complete")
        if (
            self.last_output_path is not None
            and self.last_output_path.exists()
            and is_safe_output_path(self.last_output_path)
        ):
            if self.last_output_path.suffix.lower() == ".sldasm":
                failed_constraints = result.get("constraints_failed", [])
                warning_count = len(result.get("warnings", []))
                self.result_title.set(
                    "Assembly created with warnings"
                    if failed_constraints or warning_count
                    else "Assembly created successfully"
                )
                component_count = len(result.get("instances", []))
                inserted_count = len(result.get("inserted_components", []))
                applied_count = len(result.get("constraints_applied", []))
                planned_count = len(result.get("constraints_planned", []))
                failure_line = ""
                if failed_constraints:
                    failed_id = failed_constraints[0].get("constraint_id", "unknown")
                    failure_line = f"\nFailed constraint: {failed_id}"
                self.result_detail.set(
                    f"File: {self.last_output_path.name}\n"
                    f"Location: {self.last_output_path.parent}\n"
                    f"Components inserted: {inserted_count} of {component_count}\n"
                    f"Constraints applied: {applied_count} of {planned_count}"
                    f"{failure_line}"
                )
            else:
                self.result_title.set("Model created successfully")
                self.result_detail.set(
                    f"File: {self.last_output_path.name}\nLocation: {self.last_output_path.parent}"
                )
            self.show_file_button.configure(state="normal")
        else:
            self.result_title.set(
                "The model was created in SolidWorks, but the file was not saved successfully."
            )
            self.result_detail.set("Please check the output folder or try saving manually.")
            self.show_file_button.configure(state="disabled")
        self._finish_request()

    def _handle_failure(self, message: str) -> None:
        self.progress_status.set("Ready")
        self.result_title.set(message)
        self.result_detail.set("")
        self._log(message)
        self._finish_request()

    def _finish_request(self) -> None:
        self.is_running = False
        self.create_button.configure(state="normal", text="Create Model")
        self.help_button.configure(state="normal")

    def _log(self, message: str) -> None:
        self.activity_log.configure(state="normal")
        self.activity_log.insert("end", f"[{_now()}] {message}\n")
        self.activity_log.see("end")
        self.activity_log.configure(state="disabled")

    def _set_status_color(self, state: str) -> None:
        colors = {
            "connected": ("#14532d", "#bbf7d0"),
            "not_running": ("#4c1d1d", "#fecaca"),
            "checking": ("#334155", "#dbeafe"),
        }
        fg, text = colors[state]
        self.status_badge.configure(fg_color=fg, text_color=text)


def main() -> None:
    app = MpcSolidWorksApp()
    app.mainloop()


if __name__ == "__main__":
    main()
