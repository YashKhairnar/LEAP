"""Generate frozen embeddings for unique instructional prompts."""

import argparse
import json
from pathlib import Path

from leap.action.data.prompt_embeddings import generate_prompt_embedding_store
from leap.action.models import PromptEncoder
from leap.shared.config import load_json_config
from leap.shared.device import select_device


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/action/prompt_encoder.json"))
    parser.add_argument("--device", choices=["cpu", "cuda", "mps"])
    args = parser.parse_args()
    config = load_json_config(args.config)
    checkpoint = str(config["checkpoint"])
    encoder = PromptEncoder.from_pretrained(
        checkpoint, device=args.device or str(select_device()), max_length=int(config["max_length"])
    )
    summary = generate_prompt_embedding_store(
        config["action_data_path"], config["output_path"], encoder,
        checkpoint=checkpoint, batch_size=int(config["batch_size"]),
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
