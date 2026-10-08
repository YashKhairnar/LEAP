"""Modal-backed Python execution service for LEAP learner code."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
from time import monotonic

import modal
from fastapi import Header, HTTPException
from pydantic import BaseModel, Field


APP_DIR = Path(__file__).resolve().parent
DATASET_DIR = APP_DIR.parent / "backend" / "datasets"
TOKEN_SECRET_NAME = os.getenv("MODAL_SANDBOX_SECRET_NAME", "leap-sandbox-secrets")

app = modal.App("leap-code-sandbox", include_source=False)

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install(
        "fastapi>=0.115,<1.0",
        "pydantic>=2.0,<3.0",
        "numpy",
        "pandas",
        "scikit-learn",
        "scipy",
        "seaborn",
        "matplotlib",
        "torch",
        "torchvision",
    )
    .add_local_dir(DATASET_DIR, remote_path="/leap-datasets", copy=True)
)


class ExecuteRequest(BaseModel):
    program: str = Field(min_length=1, max_length=20000)
    dataset_filename: str = Field(pattern=r"^[a-zA-Z0-9_.-]+$")


DATASET_FILES = {
    "reviews.csv": "sentiment_labelled_sentences_uci_v2.csv",
    "houses.csv": "ames_housing_v2.csv",
    "images.csv": "optical_digits_uci_v2.csv",
}


@app.function(
    image=image,
    timeout=45,
    cpu=1,
    memory=1024,
    block_network=True,
    restrict_modal_access=True,
    single_use_containers=True,
    secrets=[modal.Secret.from_name(TOKEN_SECRET_NAME)],
)
@modal.fastapi_endpoint(method="POST")
def execute(request: ExecuteRequest, authorization: str | None = Header(default=None)) -> dict:
    expected_token = os.getenv("MODAL_SANDBOX_TOKEN")
    if not expected_token or authorization != f"Bearer {expected_token}":
        raise HTTPException(status_code=401, detail="invalid sandbox token")
    source_filename = DATASET_FILES.get(request.dataset_filename)
    if source_filename is None:
        raise HTTPException(status_code=400, detail="unsupported dataset filename")

    started = monotonic()
    with tempfile.TemporaryDirectory(prefix="leap-exec-") as workdir:
        workspace = Path(workdir)
        (workspace / "main.py").write_text(request.program, encoding="utf-8")
        dataset_source = Path("/leap-datasets") / source_filename
        (workspace / request.dataset_filename).symlink_to(dataset_source)
        try:
            completed = subprocess.run(
                ["python", "main.py"],
                cwd=workspace,
                text=True,
                capture_output=True,
                timeout=35,
                check=False,
            )
        except subprocess.TimeoutExpired as error:
            return {
                "ok": False,
                "stdout": (error.stdout or "")[-20000:],
                "stderr": "Execution timed out after 35 seconds.",
                "duration": round((monotonic() - started) * 1000),
                "id": "modal-sandbox",
            }
    return {
        "ok": completed.returncode == 0,
        "stdout": completed.stdout[-20000:],
        "stderr": completed.stderr[-20000:],
        "duration": round((monotonic() - started) * 1000),
        "id": "modal-sandbox",
    }
