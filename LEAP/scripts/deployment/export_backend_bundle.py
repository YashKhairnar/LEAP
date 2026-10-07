"""Promote a compatible set of trained LEAP artifacts into the backend bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


FILES = {
    "action_checkpoint": "outputs/action/checkpoints/experiment_one_100/best_validation.pt",
    "temporal_checkpoint": "outputs/learner_state/checkpoints/jepa_baseline/best_validation.pt",
    "concept_probe_checkpoint": "outputs/concepts/checkpoints/probe_v2/best_validation.pt",
    "action_vocabularies": "data/action/processed/action_vocabularies.json",
    "prompt_embedding_store": "data/action/features/prompt_embeddings.pt",
    "response_embedding_store": "data/observation/features/response_embeddings.pt",
    "action_config": "configs/action/experiment_one.json",
    "temporal_config": "configs/learner_state/temporal_encoder.json",
    "prompt_encoder_config": "configs/action/prompt_encoder.json",
    "concept_vocabulary": "configs/concepts/concept_vocabulary_v2.json",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-version", required=True)
    parser.add_argument("--training-dataset", required=True)
    parser.add_argument("--output", type=Path, default=Path("../backend/model_artifacts"))
    parser.add_argument("--action-checkpoint", type=Path)
    args = parser.parse_args()

    sources = {name: Path(path) for name, path in FILES.items()}
    if args.action_checkpoint is not None:
        sources["action_checkpoint"] = args.action_checkpoint
    missing = [str(path) for path in sources.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError("Missing promotion artifacts: " + ", ".join(missing))

    args.output.mkdir(parents=True, exist_ok=True)
    artifacts: dict[str, dict[str, str | int]] = {}
    for name, source in sources.items():
        suffix = "".join(source.suffixes)
        destination = args.output / f"{name}{suffix}"
        shutil.copy2(source, destination)
        artifacts[name] = {
            "file": destination.name,
            "sha256": sha256(destination),
            "bytes": destination.stat().st_size,
        }

    manifest = {
        "format_version": 1,
        "model_version": args.model_version,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "training_dataset": args.training_dataset,
        "state_dimension": 128,
        "planner_version": "world_model_one_step_experimental_v1",
        "text_encoder": "sentence-transformers/all-MiniLM-L6-v2",
        "artifacts": artifacts,
    }
    (args.output / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
