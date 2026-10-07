import json

from leap.concepts import build_concept_labels


def test_concept_labels_are_chronological_and_leakage_safe(tmp_path):
    actions = [
        {
            "transition_id": "t2",
            "learner_id": "learner",
            "session_id": "session",
            "sequence_index": 2,
            "task": "sentiment_classification",
            "stage": "prediction",
            "step": "practice",
            "learning_objectives": ["held_out_prediction"],
        },
        {
            "transition_id": "t1",
            "learner_id": "learner",
            "session_id": "session",
            "sequence_index": 1,
            "task": "sentiment_classification",
            "stage": "prediction",
            "step": "learn",
            "learning_objectives": ["held_out_prediction"],
        },
    ]
    observations = [
        {
            "transition_id": "t1",
            "learner_id": "learner",
            "session_id": "session",
            "sequence_index": 1,
            "score": 1.0,
        },
        {
            "transition_id": "t2",
            "learner_id": "learner",
            "session_id": "session",
            "sequence_index": 2,
            "score": 0.0,
        },
    ]
    action_path = tmp_path / "actions.jsonl"
    observation_path = tmp_path / "observations.jsonl"
    action_path.write_text("".join(json.dumps(item) + "\n" for item in actions))
    observation_path.write_text(
        "".join(json.dumps(item) + "\n" for item in observations)
    )

    labels = build_concept_labels(
        action_path,
        observation_path,
        "configs/concepts/concept_vocabulary_v2.json",
    )
    prediction_index = labels[0]["active_concept_indices"][0]

    assert [label["transition_id"] for label in labels] == ["t1", "t2"]
    assert labels[0]["mastery_mask_before"][prediction_index] is False
    assert labels[0]["mastery_after"][prediction_index] == 1.0
    assert labels[1]["mastery_before"][prediction_index] == 1.0
    assert labels[1]["mastery_after"][prediction_index] == 0.5
    assert len(labels[0]["mastery_after"]) == 64
