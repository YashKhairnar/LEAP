# Colab ML workshop

A copy of the SJSU CSED Research Lab's Colab notebook *Machine Learning Workshop: Classifying
Restaurant Reviews*, running on this platform. It is kept separate from the three lesson paths:
its own content, code runner, database tables, API routes and pages.

## Signing in

There are no accounts while only the workshop is shown. `/login` (and `/signup`) ask for a **research
ID** only. The first time an ID is used, a workshop user is created and linked to it in
`workshop_participants`; entering the same ID again (any letter case, extra spaces ignored) returns to that
learner's work. Any non-empty ID up to 64 characters is accepted for now, and there is no password: anyone
who types an ID enters as that participant. The research ID replaces the participant code on the dashboard
and finish page. Route: `POST /api/workshop/enter`.

## Versions

There are three versions of the notebook, with the same code, cells, questions and steps:

| Version | Shown to learners as | Source |
|---|---|---|
| `primary` | Machine learning only | Hand-transcribed from the first PDF, in `backend/app/workshop/content.py` |
| `analogy` | Everyday analogies (exam analogy) | `notebooks/source/analogy.ipynb` → `notebooks/analogy.json` |
| `java` | Java connections | `notebooks/source/java.ipynb` → `notebooks/java.json` |

A new research ID chooses its version once, right after typing the ID; returning IDs go straight in
with their first choice (stored in `workshop_assignments`, with `assigned_by` = `learner_choice`).
IDs that entered before versions existed are recorded as `primary` (`before_versions`).

To update the analogy or Java version, export the notebook from Colab (File → Download → .ipynb),
replace the file in `backend/app/workshop/notebooks/source/`, and run from `backend`:

```bash
.venv/bin/python scripts/import_workshop_notebook.py analogy app/workshop/notebooks/source/analogy.ipynb
```

The importer copies the notebook's text and boxes as written (purple boxes become analogy / Java
boxes) and replaces only the Colab-specific parts with the adapted ones below. It stops if a cell's code
differs from the original version, because every version must run the same code. One notebook cell is
skipped on purpose (listed in `SKIPPED_CELLS` in the script): analogy cell 59, an earlier copy of cell 62
placed after Cell 12.

## What learners see

`Before you start` → Steps 1–6 → `Finish`, in the same order and wording as the notebook. There are
16 numbered cells plus a practice cell, and 11 *Check your understanding* questions (q1_1 to q6_2).
For each cell, learners copy the code from the grey box, paste it into the empty cell, and click ▶ Run.
A cell's Run button unlocks once the cell above it has run. A step unlocks once every cell in the
previous step has run and every question has an answer. Cell 16 counts as done only after its three
placeholder reviews are replaced.

What was adapted from Colab (everything else follows the notebook):

| Colab | Here |
|---|---|
| Save a copy in Google Drive | Work saves under the research ID automatically |
| `files.upload()` with Colab's widget | Same code. ▶ Run shows a *Choose Files* button; the file must be the workshop's `dataset.csv` (header and size are checked). The sandbox then reads the server's copy. |
| Finish 1: share the notebook link | Removed; the post-survey asks for the research ID instead |
| Rules "skipping a cell causes `NameError`", "Colab restarted?" | Reworded: cells unlock in order and earlier cells are remembered |
| — | "Download dataset.csv here" link next to the lab-website instruction |
| — | Cell 16 note: avoid `/` and `\` in reviews (the platform's code-safety check blocks them) |

Every run replays all earlier cells silently, so later cells always see the variables they need.
Outputs match the notebook: 10,000 reviews, 8,000/2,000 split, 10,788 words, accuracy 0.84, 329 mistakes.

## Code

| Part | Location |
|---|---|
| Content (text, cells, questions) | `backend/app/workshop/content.py` |
| Runner (Colab upload stand-in, replay) | `backend/app/workshop/runner.py` |
| Tables | `backend/app/workshop/store.py` |
| API under `/api/workshop` | `backend/app/workshop/router.py` |
| Dataset | `backend/datasets/workshop_restaurant_reviews_v1.csv` |
| Page `/learn/workshop` | `frontend/src/features/workshop/`, `frontend/src/app/workshop.css` |
| Tests | `backend/tests/test_workshop.py` |

## Data

Five new tables, created on startup next to the existing ones:

- `workshop_progress`: one row per learner (current stage, completed stages, uploaded file name, start/finish times)
- `workshop_cell_runs`: every run (code, output, success, duration, run number); append-only
- `workshop_answers`: every saved answer; append-only, the latest per question is the current one
- `workshop_participants`: research ID → workshop user (first and last entry times)
- `workshop_assignments`: the version each learner uses, who assigned it and when

## Configuration

- `NEXT_PUBLIC_SHOW_LESSON_PATHS` (frontend, default unset): only the workshop is shown, and `/learn/*`
  except `/learn/workshop` redirects home. Set it to `true` to show the other paths again.
- `WORKSHOP_POST_SURVEY_URL` (backend, optional): the post-survey link on the finish page.
- Code runs on the `modal` or `docker` engine. The hosted Codapi engine can't take the 1.3 MB dataset.
  **Redeploy the Modal sandbox** (`modal deploy modal_sandbox/app.py`) so it serves `dataset.csv`.
