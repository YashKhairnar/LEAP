"""Run one world-model planning request from stdin for research/debugging."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from leap.planning.runtime import WorldModelRuntime


def main() -> None:
    leap_root = Path(__file__).resolve().parents[2]
    artifact_directory = Path(os.getenv(
        "LEAP_MODEL_ARTIFACT_DIR",
        str(leap_root.parent / "backend/model_artifacts"),
    ))
    runtime = WorldModelRuntime(artifact_directory)
    print(json.dumps(runtime.plan(json.load(sys.stdin))))


if __name__ == "__main__":
    main()
