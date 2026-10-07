import torch
from torch import nn

from leap.planning import OneStepPlanner


class _ActionEncoder(nn.Module):
    def forward(self, batch):
        return batch["action_type_id"].float().unsqueeze(-1)


class _Predictor(nn.Module):
    def forward(self, state, action):
        result = state.clone()
        result[:, 0] = action[:, 0]
        return result


class _Model(nn.Module):
    def __init__(self):
        super().__init__()
        self.action_encoder = _ActionEncoder()
        self.predictor = _Predictor()


class _Probe(nn.Module):
    def forward(self, states):
        return states


def _candidates():
    ids = torch.tensor([[0, 1, 2], [0, 1, 2]])
    return {
        "task_id": ids,
        "stage_id": ids,
        "step_id": ids,
        "action_type_id": ids,
        "content_id": ids,
        "prompt_embedding": torch.zeros(2, 3, 4),
    }


def test_planner_selects_closest_valid_action():
    planner = OneStepPlanner(_Model(), distance="euclidean")
    current = torch.zeros(2, 2)
    goals = torch.tensor([[1.1, 0.0], [2.0, 0.0]])
    valid = torch.tensor([[True, True, True], [True, True, False]])

    result = planner(current, _candidates(), goals, valid)

    assert result["selected_indices"].tolist() == [1, 1]
    assert result["selected_actions"]["action_type_id"].tolist() == [1, 1]
    assert result["candidate_predicted_states"].shape == (2, 3, 2)


def test_planner_accepts_one_shared_goal():
    planner = OneStepPlanner(_Model(), distance="euclidean")
    result = planner(torch.zeros(2, 2), _candidates(), torch.tensor([2.0, 0.0]))
    assert result["selected_indices"].tolist() == [2, 2]


def test_planner_decodes_predicted_states_when_probe_is_present():
    planner = OneStepPlanner(_Model(), distance="euclidean", concept_probe=_Probe())
    result = planner(torch.zeros(2, 2), _candidates(), torch.tensor([2.0, 0.0]))

    assert result["candidate_concept_mastery"].shape == (2, 3, 2)
    assert result["selected_concept_mastery"].shape == (2, 2)
