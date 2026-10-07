# Observation component

Location: `src/leap/observation/`

## Purpose

The pretrained temporal learner encoder expects a 256-D attempt representation. This
component adapts richer tutoring observations into that size.

## Encoded fields

- learner response text;
- correctness;
- score;
- attempt number;
- response time.

Response time is clipped to five minutes and log-scaled. Attempt number is clipped to ten
and normalized.

## Pipeline

```text
response text → frozen MiniLM → 384-D cached vector
numeric outcomes → 4 normalized values
                    ↓
             ObservationEncoder
                    ↓
          256-D observation vector
```

The frozen response encoder is not trained. The projection network inside
`ObservationEncoder` is trainable.

## Artifacts

- Observations: `data/observation/processed/observations.jsonl`
- Response vectors: `data/observation/features/response_embeddings.pt`

The recorded experiment dataset contains 281 observations and 117 unique responses.
These historical counts are not a live count of web-app collection. New response exports
also include assistance and exposure provenance; preserve those fields and learner splits
explicitly when preparing a new versioned training dataset.

## Commands

```bash
python scripts/observation/prepare_observation_dataset.py
python scripts/observation/generate_response_embeddings.py
```

## Status

The component produces `[batch, 256]` observation vectors. The next step is grouping these
vectors chronologically into pre-action and post-action histories for the temporal encoder.
