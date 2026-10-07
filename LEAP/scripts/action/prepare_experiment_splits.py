"""Create deterministic learner-level splits for tutoring transitions."""

import argparse
import json
from pathlib import Path

from leap.action.data import create_tutoring_splits


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--observations",
        type=Path,
        default=Path("data/observation/processed/observations.jsonl"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/action/processed/student_splits.json"),
    )
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    print(json.dumps(
        create_tutoring_splits(args.observations, args.output, seed=args.seed), indent=2
    ))


if __name__ == "__main__":
    main()
