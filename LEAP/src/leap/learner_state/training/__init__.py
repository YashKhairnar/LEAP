"""Learner-state training and evaluation."""

from .checkpointing import load_checkpoint, save_checkpoint
from .evaluation import evaluate_identity_baseline, evaluate_jepa
from .losses import cosine_prediction_loss, jepa_loss, variance_regularization
from .step import move_jepa_batch, train_jepa_step
from .trainer import fit_jepa, train_jepa_epoch

__all__ = [
    "cosine_prediction_loss",
    "evaluate_identity_baseline",
    "evaluate_jepa",
    "fit_jepa",
    "jepa_loss",
    "load_checkpoint",
    "move_jepa_batch",
    "save_checkpoint",
    "train_jepa_epoch",
    "train_jepa_step",
    "variance_regularization",
]
