from __future__ import annotations

import ast
import json
import os
from pathlib import Path
import subprocess
import tempfile
from time import monotonic
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .datasets import dataset_for_task
from ..models import CodeExecutionRequest, CodeExecutionResult

ALLOWED_IMPORTS = {
    "csv", "datetime", "itertools", "math", "matplotlib", "numpy", "pandas",
    "re", "scipy", "seaborn", "sklearn", "statistics", "torch", "torchvision",
}
BANNED_NAMES = {
    "__import__", "breakpoint", "compile", "eval", "exec", "globals", "help",
    "input", "locals", "open", "quit", "exit", "memoryview", "vars",
}
BANNED_ATTRIBUTES = {
    "system", "popen", "spawn", "fork", "connect", "socket", "request",
    "urlopen", "read_html", "read_xml", "read_json", "to_pickle", "to_sql",
}
RESULT_MARKER = "__LEAP_RESULT_V1__"


class UnsafeCode(ValueError):
    pass


def validate_code(code: str) -> None:
    try:
        tree = ast.parse(code)
    except SyntaxError as error:
        raise UnsafeCode(f"SyntaxError: {error.msg} (line {error.lineno})") from error
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules = [alias.name.split(".", 1)[0] for alias in node.names]
            if any(module not in ALLOWED_IMPORTS for module in modules):
                raise UnsafeCode(
                    "Available imports include pandas, numpy, scikit-learn, matplotlib, "
                    "seaborn, scipy, and selected Python data utilities."
                )
        if isinstance(node, ast.ImportFrom):
            module = (node.module or "").split(".", 1)[0]
            if node.level or module not in ALLOWED_IMPORTS:
                raise UnsafeCode("That import is not available in the learning runtime.")
        if isinstance(node, ast.Name) and (node.id in BANNED_NAMES or node.id.startswith("fetch_")):
            raise UnsafeCode(f"{node.id} is not available in the learning runtime.")
        if isinstance(node, ast.Attribute) and (
            node.attr.startswith("__") or node.attr in BANNED_ATTRIBUTES or node.attr.startswith("fetch_")
        ):
            raise UnsafeCode(f"{node.attr} is not available in the learning runtime.")
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and (
            "/" in node.value or "\\" in node.value or ".." in node.value
        ):
            raise UnsafeCode("Only dataset filenames in the Codapi workspace are allowed.")


def instrumented_program(previous_cells: list[str], code: str) -> str:
    tree = ast.parse(code, mode="exec")
    if tree.body and isinstance(tree.body[-1], ast.Expr):
        expression = ast.unparse(tree.body[-1].value)
        prefix = ast.unparse(ast.Module(body=tree.body[:-1], type_ignores=[]))
        current = f"{prefix}\n_leap_result = ({expression})" if prefix else f"_leap_result = ({expression})"
    else:
        current = f"{code}\n_leap_result = None"
    replay = "\n\n".join(previous_cells)
    if replay:
        indented_replay = "\n".join(f"    {line}" for line in replay.splitlines())
        replay = (
            "import contextlib as _leap_contextlib\n"
            "import io as _leap_io\n"
            "with _leap_contextlib.redirect_stdout(_leap_io.StringIO()), "
            "_leap_contextlib.redirect_stderr(_leap_io.StringIO()):\n"
            f"{indented_replay}"
        )
    reporter = f'''
import json as _leap_json
import base64 as _leap_base64
import io as _leap_plot_io
import sys as _leap_sys
def _leap_value(value):
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (list, tuple)):
        return [_leap_value(item) for item in value[:100]]
    if isinstance(value, dict):
        return {{str(key): _leap_value(item) for key, item in list(value.items())[:100]}}
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return repr(value)[:4000]
_leap_table = None
if all(hasattr(_leap_result, attr) for attr in ("head", "columns", "to_dict")):
    _leap_head = _leap_result.head(10)
    _leap_table = {{
        "columns": [str(column) for column in _leap_head.columns],
        "rows": [{{str(key): _leap_value(item) for key, item in row.items()}} for row in _leap_head.to_dict(orient="records")],
    }}
_leap_plots = []
if "matplotlib.pyplot" in _leap_sys.modules:
    _leap_plt = _leap_sys.modules["matplotlib.pyplot"]
    for _leap_number in _leap_plt.get_fignums()[-3:]:
        _leap_buffer = _leap_plot_io.BytesIO()
        _leap_plt.figure(_leap_number).savefig(_leap_buffer, format="png", dpi=110, bbox_inches="tight")
        _leap_plots.append("data:image/png;base64," + _leap_base64.b64encode(_leap_buffer.getvalue()).decode("ascii"))
print("{RESULT_MARKER}" + _leap_json.dumps({{"result": _leap_value(_leap_result), "table_preview": _leap_table, "plots": _leap_plots}}))
'''
    return f"{replay}\n\n{current}\n{reporter}" if replay else f"{current}\n{reporter}"


def call_codapi(files: dict[str, str]) -> dict[str, Any]:
    endpoint = os.getenv("CODAPI_URL", "https://api.codapi.org/v1/exec")
    headers = {"Content-Type": "application/json"}
    token = os.getenv("CODAPI_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    payload = {
        "sandbox": os.getenv("CODAPI_SANDBOX", "python"),
        "command": "run",
        "files": files,
    }
    request = Request(
        endpoint, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
    )
    try:
        with urlopen(request, timeout=float(os.getenv("CODAPI_TIMEOUT_SECONDS", "20"))) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Codapi returned {error.code}: {detail[:500]}") from error
    except (URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Codapi is unavailable: {error}") from error


def call_docker(files: dict[str, str]) -> dict[str, Any]:
    image = os.getenv("CODE_EXECUTION_DOCKER_IMAGE", "leap-python-runtime:latest")
    timeout = float(os.getenv("CODE_EXECUTION_TIMEOUT_SECONDS", "30"))
    with tempfile.TemporaryDirectory(prefix="leap-runtime-") as workdir:
        workspace = Path(workdir)
        (workspace / "main.py").write_text(files.pop(""), encoding="utf-8")
        for filename, content in files.items():
            (workspace / filename).write_text(content, encoding="utf-8")
        command = [
            "docker", "run", "--rm", "--network", "none", "--read-only",
            "--memory", "768m", "--cpus", "1", "--pids-limit", "128",
            "--security-opt", "no-new-privileges", "--cap-drop", "ALL",
            "--tmpfs", "/tmp:rw,noexec,nosuid,size=128m",
            "--mount", f"type=bind,src={workspace},dst=/workspace,readonly",
            image,
        ]
        started = monotonic()
        try:
            completed = subprocess.run(command, text=True, capture_output=True, timeout=timeout, check=False)
        except (subprocess.TimeoutExpired, OSError) as error:
            raise RuntimeError(f"Docker execution failed: {error}") from error
    return {
        "ok": completed.returncode == 0,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "duration": round((monotonic() - started) * 1000),
        "id": "local-docker",
    }


def execution_dataset_content(content: str) -> str:
    """Keep remote execution requests below hosted proxy limits."""
    limit = int(os.getenv("CODE_EXECUTION_MAX_DATASET_BYTES", "600000"))
    if len(content.encode("utf-8")) <= limit:
        return content
    lines = content.splitlines(keepends=True)
    if not lines:
        return content
    selected = [lines[0]]
    size = len(selected[0].encode("utf-8"))
    for line in lines[1:]:
        line_size = len(line.encode("utf-8"))
        if size + line_size > limit:
            break
        selected.append(line)
        size += line_size
    return "".join(selected)


def run_code_cell(
    request: CodeExecutionRequest,
    previous_cells: list[str],
) -> CodeExecutionResult:
    dataset = dataset_for_task(request.task)
    try:
        validate_code(request.code)
        for cell in previous_cells:
            validate_code(cell)
    except UnsafeCode as error:
        return CodeExecutionResult(
            execution_id=request.execution_id, success=False, stdout="", stderr=str(error),
            result=None, table_preview=None, duration_ms=0, dataset=dataset.public(),
            replayed_cells=len(previous_cells), runtime={"engine": "codapi", "sandbox": "blocked"},
        )

    dataset_content = execution_dataset_content(dataset.path.read_text(encoding="utf-8"))
    files = {
        "": instrumented_program(previous_cells, request.code),
        dataset.runtime_filename: dataset_content,
    }
    started = monotonic()
    try:
        engine = os.getenv("CODE_EXECUTION_ENGINE", "docker")
        codapi = call_docker(files) if engine == "docker" else call_codapi(files)
    except RuntimeError as error:
        codapi = {"ok": False, "stdout": "", "stderr": str(error), "duration": 0}

    stdout = str(codapi.get("stdout", ""))
    result_value = None
    table = None
    plots: list[str] = []
    if RESULT_MARKER in stdout:
        visible_stdout, encoded_result = stdout.rsplit(RESULT_MARKER, 1)
        stdout = visible_stdout.rstrip("\n")
        try:
            structured = json.loads(encoded_result.strip())
            result_value = structured.get("result")
            table = structured.get("table_preview")
            plots = structured.get("plots") or []
        except json.JSONDecodeError:
            pass
    return CodeExecutionResult(
        execution_id=request.execution_id,
        success=bool(codapi.get("ok")),
        stdout=stdout[-20_000:],
        stderr=str(codapi.get("stderr", ""))[-20_000:],
        result=result_value,
        table_preview=table,
        plots=plots,
        duration_ms=int(codapi.get("duration") or round((monotonic() - started) * 1000)),
        dataset=dataset.public(),
        replayed_cells=len(previous_cells),
        runtime={
            "engine": engine,
            "sandbox": os.getenv("CODE_EXECUTION_DOCKER_IMAGE", "leap-python-runtime:latest") if engine == "docker" else os.getenv("CODAPI_SANDBOX", "python"),
            "execution_id": str(codapi.get("id", "")),
        },
    )
