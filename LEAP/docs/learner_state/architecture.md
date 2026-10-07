# Model architecture

## End-to-end passive model

```text
Normalized code
      |
Frozen CodeT5+ encoder
      |
256-D code vectors + 3 metadata features
      |
TemporalLearnerEncoder E_theta
      |
current learner state z_t (128-D)
      |
FutureStatePredictor P_phi
      |
predicted future state z_hat_(t+1) (128-D)

Longer target history
      |
EMA TargetEncoder E_bar_theta
      |
target future state z_(t+1) (128-D)
```

## Temporal learner encoder

For every attempt, the encoder receives a 256-dimensional frozen code embedding and three
metadata values.

1. A metadata MLP maps 3 dimensions to 16.
2. Code and metadata representations are concatenated to 272 dimensions.
3. A fusion MLP maps each attempt to the 256-dimensional transformer space.
4. A learned `[STATE]` token is prepended.
5. Learned positional embeddings are added.
6. A two-layer, four-head Transformer encoder processes the sequence.
7. The `[STATE]` output is projected from 256 to the 128-dimensional learner state.

Key configuration:

| Parameter | Value |
|---|---:|
| Code dimension | 256 |
| Metadata dimension / hidden dimension | 3 / 16 |
| Transformer dimension | 256 |
| Transformer layers / heads | 2 / 4 |
| Feed-forward dimension | 512 |
| Learner-state dimension | 128 |
| Maximum attempts | 20 |
| Dropout | 0.1 |

## Future-state predictor

The passive predictor maps one 128-dimensional learner state to another:

```text
128 -> Linear(256) -> GELU -> Dropout(0.1)
    -> Linear(128) -> LayerNorm
```

It does not currently receive an action embedding.

## Target encoder

The target encoder begins as a deep copy of the context encoder. Its parameters have
gradients disabled and are updated after optimization using:

\[
\bar\theta \leftarrow m\bar\theta + (1-m)\theta
\]

with momentum \(m=0.996\).

This creates a slowly moving latent target and avoids directly backpropagating through the
target representation.

## What was trained on DCU

| Component | DCU update mechanism | Status |
|---|---|---|
| CodeT5+ code encoder | None; frozen offline feature extractor | Not trained |
| Temporal context encoder | Gradient descent through AdamW | Trained |
| Future-state predictor | Gradient descent through AdamW | Trained |
| Target encoder | EMA of context encoder | Updated without gradients |

`LearnerJEPA.trainable_parameters()` yields the parameters of both the context encoder and
predictor. The optimizer therefore trained both components jointly on DCU prefix pairs.

## Forward pass

For context history \(H_t\) and the longer target history \(H_{t+1}\):

\[
z_t = E_\theta(H_t)
\]

\[
\hat z_{t+1} = P_\phi(z_t)
\]

\[
z_{t+1} = E_{\bar\theta}(H_{t+1})
\]

The predictor is trained to align \(\hat z_{t+1}\) with the stop-gradient target
\(z_{t+1}\).
