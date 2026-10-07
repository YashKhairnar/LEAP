"""Prepare action-encoder records and categorical vocabularies."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from leap.action.data.preprocessing import prepare_action_dataset


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/action/raw/transitions.json"),
    )
    parser.add_argument(
        "--output", type=Path, default=Path("data/action/processed/action_data.jsonl")
    )
    parser.add_argument(
        "--vocabularies",
        type=Path,
        default=Path("data/action/processed/action_vocabularies.json"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = prepare_action_dataset(args.input, args.output, args.vocabularies)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
