"""Generate frozen CodeT5+ embeddings for unique trajectory attempts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from leap.shared.config import load_json_config
from leap.code_embeddings.store import generate_embedding_store
from leap.code_embeddings import CodeEncoder
from leap.shared.device import select_device


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/code_embeddings/code_encoder.json"),
        help="JSON code-encoder configuration",
    )
    parser.add_argument("--input", type=Path, help="Override the trajectory JSONL path")
    parser.add_argument("--output", type=Path, help="Override the embedding output path")
    parser.add_argument("--batch-size", type=int, help="Override the encoder batch size")
    parser.add_argument("--device", choices=["cpu", "cuda", "mps"], help="Override device selection")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_json_config(args.config)
    checkpoint = str(config["checkpoint"])
    input_path = args.input or Path(config["trajectory_path"])
    output_path = args.output or Path(config["output_path"])
    batch_size = args.batch_size or int(config["batch_size"])
    device = args.device or str(select_device())

    print(f"Loading {checkpoint} on {device}...")
    encoder = CodeEncoder.from_pretrained(
        checkpoint,
        device=device,
        max_length=int(config["max_length"]),
    )
    summary = generate_embedding_store(
        input_path,
        output_path,
        encoder,
        checkpoint=checkpoint,
        batch_size=batch_size,
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
