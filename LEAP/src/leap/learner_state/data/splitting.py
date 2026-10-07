"""Deterministic student-level splits for leakage-free experiments."""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any


SPLIT_NAMES = ("train", "validation", "test")


def collect_student_ids(trajectory_path: str | Path) -> list[str]:
    """Return sorted unique student identifiers from trajectory JSONL."""
    students: set[str] = set()
    with Path(trajectory_path).open(encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue
            try:
                trajectory = json.loads(line)
                students.add(str(trajectory["student_id"]))
            except (json.JSONDecodeError, KeyError) as error:
                raise ValueError(f"Invalid trajectory on line {line_number}") from error
    return sorted(students)


def create_student_splits(
    trajectory_path: str | Path,
    output_path: str | Path,
    *,
    train_ratio: float = 0.70,
    validation_ratio: float = 0.15,
    test_ratio: float = 0.15,
    seed: int = 42,
) -> dict[str, Any]:
    """Shuffle students reproducibly and save mutually exclusive split membership."""
    ratios = (train_ratio, validation_ratio, test_ratio)
    if any(ratio <= 0 for ratio in ratios):
        raise ValueError("All split ratios must be positive")
    if abs(sum(ratios) - 1.0) > 1e-8:
        raise ValueError("Split ratios must sum to 1.0")

    students = collect_student_ids(trajectory_path)
    if len(students) < 3:
        raise ValueError("At least three students are required for train/validation/test splits")
    random.Random(seed).shuffle(students)

    train_end = int(len(students) * train_ratio)
    validation_end = train_end + int(len(students) * validation_ratio)
    splits = {
        "train": students[:train_end],
        "validation": students[train_end:validation_end],
        "test": students[validation_end:],
    }
    if any(not split for split in splits.values()):
        raise ValueError("A split is empty; use more students or different ratios")

    manifest = {
        "format_version": 1,
        "seed": seed,
        "ratios": {
            "train": train_ratio,
            "validation": validation_ratio,
            "test": test_ratio,
        },
        "total_students": len(students),
        "splits": splits,
    }
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def load_student_split(path: str | Path, split: str) -> set[str]:
    """Load one split's student IDs and validate the saved manifest."""
    if split not in SPLIT_NAMES:
        raise ValueError(f"split must be one of: {', '.join(SPLIT_NAMES)}")
    manifest = json.loads(Path(path).read_text(encoding="utf-8"))
    if manifest.get("format_version") != 1:
        raise ValueError(f"Unsupported split format version: {manifest.get('format_version')}")

    split_sets = {name: set(map(str, manifest["splits"][name])) for name in SPLIT_NAMES}
    if any(split_sets[left] & split_sets[right] for left in SPLIT_NAMES for right in SPLIT_NAMES if left < right):
        raise ValueError("Student split manifest contains overlapping students")
    return split_sets[split]


def summarize_split_examples(
    trajectory_path: str | Path,
    manifest: dict[str, Any],
) -> dict[str, dict[str, int]]:
    """Count students, trajectories, and next-attempt prefix pairs per split."""
    membership = {
        student: split
        for split, students in manifest["splits"].items()
        for student in map(str, students)
    }
    summary = {
        split: {"students": len(manifest["splits"][split]), "trajectories": 0, "examples": 0}
        for split in SPLIT_NAMES
    }
    with Path(trajectory_path).open(encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue
            trajectory = json.loads(line)
            split = membership[str(trajectory["student_id"])]
            summary[split]["trajectories"] += 1
            summary[split]["examples"] += max(0, len(trajectory["attempts"]) - 1)
    return summary

