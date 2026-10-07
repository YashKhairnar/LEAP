"""Generate frozen embeddings for unique learner responses."""

import argparse
import json
from pathlib import Path

from leap.observation.data import generate_response_embedding_store
from leap.observation.models import ResponseTextEncoder
from leap.shared.config import load_json_config
from leap.shared.device import select_device


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/observation/response_encoder.json"))
    parser.add_argument("--device", choices=["cpu", "cuda", "mps"])
    args = parser.parse_args()
    config = load_json_config(args.config)
    checkpoint = str(config["checkpoint"])
    encoder = ResponseTextEncoder.from_pretrained(
        checkpoint, device=args.device or str(select_device()), max_length=int(config["max_length"])
    )
    print(json.dumps(generate_response_embedding_store(
        config["observation_data_path"], config["output_path"], encoder,
        checkpoint=checkpoint, batch_size=int(config["batch_size"]),
    ), indent=2))


if __name__ == "__main__":
    main()
