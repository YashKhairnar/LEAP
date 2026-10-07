from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any
from ..paths import BACKEND_ROOT


class ModelArtifactError(RuntimeError):
    pass


REQUIRED_ARTIFACTS = {
    "action_checkpoint",
    "temporal_checkpoint",
    "concept_probe_checkpoint",
    "action_vocabularies",
    "prompt_embedding_store",
    "response_embedding_store",
    "action_config",
    "temporal_config",
    "prompt_encoder_config",
    "concept_vocabulary",
}


def artifact_directory() -> Path:
    return Path(os.getenv(
        "LEAP_MODEL_ARTIFACT_DIR",
        str(BACKEND_ROOT / "model_artifacts"),
    )).expanduser().resolve()


def load_verified_manifest() -> tuple[Path, dict[str, Any]]:
    directory = artifact_directory()
    manifest_path = directory / "manifest.json"
    if not manifest_path.is_file():
        raise ModelArtifactError(f"model manifest is missing: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("format_version") != 1:
        raise ModelArtifactError("unsupported model artifact manifest format")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict) or not REQUIRED_ARTIFACTS.issubset(artifacts):
        raise ModelArtifactError("model artifact manifest is incomplete")
    resolved_directory = directory.resolve()
    for name, metadata in artifacts.items():
        try:
            path = (directory / metadata["file"]).resolve()
            expected_digest = metadata["sha256"]
        except (KeyError, TypeError):
            raise ModelArtifactError(f"invalid model artifact metadata: {name}") from None
        if path.parent != resolved_directory:
            raise ModelArtifactError(f"model artifact path escapes bundle: {name}")
        if not path.is_file():
            raise ModelArtifactError(f"model artifact is missing: {name}")
        digest = hashlib.sha256()
        with path.open("rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(chunk)
        if digest.hexdigest() != expected_digest:
            raise ModelArtifactError(f"model artifact checksum mismatch: {name}")
    return directory, manifest
