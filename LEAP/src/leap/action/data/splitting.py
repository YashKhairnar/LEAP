"""Deterministic learner-level splits for tutoring transitions."""

import json
import random
from pathlib import Path

SPLITS = ("train", "validation", "test")


def create_tutoring_splits(
    observation_data_path: str | Path,
    output_path: str | Path,
    *,
    seed: int = 42,
) -> dict:
    learners: set[str] = set()
    with Path(observation_data_path).open(encoding="utf-8") as file:
        for line in file:
            if line.strip():
                learners.add(str(json.loads(line)["learner_id"]))
    if len(learners) < 3:
        raise ValueError("At least three learners are required for data splits")
    shuffled = sorted(learners)
    random.Random(seed).shuffle(shuffled)
    validation_count = max(1, round(len(shuffled) * 0.15))
    test_count = max(1, round(len(shuffled) * 0.15))
    train_count = len(shuffled) - validation_count - test_count
    if train_count < 1:
        raise ValueError("The split leaves no training learners")
    manifest = {
        "format_version": 1,
        "seed": seed,
        "total_learners": len(shuffled),
        "splits": {
            "train": shuffled[:train_count],
            "validation": shuffled[train_count:train_count + validation_count],
            "test": shuffled[train_count + validation_count:],
        },
    }
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def load_tutoring_split(path: str | Path, split: str) -> set[str]:
    if split not in SPLITS:
        raise ValueError(f"split must be one of: {', '.join(SPLITS)}")
    manifest = json.loads(Path(path).read_text(encoding="utf-8"))
    return set(map(str, manifest["splits"][split]))
