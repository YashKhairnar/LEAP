from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from ..models import CodeEvaluationResult


def _limits() -> None:
    try:
        import resource
        resource.setrlimit(resource.RLIMIT_CPU, (1, 1))
        resource.setrlimit(resource.RLIMIT_AS, (128 * 1024 * 1024, 128 * 1024 * 1024))
        resource.setrlimit(resource.RLIMIT_FSIZE, (1024 * 1024, 1024 * 1024))
        if hasattr(resource, "RLIMIT_NPROC"): resource.setrlimit(resource.RLIMIT_NPROC, (1, 1))
    except (ImportError, OSError, ValueError):
        pass


def evaluate_code(evaluator_id: str, code: str) -> CodeEvaluationResult:
    runner = Path(__file__).with_name("runner.py")
    with tempfile.TemporaryDirectory(prefix="leap-code-") as workdir:
        try:
            completed = subprocess.run(
                [sys.executable, "-I", "-S", str(runner), evaluator_id],
                input=json.dumps({"code": code}), text=True, capture_output=True,
                cwd=workdir, timeout=2, env={"PATH": os.environ.get("PATH", "")},
                preexec_fn=_limits if os.name == "posix" else None, check=False,
            )
        except subprocess.TimeoutExpired:
            return CodeEvaluationResult(correct=False, feedback="Execution timed out. Use direct statements without long-running work.")
    if completed.returncode != 0:
        return CodeEvaluationResult(correct=False, feedback="The sandbox stopped the program because it exceeded a safety limit.")
    try:
        return CodeEvaluationResult.model_validate_json(completed.stdout)
    except ValueError:
        return CodeEvaluationResult(correct=False, feedback="The sandbox could not evaluate this submission.")
