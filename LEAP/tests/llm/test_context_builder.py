import json

import pytest
import torch

from leap.concepts import ConceptVocabulary
from leap.llm import ActionSpecificationCatalog, LLMContextBuilder, TutorPromptBuilder

ALL_TUTOR_ACTIONS = {
    "activate.java_concept_identification", "activate.java_output_prediction",
    "activate.java_code_explanation", "connect.concept_matching",
    "connect.comparison_selection", "connect.analogy_mapping",
    "implement.code_completion", "implement.code_debugging",
    "implement.code_construction", "learn.transfer_or_new",
    "learn.difference_explanation", "learn.concept_boundary",
    "practice.misconception_diagnosis", "practice.error_identification",
    "practice.pipeline_ordering", "review.concept_summary",
    "review.novel_transfer", "review.confidence_checkpoint",
}


def test_action_catalog_covers_application_contract():
    catalog = ActionSpecificationCatalog("configs/llm/action_specifications_v1.json")
    assert set(catalog.actions) == ALL_TUTOR_ACTIONS
    for action_type, specification in catalog.actions.items():
        assert specification["pedagogical_phase"] == action_type.split(".", 1)[0]

CATALOG_PATH = "configs/llm/action_specifications_v1.json"
VOCABULARY_PATH = "configs/concepts/concept_vocabulary_v2.json"


def _builder():
    return LLMContextBuilder(
        ActionSpecificationCatalog(CATALOG_PATH),
        ConceptVocabulary(VOCABULARY_PATH),
    )


def test_catalog_covers_every_observed_action_type():
    catalog = ActionSpecificationCatalog(CATALOG_PATH)
    with open("data/action/processed/action_data.jsonl", encoding="utf-8") as file:
        action_types = {
            json.loads(line)["action_type"] for line in file if line.strip()
        }
    assert action_types <= set(catalog.actions)


def test_context_contains_question_details_and_relevant_mastery():
    action = {
        "task": "sentiment_classification",
        "stage": "tfidf_vectorization",
        "step": "practice",
        "action_type": "practice.error_identification",
        "content_id": "content",
        "prompt": "Find the error.",
        "learning_objectives": ["tfidf_representation", "fit_transform_boundary"],
    }
    mastery = torch.linspace(0, 1, 64)
    context = _builder().build(action, mastery, {"recent_correctness": [False, True]})

    assert context["question_specification"]["question_family"] == "error_identification"
    assert {item["concept"] for item in context["target_concepts"]} == {
        "feature_representation",
        "text_vectorization",
        "preprocessing_leakage_prevention",
    }
    assert context["output_schema"]["expected_answer"] == "string"


def test_context_rejects_wrong_mastery_shape():
    action = {
        "task": "cnn",
        "stage": "build_cnn",
        "step": "activate",
        "action_type": "activate.java_code_explanation",
    }
    with pytest.raises(ValueError, match="shape"):
        _builder().build(action, torch.zeros(63), {})


def test_prompt_builder_returns_system_and_user_messages():
    messages = TutorPromptBuilder().build_messages({"selected_action": {"action_type": "x"}})
    assert [message["role"] for message in messages] == ["system", "user"]
    assert "finished, learner-facing content" in messages[0]["content"]
    assert "selected_action" in messages[1]["content"]
