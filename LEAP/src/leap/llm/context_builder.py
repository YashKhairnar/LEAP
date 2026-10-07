"""Build structured, inspectable context for an LLM tutoring agent."""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

import torch

from leap.concepts import ConceptVocabulary

from .action_catalog import ActionSpecificationCatalog


class LLMContextBuilder:
    def __init__(
        self,
        action_catalog: ActionSpecificationCatalog,
        concept_vocabulary: ConceptVocabulary,
    ) -> None:
        self.action_catalog = action_catalog
        self.concept_vocabulary = concept_vocabulary

    def _target_concepts(self, action: dict[str, Any]) -> list[str]:
        concepts: set[str] = set()
        for objective in action.get("learning_objectives", []):
            concepts.update(
                self.concept_vocabulary.concepts_for_objective(
                    str(action["task"]), str(objective)
                )
            )
        if not concepts:
            concepts.update(
                self.concept_vocabulary.concepts_for_stage(
                    str(action["task"]), str(action["stage"])
                )
            )
        return sorted(concepts, key=self.concept_vocabulary.indices.__getitem__)

    def build(
        self,
        action: dict[str, Any],
        predicted_concept_mastery: torch.Tensor | Sequence[float],
        learner_context: dict[str, Any],
        *,
        difficulty: str = "adaptive",
    ) -> dict[str, Any]:
        mastery = torch.as_tensor(predicted_concept_mastery, dtype=torch.float32)
        if mastery.shape != (self.concept_vocabulary.capacity,):
            raise ValueError(
                f"predicted_concept_mastery must have shape "
                f"[{self.concept_vocabulary.capacity}]"
            )
        if ((mastery < 0) | (mastery > 1)).any():
            raise ValueError("predicted concept mastery must be between zero and one")

        specification = self.action_catalog.get(str(action["action_type"]))
        target_concepts = self._target_concepts(action)
        mastery_context = [
            {
                "concept": concept,
                "predicted_mastery": round(
                    float(mastery[self.concept_vocabulary.indices[concept]]), 4
                ),
            }
            for concept in target_concepts
        ]
        return {
            "context_version": "1.0",
            "learner": learner_context,
            "location": {
                "task": action["task"],
                "stage": action["stage"],
                "step": action["step"],
            },
            "selected_action": {
                "action_type": action["action_type"],
                "content_id": action.get("content_id"),
                "learning_objectives": list(action.get("learning_objectives", [])),
                "reference_prompt": action.get("prompt"),
            },
            "target_concepts": mastery_context,
            "mastery_status": "experimental_predicted_state_probe",
            "question_specification": {
                **specification,
                "difficulty": difficulty,
            },
            "generation_constraints": {
                "implement_selected_action_exactly": True,
                "focus_only_on_target_concepts": True,
                "do_not_reveal_answer_in_question": True,
                "use_learner_history_for_difficulty_only": True,
                "java_is_prior_knowledge_only": True,
                "all_machine_learning_code_must_be_python": True,
                "never_implement_machine_learning_in_java": True,
                "never_output_java_source_code_or_syntax": True,
                "all_code_snippets_must_be_python": True,
            },
            "output_schema": {
                "question": "string",
                "options": "array[string] or null",
                "expected_answer": "string",
                "hint": "string",
                "explanation": "string",
                "concepts_tested": "array[string]",
            },
        }


class TutorPromptBuilder:
    SYSTEM_PROMPT = (
        "You are an adaptive machine-learning tutor for learners with programming "
        "experience. Generate one question that exactly implements the selected "
        "instructional action. Produce finished, learner-facing content: carry out every "
        "instruction and never repeat or paraphrase an instruction as the question. "
        "Include required examples, code, choices, or lists directly in the question. "
        "Treat predicted mastery as uncertain evidence. Return valid JSON matching "
        "output_schema and no additional text."
    )

    def build_messages(self, context: dict[str, Any]) -> list[dict[str, str]]:
        return [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {
                "role": "user",
                "content": "Create the tutoring question from this context:\n"
                + json.dumps(context, indent=2)
                + "\n\nThe instructions describe content you must create. Do not copy their "
                "wording into the question. The question must contain the actual example, "
                "code, choices, or list that the learner will inspect.",
            },
        ]
