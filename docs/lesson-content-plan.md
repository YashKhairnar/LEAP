# Lesson content plan

What each stage of each task should teach, show, and leave out. All 18 stages have now been rewritten to this plan in `backend/app/tutoring/authored_content.py`. The code changes suggested below have not been made.

## How this plan was built

For every stage I compared four things:

1. The lesson text in `authored_content.py` (`STAGES`, `REGRESSION_STAGES`, `CNN_STAGES`).
2. The code the student runs, in `backend/app/tutoring/lesson_code.py`.
3. The starting assessment (`backend/app/assessments/bank.py`) and the final assessment (`final_bank.py`).
4. The real datasets in `backend/datasets/`.

The main finding is that **the assessments test skills the lessons never teach**. Some examples:

- Working out the size after pooling and flattening.
- Counting the images in a loader's last batch.
- Calculating MAE by hand.
- Reading a negative standardized value.
- Understanding what `stratify` does.
- Seeing why 90% accuracy can be misleading.

A student can finish every lesson and still have never seen these. That is the first thing to fix. Each stage below lists the assessment items it must prepare students for.

## Rules for every stage

1. **Teach everything the stage's assessment items test.** Use different numbers and wording from the assessments, so the lesson prepares students without giving away the items.
2. **Use one real worked example, taken from the dataset.** Show a real row, image or number, and follow it through the code's actual output.
3. **Follow one running example through the whole task.** Use the same review, house or digit from stage 1 to stage 6, so students watch one example go from raw data to prediction to score.
   - Sentiment: "The mic is great."
   - Regression: the 1,656 sq ft, 3-bed house that sold for $215,000.
   - CNN: the first image, a handwritten 0.
4. **Name one common mistake per stage**, and explain what goes wrong silently.
5. **Plain words first, then the term.** Introduce at most one new term per paragraph, and give each a "Words to know" definition.
6. **Practice should match the type of thinking the assessment asks for.**
   - If the assessment asks for a calculation (accuracy, MAE, shapes, batch sizes), practice should include calculations too.
   - Use "Which order…?" questions only in stages where order is the actual lesson.
7. **Size targets:**
   - Main idea: 60–90 words.
   - Analogy: 40–70 words.
   - Example: a small table or trace.
   - "Why it matters": 40–60 words.
   - At least 8 practice questions, each with its own hint and an explanation of why the wrong answers are wrong.

## Things to cut everywhere

- **Template text.** For example "In this step, {relationship}." and the shared hint "Focus on the role of … in this stage." Sentiment Stage 1 no longer uses either.
- **Jargon with no definition**, such as "computation graph", "capacity", "estimates parameters", "decision boundary", "spatial structure", "evaluation distribution" and "nonlinear response".
- **A "Which order…?" question in every stage.** There are 18 of them at the moment and they reward memorising the order, not understanding it. Keep them only where the order matters.
- **Transfer questions that jump to an unrelated task**, such as a house-price question inside the sentiment split lesson. Keep one per stage at most, and keep it close to the stage's idea.
- **Distractors that are obviously wrong**, like `model.predict` as an answer about loading. Replace them with believable mistakes.

## Task order

Recommended order: **Sentiment → House prices → Handwritten digits.**

- The dashboard already lists them in this order.
- But the intros number them 01 Sentiment, 02 CNN, 03 Regression, which contradicts that.
- The CNN intro lists "training data, test data and labels" as a prerequisite, so it should come last.
- Renumber the intros so CNN is 03.

The task intros (`frontend/src/features/learning/lib/lesson-introductions.ts`) are the strongest content and only need small changes:
- **Regression example:** it ends with "An estimated sale price in dollars". Replace it with a real number from the running house, e.g. "about $200,000" or whatever the trained model actually predicts.
- **Running examples:** make each task's "A simple example" use that task's running example.

---

## Task 1 · Review sentiment

### Stage 1 · Load labeled reviews (done, use as the reference)

- **Teaches:**
  - An input paired with a known answer.
  - A DataFrame row keeps that pair together.
  - `head()` and `len()` let you check the load.
- **Worked example:** row 4, `"The mic is great." | amazon | positive`, with each column's role.
- **Common mistake:** sorting or shuffling one column on its own.
- **Prepares for:** `sentiment-01` (which pairing is a labeled example) and `sentiment-post-01` (identify the label).
- **Cut:** nothing further.

### Stage 2 · Split into training and test reviews

- **Must teach:**
  - Why we test on reviews the model never saw. Compare it to studying from the exam's answer key.
  - `test_size=0.2` means 600 test reviews and 2,400 training reviews.
  - **What `stratify` does**, which is missing today. The dataset is 50% positive, so both parts stay about 50/50. Show what goes wrong without it on an uneven dataset, e.g. 60/40 (`sentiment-03`, `sentiment-post-03`).
  - `random_state` makes the split the same every run.
- **Worked example:**
  - Show the four outputs `X_train`, `X_test`, `y_train` and `y_test` with their sizes.
  - Note whether "The mic is great." ended up in train or test.
- **Common mistake:** splitting reviews and labels in two separate calls, so the pairs no longer line up.
- **Prepares for:** `sentiment-02`, `sentiment-post-02` (generalization) and `-03` (stratify).
- **Cut:** the house-price transfer question.

### Stage 3 · Turn text into numbers (TF-IDF)

- **Must teach:**
  - A model needs numbers, so each review becomes a row with one column per word.
  - **TF and IDF in plain words**, which is missing today:
    - A word scores higher when it appears in this review…
    - …and lower when it appears in many reviews.
    - So "great" counts for more than "the".
  - What the numbers in a row like `[0.0, 0.7, 0.2]` mean (`sentiment-post-04`).
  - **`fit_transform` on training text, `transform` on test text**, and why fitting on test text is leakage (`sentiment-05`, `sentiment-post-05`).
- **Worked example:**
  - Show the running review's non-zero TF-IDF weights, e.g. `mic 0.8, great 0.6`, taken from real output.
  - Show the matrix shapes: (2,400 × vocabulary) and (600 × vocabulary).
- **Common mistake:** fitting the vectorizer on all reviews before splitting.
- **Cut:** the Java `Map<String, Double>` analogy as the main explanation (it's fine as the Java variant); sparse-matrix internals.
- **Code change to consider:** add a print of the shapes and of one review's top-weighted words. Right now the code prints nothing, so the Run button has nothing to show.

### Stage 4 · Train the classifier

- **Must teach:**
  - Creating `LogisticRegression()` sets the model up. `fit` is the step that learns (`sentiment-06`, `sentiment-post-06`).
  - What it learns: one weight per word. Positive weights push towards positive, negative weights towards negative.
  - `max_iter` in one sentence at most.
- **Worked example:** the strongest positive words and the strongest negative words from the real model. This is the most memorable moment in the task.
- **Common mistake:** thinking `fit` changes the reviews, or that you can predict before calling `fit`.
- **Cut:** "decision boundary" (or define it), and the sigmoid formula.
- **Code change to consider:** promote the "inspect learned word weights" experiment into the main code, so students see the words without needing the Try it step.

### Stage 5 · Predict unseen reviews

- **Must teach:**
  - `predict` uses what the model has already learned and doesn't learn anything new.
  - **How a brand-new review is classified:** `vectorizer.transform(["…"])` then `model.predict(...)`, reusing the **same fitted vectorizer** (`sentiment-07`, `sentiment-post-07`).
  - `[:10]` only changes how many predictions are printed, not how many are made (`sentiment-08`, `sentiment-post-08`).
- **Worked example:**
  - Show 3–4 of the printed predictions, including one the model got wrong.
  - Let the student type their own review and see the prediction. Consider adding this as a Try it experiment.
- **Common mistake:** creating a new vectorizer for the new review, which gives different columns.
- **Cut:** "feature vectors from held-out reviews" as the main explanation. Say "the test reviews, turned into numbers the same way".

### Stage 6 · Measure how good it is

- **Must teach:**
  - Accuracy is correct predictions divided by total predictions. Do one calculation by hand, e.g. 42 of 60 = 70% (`sentiment-09`, `sentiment-post-09`).
  - **Why accuracy can mislead**, which is missing today:
    - On a 90/10 dataset, always guessing "positive" scores 90%.
    - Per-class recall in the report exposes this (`sentiment-10`, `sentiment-post-10`).
  - **How to read `classification_report`:** focus on the recall column and the "support" column. Mention precision in one sentence.
- **Worked example:**
  - The real accuracy.
  - The two recall values.
  - One misclassified review with a guess at why, e.g. sarcasm or "not bad".
- **Common mistake:** evaluating on training reviews and celebrating a near-perfect score.
- **Cut:** F1 (or one sentence at most). Don't define all four metrics.

---

## Task 2 · House prices (regression)

### Stage 1 · Prepare the housing data

- **Must teach:**
  - Features are the house details and the target is the price. Regression predicts a number, not a category (`regression-01`, `regression-post-01`).
  - **What `dropna()` does:** it removes the whole row if *any* value is missing, including the price (`regression-02`, `regression-post-02`).
    - Be honest: this dataset has no missing values, so `dropna()` removes 0 of 2,930 rows. Say that it's a safety step, and show the row count before and after.
  - `X` is a table of 4 columns and `y` is one column of prices.
- **Worked example:** the running house:

  | bedrooms | bathrooms | square_feet | age_years | price |
  |---|---|---|---|---|
  | 3 | 2.0 | 1,656 | 50 | $215,000 |

  Mark which columns are X and which is y.
- **Common mistake:** putting `price` into the feature list. The model would just copy the answer.
- **Cut:** "continuous target" without explanation. Say "a number that can take any value".

### Stage 2 · Keep some houses aside

- **Must teach:**
  - Same idea as Sentiment Stage 2, kept short.
  - Pass X and y **together** so each house keeps its price (`regression-03`, `regression-post-03`).
  - 2,930 houses × 0.2 means 586 test houses.
- **Worked example:** the sizes of the four outputs.
- **Common mistake:** shuffling features and prices separately.
- **Cut:** the rent-dataset transfer question, and anything this task already taught about splits. Point back to the earlier lesson instead.

### Stage 3 · Put features on the same scale

- **Must teach:**
  - Why scaling helps: square feet is in the thousands and bedrooms is under 10.
  - **What a scaled value means**, which is missing today:
    - 0 means the training average.
    - +1 means one "typical spread" above it.
    - A negative value means below average (`regression-05`, `regression-post-05`).
  - Fit the scaler on the training houses only, then reuse it for test houses (`regression-04`, `regression-post-04`).
- **Worked example:**
  - Training houses average about 1,500 sq ft, with a spread of about 505.
  - The running house (1,656 sq ft) becomes about **+0.31**.
  - The 896 sq ft house becomes about **−1.19**.
- **Common mistake:** calling `fit_transform` on the test set as well.
- **Cut:** the term "standard deviation" as the main explanation (introduce it after "typical spread"), and the formula's symbols.

### Stage 4 · Fit the price model

- **Must teach:**
  - A linear model has a starting price (the intercept) plus one coefficient per feature (`regression-06`, `regression-post-06`).
  - Reading a coefficient: "+1 spread of square feet adds about $X".
- **Worked example:** the real coefficients and intercept, e.g. printed with `zip(feature_columns, model.coef_)`.
- **Common mistake:** expecting coefficients in dollars per square foot. They're per scaled unit.
- **Cut:** the Java "updating fields" analogy (it's duplicated across all three tasks; keep it in Sentiment only).
- **Code change to consider:** print the coefficients and intercept. The current code prints nothing.

### Stage 5 · Predict prices

- **Must teach:**
  - Prediction needs the 4 features (scaled with the training scaler), not the price (`regression-07`, `regression-post-07`).
  - Read the printed actual vs predicted pairs.
- **Worked example:** the running house's prediction, if it's in the test set, or one printed row. Calculate its error: predicted − actual.
- **Common mistake:** passing unscaled features to a model trained on scaled ones.
- **Cut:** the template wording about "learned coefficients", which isn't needed once Stage 4 shows them.

### Stage 6 · Measure the error (MAE)

- **Must teach:**
  - **Calculate MAE by hand:** take each error, drop its sign, then average. Use a different example from the assessments, e.g. errors of −$8,000 and +$14,000 give an MAE of $11,000 (`regression-08`, `regression-post-08`).
  - "MAE = $X" means predictions miss by about $X on average, not every time (`regression-09`, `regression-post-09`).
  - **Comparing models fairly:** compare MAE only on the same test houses. Lower is better (`regression-10`, `regression-post-10`).
- **Worked example:**
  - The real MAE.
  - Compare it to the median price ($160,000) to show how big the error is.
  - One large miss.
- **Common mistake:** letting a positive and a negative error cancel out, i.e. averaging the errors without dropping their signs.
- **Cut:** RMSE and R² (save them for an optional "go further" note).

---

## Task 3 · Handwritten digits (CNN)

This task has the biggest gap between the assessments and the lessons. The assessments test shape arithmetic and PyTorch call order, and the lessons describe these only in general terms.

### Stage 1 · Load digit images

- **Must teach:**
  - An image is a grid of brightness numbers from 0 to 16.
  - Each row of 64 numbers becomes an 8 × 8 grid.
  - **The shape (N, 1, 8, 8):** number of images, channels (1 because it's grayscale), height and width. Practise with other sizes, e.g. 20 images is (20, 1, 8, 8) (`cnn-01`, `cnn-post-01`).
- **Worked example:** draw the first image (a 0) as an 8 × 8 number grid and as shaded squares. The existing `digit-matrix-example.tsx` component is suited to this.
- **Common mistake:** reshaping in the wrong order, e.g. treating 64 values as (8, 8, 1). The picture comes out scrambled and there's no error.
- **Cut:** the audio-classification transfer question; `TensorDataset` internals.

### Stage 2 · Split, scale and batch

- **Must teach:**
  - **Scaling:** divide pixels by 16 so they range from 0 to 1. A pixel of 12 becomes 0.75 (`cnn-02`, `cnn-post-02`).
    - Be clear that in this code the division happens when images go into the model, in Stage 4 and Stage 5. It must be applied in both places. The stage currently says "normalize" but its code doesn't normalize.
  - The 80/20 split: 4,496 training images and 1,124 test images.
  - **Batches:**
    - `batch_size=128` means 128 images per update.
    - The last batch holds what's left over: 4,496 = 35 × 128 + 16, so the last batch has 16 images (`cnn-03`, `cnn-post-03`).
- **Worked example:** the batch arithmetic above, plus the shape of one batch: (128, 1, 8, 8).
- **Common mistake:** dividing by 16 in training but forgetting to in prediction.
- **Cut:** the spam transfer question; `generator` seeding beyond one sentence.

### Stage 3 · Build the CNN

- **Must teach:**
  - A 3 × 3 filter slides across the image looking for a small pattern, such as an edge or the end of a stroke (`cnn-04`, `cnn-post-04`).
  - **Trace the shape through every layer.** This is missing today and is assessed twice:

    | After | Shape per image |
    |---|---|
    | input | 1 × 8 × 8 |
    | Conv2d(1, 16, 3, padding=1) | 16 × 8 × 8 |
    | MaxPool2d(2) | 16 × 4 × 4 |
    | Flatten | 256 |
    | Linear(256, 10) | 10 scores |

    (`cnn-05`, `cnn-post-05`; practise with a different channel count.)
  - Why there are 10 outputs: one score per digit. A 4-class problem would need 4 (`cnn-06`, `cnn-post-06`).
  - ReLU in one plain sentence: "keeps positive signals and zeroes the rest".
- **Worked example:** the table above, plus the trained filters shown as 3 × 3 images. The filters can wait for Stage 4.
- **Common mistake:** a Linear layer size that doesn't match the flattened shape, which causes a shape error.
- **Cut:** "computation graph", "capacity" and "nonlinear activation" without definitions.

### Stage 4 · Train the network

- **Must teach the job of each call** (`cnn-07`, `cnn-post-07`):
  - `zero_grad()` clears the previous batch's corrections.
  - The loss measures how wrong the scores were.
  - `backward()` works out which way to nudge each weight.
  - **`step()` actually changes the weights.**
- Also teach:
  - One pass over all batches is called an epoch. This code trains for one epoch.
  - Loss should go down.
- **Worked example:** print the loss every 10 batches so students can watch it fall. The current code prints only the final loss.
- **Common mistake:** forgetting `zero_grad()`, so corrections from earlier batches keep adding up.
- **Cut:** Adam internals (say "Adam is a popular way to take the step"); the term "gradient" before the plain version.
- **Code change to consider:** train for 3 epochs, if the runtime allows, and print the loss each epoch. One epoch gives a weak model and an unconvincing lesson.

### Stage 5 · Classify unseen digits

- **Must teach:**
  - `model.eval()` and `torch.no_grad()` mean we're only predicting: nothing is learned and no corrections are tracked (`cnn-08`, `cnn-post-08`).
  - **`argmax` picks the position of the highest score, and that position is the digit.** Practise with a 10-score list (`cnn-09`, `cnn-post-09`).
  - Divide by 16 again, matching training.
- **Worked example:**
  - Show the 10 scores for the running "0" image.
  - Point out the highest one.
  - Show one image the model got wrong.
- **Common mistake:** reading `argmax` as the highest *value* rather than its *position*.
- **Cut:** the house-price transfer question.

### Stage 6 · Measure accuracy

- **Must teach:**
  - Accuracy is correct over total. Calculate one by hand, e.g. 51 of 60 = 85% (`cnn-10`, `cnn-post-10`).
  - What 85% means on 1,124 test images: about 169 mistakes.
  - Which digits get confused. This links back to Sentiment Stage 6 on looking beyond accuracy.
- **Worked example:** the real accuracy and the most-confused pair of digits, e.g. 3 vs 8.
- **Common mistake:** reporting training accuracy.
- **Code change to consider:** a confusion matrix or a per-digit accuracy print.

---

## Practice questions per stage

Aim for at least 8 questions per stage, spread across the question pools the planner draws from:

| Pool | Count | What it checks |
|---|---|---|
| boundary | 3 | The stage's main rule, or its common mistake |
| variable | 2 | What a specific variable or output contains |
| operation | 2 | Which line or call does the job, or a calculation |
| ordering | 1–2 | Only where order matters (split → fit → transform; zero_grad → backward → step) |
| transfer | 1–2 | The same idea in a nearby problem |

Every question needs its own hint, which must not give away the answer, and an explanation that also says why the most tempting wrong answer is wrong. The tests in `backend/tests/test_authored_content.py` already check these rules for any stage that uses the new pool format.

## Suggested order of work

1. **CNN Stages 2–5:** shapes, batches, the training calls and argmax. This is the biggest gap between what's assessed and what's taught.
2. **Regression Stages 3 and 6:** scaled values and MAE calculations.
3. **Sentiment Stages 2, 3 and 6:** stratify, TF-IDF intuition, and accuracy on imbalanced data.
4. **The remaining stages**, then the task-intro and ordering fixes.
5. **The code changes noted above** (printing shapes, weights, coefficients and the loss curve). These change `CODE_VERSION`, so check them against the research protocol first.
