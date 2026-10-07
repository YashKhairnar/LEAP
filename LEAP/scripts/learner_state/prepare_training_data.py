"""Create reproducible student splits and report JEPA prefix-pair counts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from leap.shared.config import load_json_config
from leap.learner_state.data import create_student_splits, summarize_split_examples


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/learner_state/jepa_baseline.json"),
    )
    parser.add_argument("--force", action="store_true", help="Replace an existing split file")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_json_config(args.config)
    trajectory_path = Path(config["trajectory_path"])
    split_path = Path(config["split_path"])

    if split_path.exists() and not args.force:
        manifest = json.loads(split_path.read_text(encoding="utf-8"))
        print(f"Using existing split manifest: {split_path}")
    else:
        manifest = create_student_splits(
            trajectory_path,
            split_path,
            train_ratio=float(config["train_ratio"]),
            validation_ratio=float(config["validation_ratio"]),
            test_ratio=float(config["test_ratio"]),
            seed=int(config["seed"]),
        )
        print(f"Created split manifest: {split_path}")

    summary = summarize_split_examples(trajectory_path, manifest)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

