"""FastAPI application for the local Prompt-to-CAD bridge."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from api.models import ExecuteRequest, ExecuteResponse, OutputFile, ParseResponse, PromptRequest
from api.services import (
    SUPPORTED_TOOLS, ApiServiceError, execute_prompt, list_outputs,
    parse_prompt, resolve_output_file,
)
from utils.output_paths import (
    get_assemblies_output_dir,
    get_exports_output_dir,
    get_parts_output_dir,
    get_user_output_root,
)


app = FastAPI(title="Prompt-to-CAD API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "prompt-to-cad-api"}


@app.get("/api/status")
def status() -> dict[str, object]:
    return {
        "api_status": "online",
        "solidworks_mode_available": True,
        "default_mode": "dry_run",
        "output_root_dir": str(get_user_output_root()),
        "output_parts_dir": str(get_parts_output_dir()),
        "output_exports_dir": str(get_exports_output_dir()),
        "output_assemblies_dir": str(get_assemblies_output_dir()),
        "supported_tools": SUPPORTED_TOOLS,
    }


@app.post("/api/parse", response_model=ParseResponse)
def parse(request: PromptRequest) -> dict[str, object]:
    return parse_prompt(request.prompt)


@app.post("/api/execute", response_model=ExecuteResponse)
def execute(request: ExecuteRequest):
    try:
        return execute_prompt(request.prompt, request.mode, request.confirmed)
    except ApiServiceError as exc:
        return JSONResponse(status_code=exc.status_code, content={
            "success": False, "mode": request.mode, "raw_prompt": request.prompt,
            "parsed_intent": None, "validated_intent": None, "result": None,
            "logs": [], "error": exc.message,
        })


@app.get("/api/outputs", response_model=list[OutputFile])
def outputs() -> list[dict[str, object]]:
    return list_outputs()


@app.get("/api/outputs/{category}/{filename}")
def download_output(category: str, filename: str):
    try:
        path = resolve_output_file(category, filename)
    except ApiServiceError as exc:
        return JSONResponse(status_code=exc.status_code, content={"error": exc.message})
    return FileResponse(path, filename=path.name)
