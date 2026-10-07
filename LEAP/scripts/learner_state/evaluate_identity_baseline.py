"""Compare JEPA future prediction against copying the current learner state."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")

import torch

from leap.shared.config import load_json_config
from leap.learner_state.data import build_jepa_dataloaders
from leap.learner_state.models import FutureStatePredictor, LearnerJEPA, TemporalLearnerEncoder
from leap.learner_state.training import evaluate_identity_baseline, load_checkpoint
from leap.shared.device import select_device


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/learner_state/jepa_baseline.json"))
    parser.add_argument(
        "--encoder-config", type=Path, default=Path("configs/learner_state/temporal_encoder.json")
    )
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=Path("outputs/learner_state/checkpoints/jepa_baseline/best_validation.pt"),
    )
    parser.add_argument("--output", type=Path, default=Path("outputs/learner_state/metrics/identity_baseline.json"))
    parser.add_argument("--device", choices=["cpu", "cuda", "mps"])
    parser.add_argument("--max-test-batches", type=int)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_json_config(args.config)
    encoder_config = load_json_config(args.encoder_config)
    device = torch.device(args.device) if args.device else select_device()

    print(f"Device: {device}")
    loaders = build_jepa_dataloaders(config)
    model = LearnerJEPA(
        TemporalLearnerEncoder(**encoder_config),
        FutureStatePredictor(
            state_dim=int(encoder_config["state_dim"]),
            hidden_dim=int(config["predictor_hidden_dim"]),
            dropout=float(config["predictor_dropout"]),
        ),
    ).to(device)
    checkpoint = load_checkpoint(args.checkpoint, model, map_location=device)
    print(f"Checkpoint epoch: {checkpoint['epoch']}")

    metrics = evaluate_identity_baseline(
        model,
        loaders["test"],
        device,
        max_batches=args.max_test_batches,
    )
    result = {
        "checkpoint": str(args.checkpoint),
        "checkpoint_epoch": int(checkpoint["epoch"]),
        "split": "test",
        **metrics,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"Saved: {args.output}")


if __name__ == "__main__":
    main()
