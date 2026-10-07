# Data pipeline

## Source data

The completed pipeline uses DCU programming submissions from
`data/dcu/raw/programming_data.json`. The expected source fields include student, module, task,
timestamp, uploaded code, file extension, and correctness.

The configured input and output locations are in `configs/learner_state/dcu.json`.

## Cleaning

`prepare_dcu_submissions` performs the following operations:

1. Validates required columns.
2. Removes unused academic-year and IP fields when present.
3. Drops records missing required values.
4. Keeps Python files only.
5. Normalizes line endings and tabs.
6. Removes shebangs and comments while attempting to preserve hashes inside strings.
7. Removes repeated blank lines and trailing whitespace.
8. Sorts attempts chronologically by student and task.
9. Removes repeated normalized submissions within the same student-task pair.

Incomplete or syntactically invalid student code is supported through a fallback comment
remover.

## Trajectory construction

Submissions are grouped by student and task. A retained trajectory contains at least three
attempts and has this conceptual structure:

```json
{
  "trajectory_id": "student__task",
  "student_id": "student",
  "module": "module",
  "task": "task",
  "language": "python",
  "language_version": "python2",
  "attempts": [
    {
      "attempt_number": 1,
      "timestamp": "...",
      "code": "normalized source",
      "correct": false
    }
  ]
}
```

The processed output is `data/dcu/processed/trajectories.jsonl`.

## Dataset statistics

The saved preprocessing report contains:

| Statistic | Value |
|---|---:|
| Students observed before minimum-length filtering | 533 |
| Tasks observed | 1,074 |
| Retained trajectories | 32,368 |
| Retained attempts | 264,264 |
| Groups removed for having fewer than 3 attempts | 58,237 |
| Mean attempts per retained trajectory | 8.164 |
| Median attempts per retained trajectory | 5 |
| Minimum / maximum attempts | 3 / 347 |
| Correct attempts | 12.85% |
| Trajectories ending correct | 84.26% |

The field named `removed_single_attempt_trajectories` in the current statistics file counts
all trajectories shorter than the configured minimum of three, not only single-attempt
trajectories.

The split manifest contains 507 retained students. The difference from 533 occurs because
the preprocessing statistic counts students before short trajectories are excluded.

## Frozen code embeddings

Each distinct normalized code submission is identified by its SHA-256 hash and encoded once
with `Salesforce/codet5p-110m-embedding`.

- Maximum token length: 512
- Embedding dimension: 256
- Configured encoding batch size: 32
- Output: `data/dcu/features/code_embeddings.pt`

CodeT5+ is placed in evaluation mode, has gradients disabled, and is not updated during
JEPA training. The saved PyTorch store includes its format version, checkpoint name, code
hashes, embedding dimension, and embedding tensor. The lookup is loaded on CPU with memory
mapping when supported.

## Leakage-free splits

Students, rather than individual attempts or trajectories, are split with seed 42. This
prevents the same student's behavior from appearing in both training and evaluation.

| Split | Students | Trajectories | Prefix-pair examples |
|---|---:|---:|---:|
| Train | 354 | 22,674 | 163,872 |
| Validation | 76 | 4,824 | 34,163 |
| Test | 77 | 4,870 | 33,861 |

The configured ratios are 70% / 15% / 15%. Integer rounding accounts for the exact student
counts.

## JEPA prefix pairs

For a trajectory with attempts \(1,\ldots,n\), the dataset creates \(n-1\) examples. For
each target index, the context ends immediately before the target attempt:

```text
context: attempts 1..t
target:  attempts 1..t+1
```

Histories are padded to 20 attempts. For longer trajectories, a rolling window preserves
later transitions rather than discarding everything after attempt 20.

Each batch contains:

- context and target code embeddings;
- context and target metadata;
- context and target padding masks;
- trajectory and student identifiers;
- target attempt number and target correctness.

The three metadata features per attempt are normalized attempt number, previous-attempt
correctness, and an indicator that the attempt is the first one.
