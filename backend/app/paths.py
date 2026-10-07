"""Stable runtime asset paths, independent of feature-package nesting."""
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
