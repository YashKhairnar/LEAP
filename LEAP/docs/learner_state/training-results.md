# Training and results

## Training objective

The prediction loss is cosine distance:

\[
\mathcal L_{pred} = 1 - \cos(\hat z_{t+1}, \operatorname{sg}(z_{t+1}))
\]

To discourage a collapsed context representation, the implementation also penalizes state
dimensions whose batch standard deviation falls below 1.0:

\[
\mathcal L = \mathcal L_{pred} + 0.1\mathcal L_{variance}
\]

The reported `cosine_similarity` in the training and evaluation logs is
`1 - prediction_loss`.

## Experiment configuration

| Hyperparameter | Value |
|---|---:|
| Random seed | 42 |
| Batch size | 32 |
| Epochs | 20 |
| Optimizer | AdamW |
| Learning rate | 0.0001 |
| Weight decay | 0.01 |
| Target EMA momentum | 0.996 |
| Variance weight | 0.1 |
| Minimum state standard deviation | 1.0 |
| Gradient clipping norm | 1.0 |
| Predictor hidden dimension | 256 |
| Predictor dropout | 0.1 |

Training uses shuffled training batches and deterministic student splits. Validation does
not perform optimizer or target-encoder updates. The best-validation and latest checkpoints
are maintained separately.

## Completed run

The full `jepa_baseline` run completed 20 epochs. The final epoch recorded:

| Metric | Train | Validation |
|---|---:|---:|
| Total loss | 0.00433 | 0.01224 |
| Prediction loss | 0.00430 | 0.00262 |
| Cosine similarity | 0.99570 | 0.99738 |
| Mean context-state standard deviation | 1.21316 | 1.02710 |

The selected best-validation checkpoint is from epoch 8, demonstrating that checkpoint
selection was based on validation loss rather than the last epoch.

## Held-out test result

The best checkpoint was evaluated on 33,861 prefix pairs from 77 held-out students:

| Metric | Value |
|---|---:|
| Test loss | 0.01149 |
| Prediction loss | 0.00191 |
| Variance loss | 0.09588 |
| Context-state standard deviation | 1.01104 |
| Predicted-target cosine similarity | 0.99809 |

## Identity-baseline comparison

The identity baseline uses the unchanged current learner state \(z_t\) as the prediction
for \(z_{t+1}\). This checks whether the learned predictor improves over merely exploiting
the similarity of consecutive states.

| Metric | Value |
|---|---:|
| Predictor cosine similarity | 0.99809 |
| Identity cosine similarity | 0.83470 |
| Mean improvement | 0.16339 |
| Median improvement | 0.00966 |
| Improvement standard error | 0.00257 |
| 95% confidence interval | [0.15836, 0.16843] |
| Predictor win rate | 76.92% |
| Tie rate | 0% |

These results show that the predictor usually aligns more closely with the target state than
copying the current state. They do not by themselves establish that the latent space is
conceptually interpretable or that a tutor using it improves student learning.

## Artifacts

- `outputs/learner_state/checkpoints/jepa_baseline/best_validation.pt`
- `outputs/learner_state/checkpoints/jepa_baseline/latest.pt`
- `outputs/learner_state/metrics/jepa_baseline.jsonl`
- `outputs/learner_state/metrics/jepa_baseline_test.json`
- `outputs/learner_state/metrics/identity_baseline.json`

## Verification status

The repository includes unit tests for configuration, preprocessing, datasets, embeddings,
the temporal encoder, JEPA composition, and the identity baseline. During this documentation
update the tests could not be rerun because `pytest` is not installed in the active shell's
Python environment. This is an environment limitation, not a recorded test failure.
