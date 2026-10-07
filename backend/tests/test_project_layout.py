"""Guard asset and isolated-runner paths when reorganizing feature packages."""
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from app.database import DEFAULT_DATABASE
from app.execution.datasets import DATASET_ROOT, dataset_for_task
from app.execution.sandbox import evaluate_code
from app.paths import BACKEND_ROOT
from app.planning.artifacts import artifact_directory


class ProjectLayoutTests(unittest.TestCase):
    def test_runtime_assets_remain_under_backend_root(self):
        self.assertEqual(BACKEND_ROOT, Path(__file__).resolve().parents[1])
        self.assertEqual(DEFAULT_DATABASE, BACKEND_ROOT / "data" / "leap.db")
        self.assertEqual(DATASET_ROOT, BACKEND_ROOT / "datasets")
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(artifact_directory(), BACKEND_ROOT / "model_artifacts")
        for task in ("sentiment_classification", "cnn", "regression"):
            self.assertIsNotNone(dataset_for_task(task))

    def test_isolated_runner_is_still_executable_after_move(self):
        result = evaluate_code("data_loading", 'import pandas as pd\ndf = pd.read_csv("reviews.csv")')
        self.assertTrue(result.correct, result.feedback)
