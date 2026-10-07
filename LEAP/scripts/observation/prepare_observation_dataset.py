"""Prepare learner-observation records from tutoring transitions."""

import argparse
import json
from pathlib import Path

from leap.observation.data import prepare_observation_dataset


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/action/raw/transitions.json"))
    parser.add_argument("--output", type=Path, default=Path("data/observation/processed/observations.jsonl"))
    args = parser.parse_args()
    print(json.dumps(
        prepare_observation_dataset(args.input, args.output), indent=2
    ))


if __name__ == "__main__":
    main()
