# Action component

Location: `src/leap/action/`

## Purpose

This component represents an instructional action and predicts its effect when combined
with a learner state.

## Input fields

Only information known when the action is presented is encoded:

- `location_before.task`;
- `location_before.stage`;
- `location_before.step`;
- `instructional_action.action_type`;
- `instructional_action.content_id`;
- presented question prompt.

Post-action response, correctness, progression, and actual `location_after` are excluded to
prevent future-information leakage.

## Pipeline

```text
Raw transition export
      ↓
preprocessing.py
      ↓
categorical vocabularies + action JSONL

unique prompts → frozen MiniLM → cached 384-D prompt embeddings

five categorical embeddings + prompt embedding
      ↓
ActionEncoder
      ↓
32-D action vector
```

`ActionConditionedPredictor` concatenates the 128-D learner state with the 32-D action and
predicts a residual update in the 128-D learner-state space.

`ActionConditionedJEPA` now connects the full pipeline. The context branch encodes the
learner's prior observations, the action branch encodes the selected tutoring action, and
the predictor estimates the learner state after that action. Separate frozen target
observation and temporal encoders supply the training target and are updated with EMA.
The pretrained temporal encoder is frozen by default for Experiment 1.

## Artifacts

- Raw transitions: `data/action/raw/transitions.json`
- Processed actions: `data/action/processed/action_data.jsonl`
- Vocabularies: `data/action/processed/action_vocabularies.json`
- Prompt vectors: `data/action/features/prompt_embeddings.pt`

The recorded experiment dataset contains 281 actions, 60 unique prompts, 12 observed action types, and 122
observed content IDs. Saved vocabulary sizes are one larger because index zero is `<UNK>`.
These are historical artifact counts, not a live count of app collection. New exports must
be prepared under a separate version with explicit quality and learner-split handling; see
the [collection guide](../../../docs/collection.md).

## Commands

```bash
python scripts/action/prepare_action_dataset.py
python scripts/action/generate_prompt_embeddings.py
python scripts/action/train_experiment_one.py
```

## Experiment 1

Experiment 1 trains the observation encoder, 32-D action encoder, and action-conditioned
predictor while keeping the pretrained DCU temporal learner encoder frozen. Target
observation and temporal encoders are updated using EMA with momentum 0.996.

Three runs were completed on the learner-level split:

| Requested epochs | Best epoch | Best validation loss | Test loss | Prediction loss | Variance loss | State std |
|---:|---:|---:|---:|---:|---:|---:|
| 30 | 6 | 0.2602 | 0.0654 | 0.0060 | 0.5940 | 0.4264 |
| 100 | 53 | 0.2322 | 0.0458 | 0.0176 | 0.2825 | 0.7748 |
| 200 | 53 | 0.2322 | 0.0458 | 0.0176 | 0.2825 | 0.7748 |

The 100- and 200-epoch runs selected effectively identical epoch-53 checkpoints. Extending
training beyond 100 epochs therefore provided no measurable improvement. The longer run's
artifact directory is named `experiment_one_500`, although the recorded metrics contain
200 epochs.

- Best model: `outputs/action/checkpoints/experiment_one/best_validation.pt`
- Latest model: `outputs/action/checkpoints/experiment_one/latest.pt`
- Epoch metrics: `outputs/action/metrics/experiment_one.jsonl`
- Test metrics: `outputs/action/metrics/experiment_one_test.json`
- 100-epoch metrics: `outputs/action/metrics/experiment_one_100.jsonl`
- 200-epoch metrics: `outputs/action/metrics/experiment_one_500.jsonl`

The no-action comparison is complete. The next evaluation should add early stopping and
verify that changing the action while holding the learner state fixed materially changes
the predicted next state.

## No-action baseline

The fair no-action baseline was trained for 100 epochs using the same tutoring histories,
targets, learner split, pretrained frozen temporal encoder, optimizer settings, and EMA
targets. It removes all action fields and uses a residual predictor conditioned only on the
current learner state.

| Model | Best validation loss | Test loss | Prediction loss | Variance loss | State std |
|---|---:|---:|---:|---:|---:|
| Action-conditioned (100 epochs) | 0.2322 | 0.0458 | 0.0176 | 0.2825 | 0.7748 |
| No-action (100 epochs) | 0.1532 | 0.0499 | 0.0164 | 0.3353 | 0.7114 |

The action-conditioned model has slightly better total test loss and state diversity, but
the no-action baseline has slightly better prediction loss. Therefore Experiment 1 does
not yet demonstrate that action information improves next-state prediction. This result
must also be interpreted cautiously because validation contains only seven transitions.

- Baseline model: `outputs/action/checkpoints/no_action_baseline/best_validation.pt`
- Baseline metrics: `outputs/action/metrics/no_action_baseline.jsonl`
- Baseline test metrics: `outputs/action/metrics/no_action_baseline_test.json`

Because validation contains only seven transitions, these measurements verify the pipeline
but are not yet a reliable estimate of generalization.

## Status

`ActionDataset`, `ActionEncoder`, `ActionConditionedPredictor`, and
`ActionConditionedJEPA` are implemented and tested. `ActionConditionedDataset` joins
actions and observations by `transition_id`,
groups them by learner/session, and creates leakage-safe context/target histories.

The deterministic learner-level split currently contains:

| Split | Learners | Transitions |
|---|---:|---:|
| Train | 4 | 231 |
| Validation | 1 | 7 |
| Test | 1 | 43 |

The validation set is extremely small, so Experiment 1 results must be treated as a pipeline
demonstration rather than a reliable generalization estimate.
