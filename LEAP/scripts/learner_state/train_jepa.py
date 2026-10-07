"""Train the learner-state JEPA with validation and checkpointing."""

from __future__ import annotations

import argparse
import json
import os
import random
from pathlib import Path

os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")

import torch

from leap.shared.config import load_json_config
from leap.learner_state.data import build_jepa_dataloaders
from leap.learner_state.models import FutureStatePredictor, LearnerJEPA, TemporalLearnerEncoder
from leap.learner_state.training import evaluate_jepa, fit_jepa, load_checkpoint
from leap.shared.device import select_device


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/learner_state/jepa_baseline.json"))
    parser.add_argument(
        "--encoder-config", type=Path, default=Path("configs/learner_state/temporal_encoder.json")
    )
    parser.add_argument("--device", choices=["cpu", "cuda", "mps"])
    parser.add_argument("--epochs", type=int, help="Override total epochs")
    parser.add_argument("--max-train-batches", type=int)
    parser.add_argument("--max-validation-batches", type=int)
    parser.add_argument("--max-test-batches", type=int)
    parser.add_argument("--run-name", default="jepa_baseline")
    parser.add_argument("--resume", type=Path, help="Resume from a checkpoint")
    parser.add_argument("--skip-test", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_json_config(args.config)
    encoder_config = load_json_config(args.encoder_config)
    if args.epochs is not None:
        if args.epochs < 1:
            raise ValueError("epochs must be at least 1")
        config["epochs"] = args.epochs
    config["checkpoint_directory"] = f"outputs/learner_state/checkpoints/{args.run_name}"
    config["metrics_path"] = f"outputs/learner_state/metrics/{args.run_name}.jsonl"

    seed = int(config["seed"])
    random.seed(seed)
    torch.manual_seed(seed)
    device = torch.device(args.device) if args.device else select_device()
    print(f"Device: {device}")
    print("Building datasets and DataLoaders...")
    loaders = build_jepa_dataloaders(config)
    print(
        "Examples: "
        + ", ".join(f"{name}={len(loader.dataset):,}" for name, loader in loaders.items())
    )

    context_encoder = TemporalLearnerEncoder(**encoder_config)
    predictor = FutureStatePredictor(
        state_dim=int(encoder_config["state_dim"]),
        hidden_dim=int(config["predictor_hidden_dim"]),
        dropout=float(config["predictor_dropout"]),
    )
    model = LearnerJEPA(context_encoder, predictor).to(device)
    optimizer = torch.optim.AdamW(
        model.trainable_parameters(),
        lr=float(config["learning_rate"]),
        weight_decay=float(config["weight_decay"]),
    )

    start_epoch = 0
    best_validation_loss = float("inf")
    if args.resume:
        checkpoint = load_checkpoint(args.resume, model, optimizer, map_location=device)
        start_epoch = int(checkpoint["epoch"])
        best_validation_loss = float(checkpoint["best_validation_loss"])
        print(f"Resumed from epoch {start_epoch}: {args.resume}")

    result = fit_jepa(
        model,
        loaders,
        optimizer,
        device,
        config,
        start_epoch=start_epoch,
        best_validation_loss=best_validation_loss,
        max_train_batches=args.max_train_batches,
        max_validation_batches=args.max_validation_batches,
        append_history=args.resume is not None,
    )

    test_metrics = None
    best_path = Path(config["checkpoint_directory"]) / "best_validation.pt"
    if not args.skip_test and best_path.exists():
        load_checkpoint(best_path, model, map_location=device)
        test_metrics = evaluate_jepa(
            model,
            loaders["test"],
            device,
            variance_weight=float(config["variance_weight"]),
            minimum_std=float(config["minimum_state_std"]),
            max_batches=args.max_test_batches,
        )
        test_metrics_path = Path("outputs/learner_state/metrics") / f"{args.run_name}_test.json"
        test_metrics_path.parent.mkdir(parents=True, exist_ok=True)
        test_metrics_path.write_text(json.dumps(test_metrics, indent=2) + "\n", encoding="utf-8")
        print(f"Test: {json.dumps(test_metrics, indent=2)}")

    print(
        json.dumps(
            {
                "best_validation_loss": result["best_validation_loss"],
                "best_checkpoint": str(best_path),
                "metrics": config["metrics_path"],
                "test": test_metrics,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
