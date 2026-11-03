"""Beginner-friendly starting assessments paired by concept with the final forms."""

from __future__ import annotations

from dataclasses import dataclass

VERSION = "task_assessment_v4"
UNSURE = "I’m not sure yet"


@dataclass(frozen=True)
class AssessmentQuestion:
    id: str
    stage: str
    concept: str
    prompt: str
    options: tuple[str, str, str, str]
    answer: int
    explanation: str
    code: str | None = None


Q = AssessmentQuestion


QUESTION_BANK: dict[str, tuple[AssessmentQuestion, ...]] = {
    "sentiment_classification": (
        Q("sentiment-01", "data_loading_and_preparation", "Features and labels",
          "To help a computer learn whether reviews are positive or negative, what would each example need?",
          ("Only the review’s length", "A review and its known category", UNSURE, "Only the website name"), 1,
          "Learning examples need both the review and its known positive/negative category."),
        Q("sentiment-02", "train_test_split", "Generalization",
          "What is the fairest way to check whether a computer can handle reviews it has not learned from?",
          ("Check it on new reviews", UNSURE, "Check only its easiest reviews", "Check the same reviews again"), 0,
          "Reviews kept out of learning provide evidence about performance on new examples."),
        Q("sentiment-03", "train_test_split", "Stratified splitting",
          "A review collection is half positive and half negative. If it is divided into learning and checking groups, what is usually most useful?",
          (UNSURE, "Put only positive reviews in learning", "Keep a similar mix in both groups", "Copy every review into both groups"), 2,
          "A similar positive/negative mix makes both groups represent the full collection."),
        Q("sentiment-04", "tfidf_vectorization", "Text representation",
          "Most prediction programs perform calculations with numbers. What must happen to review text before such a program can use it?",
          ("Delete every repeated word", "Turn the words into numeric information", "Translate it into another language", UNSURE), 1,
          "Text must be represented numerically before a mathematical model can use it."),
        Q("sentiment-05", "tfidf_vectorization", "Data leakage",
          "A student first looks at every review, including the reviews reserved for checking, to choose important words. Why might that be unfair?",
          ("The checking reviews influenced preparation", "Important words cannot be counted", UNSURE, "The reviews become too short"), 0,
          "Reserved reviews should not influence decisions made while preparing the learning data."),
        Q("sentiment-06", "model_training", "Fitting a classifier",
          "What does it mean for a prediction program to learn from labeled reviews?",
          (UNSURE, "It memorizes the website colors", "It removes all negative reviews", "It finds patterns connecting words to categories"), 3,
          "Learning means finding patterns that connect review information with known categories."),
        Q("sentiment-07", "prediction", "Predicting new reviews",
          "After a program has learned from earlier reviews, what should it need to categorize one new review?",
          ("The new review text", "The correct category in advance", "A second copy of every old review", UNSURE), 0,
          "A trained program receives the new review as input; the category is what it must predict."),
        Q("sentiment-08", "prediction", "Prediction versus display",
          "A screen shows only the first 3 predictions from a set of 100 reviews. What can you safely conclude?",
          ("Only 3 predictions were made", UNSURE, "The display may be showing a small sample", "The other 97 reviews were deleted"), 2,
          "Limiting what is displayed does not necessarily limit how many predictions were calculated."),
        Q("sentiment-09", "evaluation", "Interpreting accuracy",
          "A program categorizes 48 out of 60 checking reviews correctly. What percentage did it get correct?",
          ("48%", "60%", UNSURE, "80%"), 3,
          "48 divided by 60 is 0.8, or 80%."),
        Q("sentiment-10", "evaluation", "Looking beyond accuracy",
          "There are 90 positive and 10 negative reviews. A program always answers “positive.” What important problem does its 90% score hide?",
          (UNSURE, "It misses every negative review", "It reads reviews too slowly", "It predicts too many categories"), 1,
          "Always choosing the larger group gives 90% overall but fails on all negative reviews."),
    ),
    "regression": (
        Q("regression-01", "prepare_housing_data", "Features and target",
          "If a computer is estimating a house’s sale price, which information should be the input and which should be the answer?",
          (UNSURE, "Input: price; answer: bedrooms", "Input: house details; answer: price", "Input and answer: price"), 2,
          "House details are available inputs, while sale price is the number to estimate."),
        Q("regression-02", "prepare_housing_data", "Missing data",
          "One house record has no bathroom value. What is a reasonable action before using the records to learn?",
          ("Pretend every missing value is 100", "Remove or carefully fill the incomplete record", UNSURE, "Change its price to zero"), 1,
          "Missing information must be handled deliberately, for example by removing or carefully filling it."),
        Q("regression-03", "split_housing_data", "Paired splitting",
          "When house details are divided into learning and checking groups, what must stay matched?",
          ("Each house and its actual price", UNSURE, "Houses with the same street number", "All high prices and all large houses"), 0,
          "Each house’s details must remain paired with its own actual price."),
        Q("regression-04", "scale_features", "Preprocessing without leakage",
          "A student adjusts number ranges using both learning houses and houses reserved for checking. What is the main concern?",
          (UNSURE, "The house prices become text", "The checking houses influenced preparation", "The learning group becomes larger"), 2,
          "Reserved houses should not influence preparation choices made for learning."),
        Q("regression-05", "scale_features", "Interpreting standardized values",
          "After values are recentered around an average, a house’s size is shown as a negative number. What could that mean?",
          ("Its size is below the learning-group average", "The house has negative physical space", "Its sale price must be negative", UNSURE), 0,
          "A negative recentered value can mean below average; it does not mean negative physical size."),
        Q("regression-06", "train_regression", "Learning coefficients",
          "What kind of pattern could help estimate a price from house details?",
          ("A rule linking details such as size to price", UNSURE, "A list that gives every house the same price", "A rule based only on row numbers"), 0,
          "A useful model learns how changes in input details relate to changes in price."),
        Q("regression-07", "predict_prices", "Inference inputs",
          "A new house has bedroom, bathroom, size, and age information but has not sold yet. Can a learned program estimate its price?",
          ("No, it must know the sale price first", "Yes, using the available house details", UNSURE, "Only if every detail equals an old house"), 1,
          "Prediction uses available house details to estimate the unknown sale price."),
        Q("regression-08", "evaluate_regression", "Calculating MAE",
          "Two price estimates miss the actual prices by $10,000 and $30,000. What is their average error size?",
          (UNSURE, "$10,000", "$40,000", "$20,000"), 3,
          "The average error size is ($10,000 + $30,000) / 2 = $20,000."),
        Q("regression-09", "evaluate_regression", "Interpreting MAE",
          "A report says the average size of the model’s price errors is $18,000. What does that mean?",
          ("Every estimate is exactly $18,000 high", "No error can exceed $18,000", "Estimates differ by $18,000 on average", UNSURE), 2,
          "The value describes the average size of errors, not their direction or maximum."),
        Q("regression-10", "evaluate_regression", "Comparing models fairly",
          "Two price-estimating programs are checked on the same houses. One has an average error of $15,000 and the other $22,000. Which performed better on those houses?",
          ("The $15,000-error program", UNSURE, "The $22,000-error program", "They performed exactly the same"), 0,
          "On the same checking set, the smaller average error indicates closer estimates."),
    ),
    "cnn": (
        Q("cnn-01", "load_images", "Image tensor shape",
          "A grayscale image is stored as an 8 by 8 grid of brightness values. How many brightness values describe one image?",
          ("8", "16", "64", UNSURE), 2,
          "An 8 by 8 grid contains 64 brightness values."),
        Q("cnn-02", "normalize_split", "Input normalization",
          "Brightness values run from 0 to 16. What does dividing every value by 16 do?",
          ("Changes the values to a 0-to-1 range", UNSURE, "Changes every image into digit 16", "Removes half the pixels"), 0,
          "Dividing by the maximum rescales 0–16 values to 0–1 without changing the image shape."),
        Q("cnn-03", "normalize_split", "Mini-batches",
          "Instead of processing every image at once, a program works with small groups of images. What is one such group commonly called?",
          (UNSURE, "A label", "A pixel", "A batch"), 3,
          "A batch is a group of examples processed together."),
        Q("cnn-04", "build_cnn", "Convolution",
          "To recognize handwritten digits, why might a program examine small neighboring areas of an image?",
          ("To find local strokes and curves", "To replace every image with one pixel", UNSURE, "To reveal the correct label automatically"), 0,
          "Small image regions contain local visual patterns such as stroke edges and curves."),
        Q("cnn-05", "build_cnn", "Pooling and flattening",
          "An 8 by 8 grid is reduced to half its width and half its height. What size is the new grid?",
          ("2 by 2", UNSURE, "4 by 4", "8 by 4"), 2,
          "Halving both dimensions changes an 8 by 8 grid to 4 by 4."),
        Q("cnn-06", "build_cnn", "Output scores",
          "A program must choose one digit from 0 through 9. How many possible digit choices are there?",
          (UNSURE, "9", "10", "11"), 2,
          "The digits 0 through 9 give ten possible choices."),
        Q("cnn-07", "train_network", "Gradients and weight updates",
          "During learning, the program compares a prediction with the known digit. What should it do when the prediction is wrong?",
          ("Update its internal values to reduce similar errors", "Delete the image", "Keep everything unchanged", UNSURE), 0,
          "Learning uses errors to adjust internal values so future predictions can improve."),
        Q("cnn-08", "classify_images", "Inference versus training",
          "When checking a trained image program on reserved images, should those images change what it has learned?",
          ("Yes, always reveal their answers first", UNSURE, "No, checking should measure it without teaching it", "Yes, replace all earlier learning"), 2,
          "Reserved images should measure the trained program without updating it from their answers."),
        Q("cnn-09", "classify_images", "Selecting a class",
          "A digit program gives these scores: digit 0 → 0.2, digit 1 → 0.7, digit 2 → 0.1. Which digit would it choose?",
          ("Digit 0", "Digit 1", UNSURE, "Digit 2"), 1,
          "The largest score is 0.7, which belongs to digit 1."),
        Q("cnn-10", "evaluate_cnn", "Held-out accuracy",
          "A program correctly recognizes 85 of 100 reserved digit images. What is its score on those images?",
          ("15%", UNSURE, "100%", "85%"), 3,
          "85 correct out of 100 is 85%."),
    ),
}


def assessment_task(task: str) -> str:
    task = "sentiment_classification" if task == "sentiment" else task
    if task not in QUESTION_BANK:
        raise ValueError("Unknown assessment task")
    return task
