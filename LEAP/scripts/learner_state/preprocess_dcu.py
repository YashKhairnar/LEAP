"""Create cleaned learner trajectories from the DCU submissions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from leap.shared.config import load_json_config
from leap.learner_state.data import load_dcu_submissions, prepare_dcu_submissions, write_trajectories


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/learner_state/dcu.json"),
        help="JSON data configuration file",
    )
    parser.add_argument("--input", type=Path, help="Override the configured input path")
    parser.add_argument("--output-dir", type=Path, help="Override the configured output directory")
    parser.add_argument(
        "--minimum-attempts", type=int, help="Override the configured minimum trajectory length"
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_json_config(args.config)
    input_path = args.input or Path(config["input_path"])
    output_directory = args.output_dir or Path(config["output_directory"])
    minimum_attempts = (
        args.minimum_attempts
        if args.minimum_attempts is not None
        else int(config["minimum_attempts"])
    )

    cleaned = prepare_dcu_submissions(load_dcu_submissions(input_path))
    stats = write_trajectories(
        cleaned,
        output_directory / "trajectories.jsonl",
        output_directory / "trajectory_statistics.json",
        minimum_attempts=minimum_attempts,
    )
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
