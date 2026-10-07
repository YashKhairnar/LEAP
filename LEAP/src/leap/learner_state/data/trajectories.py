"""Convert cleaned programming submissions into learner trajectories."""

from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import Any

import pandas as pd


def write_trajectories(
    frame: pd.DataFrame,
    jsonl_path: str | Path,
    statistics_path: str | Path,
    *,
    minimum_attempts: int = 2,
) -> dict[str, Any]:
    """Write one JSONL record per student/task trajectory and return summary statistics."""
    if minimum_attempts < 1:
        raise ValueError("minimum_attempts must be at least 1")

    jsonl_path = Path(jsonl_path)
    statistics_path = Path(statistics_path)
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    statistics_path.parent.mkdir(parents=True, exist_ok=True)

    stats: dict[str, Any] = {
        "total_students": 0,
        "total_tasks": 0,
        "total_trajectories": 0,
        "total_attempts": 0,
        "removed_single_attempt_trajectories": 0,
    }
    students: set[str] = set()
    tasks: set[str] = set()
    attempt_counts: list[int] = []
    correct_attempts = 0
    ending_correct = 0

    with jsonl_path.open("w", encoding="utf-8") as output:
        for (user, task_id), group in frame.groupby(["user", "unique_task_id"], sort=False):
            students.add(str(user))
            tasks.add(str(task_id))
            if len(group) < minimum_attempts:
                stats["removed_single_attempt_trajectories"] += 1
                continue

            attempts = []
            for number, row in enumerate(group.itertuples(index=False), start=1):
                is_correct = bool(row.correct)
                attempts.append(
                    {
                        "attempt_number": number,
                        "timestamp": str(row.date).replace(" ", "T"),
                        "code": row.normalized_code,
                        "correct": is_correct,
                    }
                )
                correct_attempts += int(is_correct)

            clean_task_id = str(task_id).removesuffix(".py")
            module, separator, task_name = clean_task_id.partition("_")
            record = {
                "trajectory_id": f"{user}__{task_id}",
                "student_id": user,
                "module": module if separator else "unknown",
                "task": task_name if separator else str(task_id),
                "task_id": task_id,
                "language": "python",
                "language_version": "python2",
                "attempts": attempts,
            }
            output.write(json.dumps(record, default=str) + "\n")
            stats["total_trajectories"] += 1
            stats["total_attempts"] += len(attempts)
            attempt_counts.append(len(attempts))
            ending_correct += int(attempts[-1]["correct"])

    stats["total_students"] = len(students)
    stats["total_tasks"] = len(tasks)
    if attempt_counts:
        stats.update(
            average_attempts_per_trajectory=statistics.mean(attempt_counts),
            median_attempts_per_trajectory=statistics.median(attempt_counts),
            minimum_attempts=min(attempt_counts),
            maximum_attempts=max(attempt_counts),
            correct_attempt_percentage=100 * correct_attempts / stats["total_attempts"],
            trajectories_ending_correct_percentage=100 * ending_correct / stats["total_trajectories"],
        )

    statistics_path.write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    return stats

