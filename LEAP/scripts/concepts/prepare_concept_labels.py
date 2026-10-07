"""Generate 64-D concept evidence and mastery labels from tutoring transitions."""

import argparse
import json
from pathlib import Path

from leap.concepts import write_concept_labels


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--actions",
        type=Path,
        default=Path("data/action/processed/action_data.jsonl"),
    )
    parser.add_argument(
        "--observations",
        type=Path,
        default=Path("data/observation/processed/observations.jsonl"),
    )
    parser.add_argument(
        "--vocabulary",
        type=Path,
        default=Path("configs/concepts/concept_vocabulary_v2.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/concepts/processed/concept_labels.jsonl"),
    )
    args = parser.parse_args()
    result = write_concept_labels(
        args.actions,
        args.observations,
        args.vocabulary,
        args.output,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
