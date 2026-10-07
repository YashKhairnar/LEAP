import torch
from torch import nn

class ActionEncoder(nn.Module):
    """
    Represents an action that can be taken by the tutor. 
    
    Args:  
    """
    def __init__(
        self,
        task_count: int,
        stage_count: int,
        step_count: int,
        action_type_count: int,
        content_count: int,
        categorical_dim: int = 16,
        prompt_dim: int = 384,
        action_dim: int = 32,
    ):
        super().__init__()

        self.task_embedding = nn.Embedding(task_count, categorical_dim)
        self.stage_embedding = nn.Embedding(stage_count, categorical_dim)
        self.step_embedding = nn.Embedding(step_count, categorical_dim)
        self.action_type_embedding = nn.Embedding(
            action_type_count, categorical_dim
        )
        self.content_embedding = nn.Embedding(
            content_count, categorical_dim
        )

        combined_dim = categorical_dim * 5 + prompt_dim

        self.projection = nn.Sequential(
            nn.Linear(combined_dim, 256),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(256, action_dim),
            nn.LayerNorm(action_dim),
        )

    def forward(self, batch:dict[str, torch.Tensor]) -> torch.Tensor:
        features = [
            self.task_embedding(batch['task_id']),
            self.stage_embedding(batch['stage_id']),
            self.step_embedding(batch['step_id']),
            self.action_type_embedding(batch['action_type_id']),
            self.content_embedding(batch['content_id']),
            batch['prompt_embedding']
        ]

        combined = torch.cat(features, dim =-1)
        return self.projection(combined)