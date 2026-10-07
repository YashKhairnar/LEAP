"""Dataset of categorical action fields and frozen prompt embeddings."""

import json
from pathlib import Path
from typing import ClassVar

import torch
from torch.utils.data import Dataset

from .prompt_embeddings import PromptEmbeddingLookup


class ActionDataset(Dataset):
    fields = ("task", "stage", "step", "action_type", "content_id")
    output_names: ClassVar[dict[str, str]] = {
        "task": "task_id",
        "stage": "stage_id",
        "step": "step_id",
        "action_type": "action_type_id",
        "content_id": "content_id",
    }

    def __init__(self, data_path, vocabulary_path, prompt_embedding_path) -> None:
        with Path(data_path).open(encoding="utf-8") as file:
            self.data = [json.loads(line) for line in file if line.strip()]
        with Path(vocabulary_path).open(encoding="utf-8") as file:
            self.vocabularies = json.load(file)
        self.prompt_embeddings = PromptEmbeddingLookup(prompt_embedding_path)

    def __len__(self) -> int:
        return len(self.data)

    def __getitem__(self, index: int) -> dict[str, torch.Tensor]:
        record = self.data[index]
        item = {
            self.output_names[field]: torch.tensor(
                self.vocabularies[field].get(record[field], self.vocabularies[field]["<UNK>"]),
                dtype=torch.long,
            )
            for field in self.fields
        }
        item["prompt_embedding"] = self.prompt_embeddings.get_prompt(record["prompt"])
        return item
