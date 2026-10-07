# Code-embeddings component

Location: `src/leap/code_embeddings/`

## Purpose

This component converts normalized Python submissions into fixed 256-D CodeT5+
representations used by the DCU learner-state model.

## Files

- `encoder.py`: frozen `Salesforce/codet5p-110m-embedding` wrapper;
- `store.py`: SHA-256 deduplication, batch generation, persistence, and lookup.

## Data flow

```text
DCU normalized code
      ↓
SHA-256 deduplication
      ↓
Frozen CodeT5+
      ↓
data/dcu/features/code_embeddings.pt
```

The embedding model is never trained by the JEPA optimizer. Unique submissions are encoded
once and retrieved by their normalized-code hash.

## Configuration and command

- Configuration: `configs/code_embeddings/code_encoder.json`
- Script: `scripts/code_embeddings/generate_embeddings.py`

```bash
python scripts/code_embeddings/generate_embeddings.py
```
