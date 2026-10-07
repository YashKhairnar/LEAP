from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..paths import BACKEND_ROOT

DATASET_ROOT = BACKEND_ROOT / "datasets"


@dataclass(frozen=True)
class DatasetSpec:
    dataset_id: str
    version: str
    task: str
    filename: str
    runtime_filename: str
    target: str
    features: tuple[str, ...]
    description: str

    @property
    def path(self) -> Path:
        return DATASET_ROOT / self.filename

    def public(self) -> dict[str, Any]:
        with self.path.open(newline="", encoding="utf-8") as file:
            rows = list(csv.DictReader(file))
        return {
            "dataset_id": self.dataset_id,
            "version": self.version,
            "task": self.task,
            "filename": self.filename,
            "runtime_filename": self.runtime_filename,
            "target": self.target,
            "features": list(self.features),
            "description": self.description,
            "columns": list(rows[0]) if rows else [],
            "row_count": len(rows),
            "preview": rows[:5],
        }


DATASETS = {
    "sentiment_classification": DatasetSpec(
        "uci_sentiment_labelled_sentences", "2", "sentiment_classification", "sentiment_labelled_sentences_uci_v2.csv",
        "reviews.csv", "sentiment", ("review", "source"), "All 3,000 labeled Amazon, IMDb, and Yelp sentences from the UCI Sentiment Labelled Sentences dataset (CC BY 4.0).",
    ),
    "sentiment": DatasetSpec(
        "uci_sentiment_labelled_sentences", "2", "sentiment_classification", "sentiment_labelled_sentences_uci_v2.csv",
        "reviews.csv", "sentiment", ("review", "source"), "All 3,000 labeled Amazon, IMDb, and Yelp sentences from the UCI Sentiment Labelled Sentences dataset (CC BY 4.0).",
    ),
    "regression": DatasetSpec(
        "ames_housing", "2", "regression", "ames_housing_v2.csv",
        "houses.csv", "price", ("bedrooms", "bathrooms", "square_feet", "age_years"),
        "All 2,930 Ames, Iowa property sales, reduced to four explanatory features and the recorded sale price.",
    ),
    "cnn": DatasetSpec(
        "uci_optical_digits", "2", "cnn", "optical_digits_uci_v2.csv",
        "images.csv", "label", tuple(f"pixel_{index}" for index in range(64)),
        "All 5,620 UCI Optical Digits examples represented as real 8×8 image intensity grids (CC BY 4.0).",
    ),
}


def dataset_for_task(task: str) -> DatasetSpec:
    try:
        return DATASETS[task]
    except KeyError:
        raise ValueError(f"no executable dataset is registered for task: {task}") from None
