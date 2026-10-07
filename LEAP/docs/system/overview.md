# Project overview

Implementation status reviewed 2026-09-14. This page describes the research model; see
[application status](../../../docs/status.md) for lesson UI and collection readiness.

## Research motivation

LEAP is being developed as an agentic conceptual-bridge tutor for learners moving from
imperative programming concepts to machine-learning concepts. The long-term system should
do more than answer questions: it should estimate a learner's conceptual state, predict
how that state may change under alternative teaching actions, and use those predictions to
plan instruction.

The intended research contribution is a learner world model that supports conceptual
transfer and pedagogical planning, rather than a general-purpose chatbot or RAG wrapper.

## Long-term formulation

Let:

- \(H_t\) be the learner's interaction history;
- \(z_t\) be a latent learner or belief state;
- \(a_t\) be a teaching action;
- \(z_{t+1}\) be the state after the learner responds.

The eventual action-conditioned dynamics model is:

\[
z_t = E_\theta(H_t)
\]

\[
\hat z_{t+1} = P_\phi(z_t, a_t)
\]

Because true knowledge is hidden and responses are noisy observations, the latent state is
best interpreted as a learner **belief state**, not a direct measurement of cognition.

## Completed scope

The repository implements the passive DCU pretraining stage and the first tutoring-domain
action-conditioned experiment:

1. Clean raw Python submissions.
2. Group chronological attempts into student-task trajectories.
3. Encode unique code submissions with frozen CodeT5+.
4. Create deterministic, student-disjoint train/validation/test splits.
5. Convert each trajectory into history/next-attempt prefix pairs.
6. Train a temporal learner encoder and future-state predictor jointly.
7. Maintain a frozen target encoder using exponential moving average (EMA).
8. Save latest and best-validation checkpoints.
9. Evaluate latent next-state prediction on the held-out test students.
10. Compare the predictor against an identity baseline that simply copies the current state.
11. Encode tutoring observations and instructional actions.
12. Train an action-conditioned next-state predictor with EMA targets.
13. Compare it with a tutoring-domain no-action baseline.
14. Select among three candidate actions using one-step planning.
15. Map task objectives into a generic 64-concept ontology and train a linear state probe.

## Current model boundary

The tutoring predictor learns:

\[
P_\phi(z_t, a_t) \rightarrow \hat z_{t+1}
\]

It models how a learner's latent representation may change after a recorded instructional
action. The one-step planner can rank candidate actions, but the current data does not show
that action conditioning predicts better than the no-action baseline. The 64-concept probe
is also inconclusive. The system therefore demonstrates the complete research pipeline,
not an effective or validated tutoring policy.

## Project stage

| Stage | Status |
|---|---|
| DCU ingestion and cleaning | Complete |
| Learner trajectory construction | Complete |
| Frozen code embedding generation | Complete |
| Passive learner-state JEPA | Complete |
| Held-out evaluation and identity baseline | Complete |
| Rich tutoring-data schema | Complete for schema 2.1 |
| Action preprocessing and prompt embeddings | Complete |
| Action encoder | Complete |
| Observation preprocessing and response embeddings | Complete |
| Observation encoder | Complete |
| Action-conditioned predictor | Complete |
| Chronological action-conditioned dataset | Complete |
| Joint fine-tuning loop | Complete for Experiment 1 |
| No-action comparison | Complete |
| One-step teaching planner | Complete as pipeline demo |
| Generic 64-concept ontology and labels | Complete |
| Current-state concept probe V1 | Complete; mixed/inconclusive result |
| Predicted-state concept probe V2 | Complete and planner-integrated; below baseline |
| LLM action specification and context builder | Complete |
| Online inference host and bundle validation | Implemented; shadow-only in the app |
| Uniform action collection and provenance | Implemented; technical pilot needed |
| Quality-audited participant export | Implemented; training integration still explicit |
| Validated adaptive instructional policy | Future work |
| Online learner-specific parameter adaptation | Future work |

## Component organization

Implementation and artifacts are organized by research component:

- `leap.code_embeddings`: frozen code representation generation;
- `leap.learner_state`: DCU preprocessing, JEPA models, training, and evaluation;
- `leap.action`: transition preprocessing, prompt features, and action modeling;
- `leap.observation`: response preprocessing, response features, and observation adaptation;
- `leap.concepts`: generic ML ontology, weak mastery labels, and concept probe;
- `leap.planning`: one-step candidate-action planning;
- `leap.llm`: action specifications and structured tutoring-content prompts;
- `leap.shared`: configuration and device utilities.

## Connection to the web application

The sibling `model_service/` hosts `leap.planning.runtime.WorldModelRuntime`. The application
backend calls it through `backend/app/planning/client.py`, then uniformly randomizes the
delivered action. The selected action conditions generation in `backend/app/tutoring/generator.py`;
fixed code/experiments and final MCQs are authored separately from generated prose/questions.

The backend saves exact generated content and responses, visible-question timing and
assistance labels. Audited exports use the existing `learning_record` envelope, but their
quality and learner-split fields require explicit handling in the training workflow. The
current goal is handcrafted, candidate prompts are action descriptions before generation,
and recommendations remain experimental; none of these is a validated mastery measure.
