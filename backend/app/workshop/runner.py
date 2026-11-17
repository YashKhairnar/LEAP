"""Run workshop cells the way the Colab notebook would.

Each run replays every earlier workshop cell (silently) and then the learner's
cell, so later steps always see the variables earlier steps made. A trusted
prelude installs a stand-in for ``google.colab.files`` so the notebook's own
upload cell runs unchanged: ``files.upload()`` returns the workshop dataset
under the filename the learner picked in the browser.
"""

from __future__ import annotations

import json
import os
import re
from time import monotonic
from typing import Any

from ..execution.cells import (
    ALLOWED_IMPORTS,
    RESULT_MARKER,
    UnsafeCode,
    call_codapi,
    call_docker,
    call_modal,
    instrumented_program,
    validate_code,
)
from ..paths import BACKEND_ROOT
from .content import DATASET_FILENAME, PRIMARY, RUNTIME_DATASET_FILENAME, WorkshopVersion

DATASET_PATH = BACKEND_ROOT / "datasets" / DATASET_FILENAME
WORKSHOP_IMPORTS = frozenset(ALLOWED_IMPORTS | {"io", "google"})
WORKSHOP_DUNDERS = frozenset({"__version__"})
UPLOAD_NAME = re.compile(r"^[A-Za-z0-9 _().-]{1,120}$")

_PRELUDE = '''
import sys as _w_sys
import types as _w_types
_w_google = _w_types.ModuleType("google")
_w_colab = _w_types.ModuleType("google.colab")
_w_files = _w_types.ModuleType("google.colab.files")
def _w_upload(_w_name={name}):
    with open({dataset}, "rb") as _w_handle:
        _w_data = _w_handle.read()
    print(f"{{_w_name}}(text/csv) - {{len(_w_data)}} bytes, last modified: n/a - 100% done")
    print(f"Saving {{_w_name}} to {{_w_name}}")
    return {{_w_name: _w_data}}
_w_files.upload = _w_upload
_w_colab.files = _w_files
_w_google.colab = _w_colab
_w_sys.modules.update({{"google": _w_google, "google.colab": _w_colab, "google.colab.files": _w_files}})
'''


def valid_upload_name(name: str) -> bool:
    return bool(UPLOAD_NAME.fullmatch(name)) and ".." not in name


def prelude(uploaded_filename: str | None) -> str:
    name = uploaded_filename if uploaded_filename and valid_upload_name(uploaded_filename) else RUNTIME_DATASET_FILENAME
    return _PRELUDE.format(name=json.dumps(name), dataset=json.dumps(RUNTIME_DATASET_FILENAME))


def workshop_program(cell_id: str, code: str, uploaded_filename: str | None, version: WorkshopVersion = PRIMARY) -> str:
    """Validate learner code and build the full program for one cell run."""
    validate_code(code, WORKSHOP_IMPORTS, WORKSHOP_DUNDERS)
    earlier = [previous.code for previous in version.cells_before(cell_id)]
    for previous in earlier:
        validate_code(previous, WORKSHOP_IMPORTS, WORKSHOP_DUNDERS)
    return instrumented_program([prelude(uploaded_filename), *earlier], code)


def _execute(program: str) -> dict[str, Any]:
    engine = os.getenv("CODE_EXECUTION_ENGINE", "docker")
    if engine == "modal":
        return call_modal(program, RUNTIME_DATASET_FILENAME)
    files = {"": program, RUNTIME_DATASET_FILENAME: DATASET_PATH.read_text(encoding="utf-8")}
    if engine == "docker":
        return call_docker(files)
    # Codapi's hosted proxy rejects the 1.3 MB dataset; the workshop needs docker or modal.
    return call_codapi(files)


def run_workshop_cell(version: WorkshopVersion, cell_id: str, code: str, uploaded_filename: str | None) -> dict[str, Any]:
    engine = os.getenv("CODE_EXECUTION_ENGINE", "docker")
    try:
        program = workshop_program(cell_id, code, uploaded_filename, version)
    except UnsafeCode as error:
        return {"success": False, "stdout": "", "stderr": str(error), "result": None,
                "table_preview": None, "plots": [], "duration_ms": 0, "engine": engine}
    started = monotonic()
    try:
        raw = _execute(program)
    except RuntimeError as error:
        raw = {"ok": False, "stdout": "", "stderr": str(error), "duration": 0}
    return parse_output(raw, started, engine)


def parse_output(raw: dict[str, Any], started: float, engine: str) -> dict[str, Any]:
    stdout = str(raw.get("stdout", ""))
    result = None
    table = None
    plots: list[str] = []
    if RESULT_MARKER in stdout:
        stdout, encoded = stdout.rsplit(RESULT_MARKER, 1)
        stdout = stdout.rstrip("\n")
        try:
            structured = json.loads(encoded.strip())
            result = structured.get("result")
            table = structured.get("table_preview")
            plots = structured.get("plots") or []
        except json.JSONDecodeError:
            pass
    return {
        "success": bool(raw.get("ok")),
        "stdout": stdout[-20_000:],
        "stderr": str(raw.get("stderr", ""))[-20_000:],
        "result": result,
        "table_preview": table,
        "plots": plots,
        "duration_ms": int(raw.get("duration") or round((monotonic() - started) * 1000)),
        "engine": engine,
    }
