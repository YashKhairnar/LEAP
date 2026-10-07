# Learner-state component

Location: `src/leap/learner_state/`

## Purpose

This component learns a passive latent learner state from chronological DCU programming
attempts and predicts the state after the next attempt.

```text
attempt history H_t → TemporalLearnerEncoder → z_t [128]
z_t → FutureStatePredictor → predicted z_(t+1) [128]
H_(t+1) → EMA TargetEncoder → target z_(t+1) [128]
```

## Packages

- `data/`: DCU loading, cleaning, trajectories, splits, prefix pairs, and DataLoaders;
- `models/`: temporal encoder, passive predictor, target encoder, and JEPA composition;
- `training/`: losses, training steps, checkpoints, evaluation, and epoch orchestration.

## Detailed documents

- [Data pipeline](data-pipeline.md)
- [Architecture](architecture.md)
- [Training and results](training-results.md)

## Status

The 20-epoch baseline is complete. The best checkpoint is epoch 8 and remains available at
`outputs/learner_state/checkpoints/jepa_baseline/best_validation.pt`.

The temporal encoder is also reused, frozen, by the tutoring-domain action-conditioned
model. A post-hoc linear probe now tests whether its 128-D tutoring states contain the 64
generic ML mastery concepts. Results are mixed: the probe improves test BCE over a
smoothed mean baseline but has worse MAE. See the [concept documentation](../concepts/README.md).
