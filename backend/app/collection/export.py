"""Read-only, allowlisted export with provenance checks and joined observations.

No passwords, participant login codes, or authentication sessions are exported.
Model-predicted states remain provenance only, never observed outcome labels.
"""
from collections import Counter
import hashlib
import json

from ..database import connect


def learner_split(learner_id: str, seed: str = "leap-split-v1") -> str:
    bucket = int.from_bytes(hashlib.sha256(f"{seed}:{learner_id}".encode()).digest()[:4], "big") % 100
    return "train" if bucket < 70 else "validation" if bucket < 85 else "test"


def build_collection_export(learner_ids: set[str], mode: str = "pilot", seed: str = "leap-split-v1") -> dict:
    if not learner_ids:
        raise ValueError("An explicit allowlist of learner IDs is required; development accounts are not included implicitly")
    if mode not in {"development", "pilot", "study"}:
        raise ValueError("Unknown collection mode")
    records, events, assessments, code_executions = [], [], [], []
    with connect() as connection:
        # One consistent read transaction; this function does not mutate source data.
        connection.execute("BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY" if connection.postgres else "BEGIN")
        for learner in sorted(learner_ids):
            learner_events = []
            for row in connection.execute("SELECT * FROM behavior_events WHERE learner_id = ? ORDER BY session_id, sequence_index", (learner,)).fetchall():
                event = json.loads(row["payload"])
                if event.get("collection_mode") != mode:
                    continue
                event.update(learner_id=learner, sequence_index=row["sequence_index"])
                learner_events.append(event)
            events.extend(learner_events)
            presentations = {(event["session_id"], event["event_id"]): event for event in learner_events if event["event_type"] == "content_presented"}
            for row in connection.execute("SELECT payload FROM transitions WHERE learner_id = ? ORDER BY session_id, sequence_index", (learner,)).fetchall():
                transition = json.loads(row["payload"])
                if transition.get("collection_mode") != mode:
                    continue
                content_id = transition["instructional_action"]["content_id"]
                content_row = connection.execute("SELECT payload FROM content_items WHERE content_id = ?", (content_id,)).fetchone()
                content = json.loads(content_row["payload"]) if content_row else None
                issues = []
                presentation = presentations.get((transition["session_id"], transition.get("presentation_id")))
                if content is None:
                    issues.append("missing_content")
                if presentation is None:
                    issues.append("missing_presentation")
                elif presentation["data"].get("content_id") != content_id:
                    issues.append("presentation_content_mismatch")
                elif presentation["sequence_index"] >= transition["sequence_index"]:
                    issues.append("presentation_not_before_attempt")
                observation = transition["observation"]
                if observation.get("timing_version") != "visible_foreground_v1":
                    issues.append("unverified_timing")
                if observation.get("exposure_id") != transition.get("presentation_id"):
                    issues.append("exposure_id_mismatch")
                if observation.get("evidence_kind") not in {"independent", "hint_assisted", "post_feedback_retry"}:
                    issues.append("unknown_assistance")
                elif (observation.get("evidence_kind") == "independent" and (
                    observation.get("hint_used") is not False
                    or observation.get("answer_revealed_before_attempt") is not False
                    or observation["attempt"] != 1
                )):
                    issues.append("inconsistent_independence")
                decision = (content or {}).get("planner_decision") or {}
                candidates = decision.get("candidates", [])
                probabilities = decision.get("action_probabilities", [])
                probability = decision.get("selection_probability")
                chosen = decision.get("selected_index")
                valid_assignment = (
                    decision.get("assignment_policy") == "uniform_random_v1"
                    and isinstance(chosen, int) and 0 <= chosen < len(candidates)
                    and len(probabilities) == len(candidates)
                    and all(isinstance(p, (float, int)) and abs(p - 1 / len(candidates)) < 1e-8 for p in probabilities)
                    and isinstance(probability, (float, int)) and abs(probability - 1 / len(candidates)) < 1e-8
                    and candidates[chosen].get("action_type") == transition["instructional_action"]["action_type"]
                )
                if not valid_assignment:
                    issues.append("missing_or_invalid_assignment")
                records.append({
                    "learning_record": {"transition": {"payload": transition}, "content_item": {"payload": content}},
                    "quality": {"issues": issues,
                        "independent_outcome": not issues and observation.get("evidence_kind") == "independent" and observation["attempt"] == 1},
                    "split": learner_split(learner, seed),
                })
            for row in connection.execute("SELECT payload FROM task_assessments WHERE learner_id = ?", (learner,)).fetchall():
                result = json.loads(row["payload"])
                if result.get("collection_mode") == mode:
                    assessments.append({"learner_id": learner, "split": learner_split(learner, seed), **result})
            for row in connection.execute("SELECT payload FROM task_pre_assessments WHERE learner_id = ?", (learner,)).fetchall():
                result = json.loads(row["payload"])
                if result.get("collection_mode") == mode:
                    assessments.append({"learner_id": learner, "split": learner_split(learner, seed), **result})
            for row in connection.execute("SELECT payload, session_id, sequence_index FROM code_executions WHERE learner_id = ? ORDER BY session_id, sequence_index", (learner,)).fetchall():
                payload = json.loads(row["payload"])
                if payload.get("collection_mode") == mode:
                    code_executions.append({"learner_id": learner, "session_id": row["session_id"], "sequence_index": row["sequence_index"], **payload})
    issues = Counter(issue for record in records for issue in record["quality"]["issues"])
    observed = {record["learning_record"]["transition"]["payload"]["learner_id"] for record in records}
    splits = {name: sorted(learner for learner in observed if learner_split(learner, seed) == name) for name in ("train", "validation", "test")}
    return {
        "manifest": {"format_version": 1, "collection_mode": mode, "split_seed": seed, "splits": splits,
            "records": len(records), "issues": dict(issues),
            "independent_outcomes": sum(record["quality"]["independent_outcome"] for record in records),
            "missing_allowlisted_learners": sorted(learner_ids - observed),
            "empty_splits": [name for name, members in splits.items() if not members],
            "outcome_source": "actual_responses_not_predicted_states"},
        "records": records, "events": events, "assessments": assessments, "code_executions": code_executions,
    }
