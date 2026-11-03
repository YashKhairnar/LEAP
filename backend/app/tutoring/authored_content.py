"""Authored lesson and practice content.

This module is deliberately deterministic: it does not call an LLM, planner, or
remote service. The response shape matches the former tutor endpoint so the
learner UI and collection pipeline can continue to use the same contracts.
"""

from __future__ import annotations

from hashlib import sha256
from uuid import uuid4

from ..execution.datasets import dataset_for_task
from ..models import (
    GeneratedLessonContent,
    GeneratedLessonSection,
    InstructionalActionType,
    TutorContent,
    TutorGenerationRequest,
    TutorGenerationResponse,
)
from .authored_questions import QUESTIONS
from .lesson_code import fixed_code_experiments, fixed_lesson_code

AUTHORED_CONTENT_VERSION = "authored_content_v5"


class AuthoredContentUnavailable(ValueError):
    pass


STAGES: dict[str, dict[str, object]] = {
    "data_loading_and_preparation": {
        "title": "Load labeled reviews",
        "intro": "Before a model can learn anything, it needs examples where we already know the answer. Our file, reviews.csv, holds 3,000 short reviews from Amazon, IMDb and Yelp, and a person has marked each one positive or negative. In this stage you load that file into a pandas DataFrame, which is a table in Python, and check that every review is still next to its answer.",
        "intro_items": [
            "Load reviews.csv into a DataFrame called df",
            "Look at the first few rows to see the columns",
            "Check that all 3,000 reviews loaded",
        ],
        "target": "a pandas DataFrame of labeled rows",
        "analogy": "In Java you might read each line of the file into a Review object with a text field and a sentiment field, then keep them in a List<Review>. A pandas DataFrame does the same job in one line: each row is like one Review object, and each column is like one field.",
        "everyday": "Think of a spreadsheet with one review per row. One column holds what the customer wrote, and another holds whether it was positive or negative. Loading the file opens that spreadsheet so Python can read it. As long as you never sort one column on its own, each review stays next to its answer.",
        "concept": "In supervised learning, each training example is an input paired with a known answer, called the label. Here the input is the review text and the label is its sentiment. A DataFrame stores one example per row, so the pairing is kept by position: the text and the label in the same row belong together.",
        "example": "Here is one real row from the file. You will see it as the fifth row when you run the code.",
        # "column | value | role" items render as a table row in the lesson.
        "example_items": [
            "review | \"The mic is great.\" | The input the model reads",
            "sentiment | positive | The label: the answer the model learns to give",
            "source | amazon | Where the review came from. Not used for learning.",
            "The file has 3,000 rows like this: 1,500 positive and 1,500 negative.",
        ],
        "result": "df.head() prints the first five rows with their review, source and sentiment columns. The last line prints Rows: 3000.",
        "why": "The model learns only from these pairs. A common mistake is changing one column without the other, for example sorting the reviews but not their labels. Every review would then sit next to someone else's answer, and the model would learn nonsense without any error message.",
        "code_explanation": [
            "import pandas as pd — loads pandas, the Python library for tables, under the short name pd.",
            'pd.read_csv("reviews.csv") — reads the file and returns a DataFrame, which we store in df.',
            "df.head() — returns the first five rows so you can check the columns look right.",
            "len(df) — counts the rows. Each row is one review, so it should print 3000.",
        ],
        "review": "A training row is an input plus its known answer. Load the data as a table and keep each review in the same row as its label.",
    },
    "train_test_split": {
        "title": "Keep some reviews aside for testing",
        "intro": "A model can do well on reviews it has already seen just by remembering them. To find out whether it has learned something general, 20% of the reviews are held back as a test set: 600 reviews it never sees while learning. The other 2,400 train it. stratify makes sure both sets keep the same 50/50 mix of positive and negative reviews.",
        "intro_items": [
            "Split reviews and labels into training and test sets",
            "Check the sizes: 2,400 and 600",
            "Keep the positive/negative mix the same in both",
        ],
        "target": "training and test reviews",
        "analogy": "It's like testing Java code on cases you didn't look at while writing it: if you only test the inputs you debugged with, passing proves little. train_test_split picks the unseen cases at random, and because reviews and labels go in one call, it cuts both lists at the same positions, so every review keeps its label.",
        "everyday": "Studying with past exam papers works, but if you then test yourself on the very same papers, a perfect score just means you remember them. Setting a few papers aside, unopened, gives an honest check. The test set is those unopened papers.",
        "concept": "Performance on training data overstates how a model generalizes, so a random 20% is held out. stratify=df[\"sentiment\"] makes the split keep the class proportions: with a 50/50 dataset, both sets stay 50/50. Without it, a random split could tilt one set, making the test score harder to interpret. random_state=42 makes the split reproducible.",
        "example": "What the split produces for this dataset.",
        "example_items": [
            "# Output | Size | Positive / negative",
            "X_train, y_train | 2,400 reviews | 1,200 / 1,200",
            "X_test, y_test | 600 reviews | 300 / 300",
            "\"The mic is great.\" | in X_test | The model won't see it until Stage 5",
            "Both sets keep the dataset's 50/50 mix because of stratify.",
        ],
        "result": "The code prints Training reviews: 2400 Test reviews: 600, then the test labels: {'positive': 300, 'negative': 300}. stratify kept the test set exactly half positive and half negative.",
        "why": "Split reviews and labels in one call. Splitting them separately, or shuffling one list, would pair most reviews with someone else's label; nothing crashes, the model just learns nonsense. And never let test reviews into training: a score on reviews the model has seen measures memory, not skill.",
        "code_explanation": [
            'train_test_split(df["review"], df["sentiment"], ...) — splits reviews and labels together, at the same random positions.',
            "test_size=0.2 — keeps 20% of the 3,000 reviews, 600 of them, for testing.",
            "random_state=42 — makes the split the same every run.",
            'stratify=df["sentiment"] — keeps the positive/negative mix equal in both sets.',
            'y_test.value_counts() — counts each label in the test set, to check the 50/50 mix.',
        ],
        "review": "Split reviews and labels together: 2,400 to learn from, 600 kept unseen. stratify keeps both sets 50/50.",
    },
    "tfidf_vectorization": {
        "title": "Turn review text into numbers",
        "intro": "A model can't read words; it needs numbers. TF-IDF turns each review into a row of numbers with one column per word in the vocabulary, 4,558 columns here. Most entries are 0, because a short review uses only a few words. A word gets a high number when it stands out in that review but is rare across reviews, so 'mic' counts for more than 'the'.",
        "intro_items": [
            "Learn the vocabulary from the training reviews",
            "Turn every review into a row of word weights",
            "Use the same vocabulary for the test reviews",
        ],
        "target": "TF-IDF feature matrices",
        "analogy": "Think of a Map<String, Double> per review, mapping each word to a weight, then lined up into a table with one fixed column per vocabulary word. fit_transform builds the column list from training reviews; transform reuses that exact list for test reviews, so column 1,234 means the same word everywhere.",
        "everyday": "Imagine highlighting each review. Words that appear in nearly every review, like 'the' or 'is', get a faint highlight because they tell you little. Words that are rare across reviews, like 'mic' or 'awful', get a bold one. TF-IDF turns those highlights into numbers.",
        "concept": "TF-IDF weight = term frequency × inverse document frequency. TF is how often a word appears in this review; IDF is high for words found in few reviews and low for common ones. Each row is then scaled to length 1. fit learns the vocabulary and IDF values from training text only; transform applies them unchanged to test text.",
        "example": "The running review, \"The mic is great.\", as TF-IDF weights. Every other column in its row is 0.",
        "example_items": [
            "# Word | How rare (IDF) | Weight in this review",
            "mic | 7.69: very rare | 0.85",
            "great | 3.68: fairly common | 0.41",
            "is | 2.51: common | 0.28",
            "the | 1.81: in most reviews | 0.20",
            "The full row has 4,558 columns; these 4 are the only ones that aren't 0.",
        ],
        "result": "The code prints the two shapes, (2400, 4558) and (600, 4558): the same 4,558 columns for both. Then it prints the non-zero weights for \"The mic is great.\": great 0.41, is 0.28, mic 0.85, the 0.2.",
        "why": "Fit the vectorizer on training reviews only, then transform the test reviews with it. If test reviews help build the vocabulary and word rarity, the test isn't truly unseen any more. A separate fit on test text would also create different columns, so the numbers wouldn't line up with what the model learned.",
        "code_explanation": [
            "TfidfVectorizer() — creates a vectorizer that hasn't learned any vocabulary yet.",
            "vectorizer.fit_transform(X_train) — learns the vocabulary and word rarity from training reviews, then converts them.",
            "vectorizer.transform(X_test) — converts test reviews with the training vocabulary. Words never seen in training are ignored.",
            "X_train_tfidf, X_test_tfidf — tables with one row per review and one column per vocabulary word.",
            "vectorizer.get_feature_names_out() — the 4,558 vocabulary words, in column order.",
            'vectorizer.transform(["The mic is great."]) — turns one new review into a row with the same columns.',
        ],
        "review": "TF-IDF turns each review into word weights, highest for words rare across reviews. Learn the vocabulary from training reviews only.",
    },
    "model_training": {
        "title": "Train the classifier",
        "intro": "Logistic regression learns one weight per word. Positive weights push a review towards positive, negative weights towards negative, and a review's prediction comes from adding up its words' weights, each multiplied by its TF-IDF value. fit finds those 4,558 weights by checking them against the 2,400 labeled training reviews.",
        "intro_items": [
            "Create a LogisticRegression model",
            "Fit it on the training features and labels",
            "Read the words it learned",
        ],
        "target": "a fitted sentiment classifier",
        "analogy": "Think of an object with a double[] weights field, one entry per vocabulary word, plus a double bias. LogisticRegression() creates the object; fit(X, y) is the method that fills the array from the examples. Until fit runs, the fields are empty and the model can't predict anything.",
        "everyday": "Think of a judge learning which words signal a happy or unhappy customer by reading 2,400 reviews where the answer is known. They learn that 'great' and 'love' are strong good signs, and 'not' and 'worst' are strong bad signs. fit is that learning; the weights are what the judge remembers.",
        "concept": "Logistic regression computes a score = bias + Σ weight × TF-IDF value, then turns it into a probability of the positive class. fit chooses the weights that best match the training labels. max_iter=1000 gives the optimizer enough steps to finish, and random_state makes the result reproducible.",
        "example": "The words with the strongest weights after training on the 2,400 reviews.",
        "example_items": [
            "# Word | Weight | Pushes towards",
            "great | +4.92 | Positive: the strongest positive word",
            "good | +3.30 | Positive",
            "not | −4.60 | Negative: the strongest negative word",
            "bad | −3.42 | Negative",
            "worst, poor | −2.54, −2.39 | Negative",
        ],
        "result": "The code prints the five strongest words each way. Most negative: not, bad, worst, poor, don (from \"don't\"). Most positive: great, good, love, best, excellent.",
        "why": "Creating LogisticRegression() learns nothing; only fit does, and only from the training reviews and their labels. The weights also show the model's limits: it scores words one at a time, so it can't tell that 'not bad' is praise. 'not' and 'bad' are both strongly negative.",
        "code_explanation": [
            "LogisticRegression(max_iter=1000, random_state=42) — creates an untrained classifier. max_iter allows enough learning steps.",
            "model.fit(X_train_tfidf, y_train) — learns one weight per word from the training reviews and their labels.",
            "model.coef_ — after fitting, the 4,558 word weights. Positive means 'pushes towards positive'.",
            "model.classes_ — after fitting, ['negative', 'positive']: the two labels it can predict.",
            "model.coef_[0].argsort() — sorts the words from most negative weight to most positive.",
        ],
        "review": "fit learns one weight per word from the training reviews: positive pushes positive. Words are scored one at a time.",
    },
    "prediction": {
        "title": "Predict the sentiment of unseen reviews",
        "intro": "Now the trained model labels the 600 test reviews it never saw. For each review it adds up its words' weights and picks positive or negative. The test reviews were already turned into numbers with the training vocabulary, so predict just applies what fit learned. Nothing is learned here, and the true labels are kept aside for the next stage.",
        "intro_items": [
            "Predict a label for every test review",
            "Read the printed predictions",
            "Classify a brand-new review with the same pipeline",
        ],
        "target": "predicted labels for unseen reviews",
        "analogy": "model.predict(X_test_tfidf) is like calling a pure Java method on every element of an array: it reads the stored weights, computes a label for each review and returns a String[] of 600 labels. It never changes the weights.",
        "everyday": "The judge now reads new reviews and gives a verdict on each, using what they learned, without being told the answers. Later, you compare their verdicts with the real labels.",
        "concept": "Inference applies the fitted pipeline. A new review must go through the same fitted vectorizer (transform, not fit) so its columns match the ones the weights belong to; model.predict then returns the class with the higher probability.",
        "example": "Our running review is in the test set. This is how it's classified, plus one the model gets wrong.",
        "example_items": [
            "# Step | Result | Note",
            "\"The mic is great.\" | In X_test | The model never trained on it",
            "vectorizer.transform | mic 0.85, great 0.41, … | The same columns as training",
            "model.predict | positive | 88% sure, according to predict_proba",
            "A tricky review | \"The food was not bad at all.\" → negative | Wrong: 'not' and 'bad' are scored separately",
        ],
        "result": "The code prints 10 lines like positive: Reversible plug works great. Each is a test review with its predicted label. y_pred holds a prediction for all 600.",
        "why": "A new review must go through the same fitted vectorizer, with transform. Creating or fitting a new vectorizer would build different columns, so the weights would line up with the wrong words and the predictions would be meaningless, often without any error.",
        "code_explanation": [
            "model.predict(X_test_tfidf) — returns positive or negative for each of the 600 test reviews.",
            "zip(X_test, y_pred) — pairs each review's text with its predicted label.",
            "[:10] — prints only the first 10 pairs; all 600 predictions still exist.",
            'f"{prediction}: {review}" — prints the label, then the review.',
        ],
        "review": "predict applies the learned weights to test reviews in the training columns. New reviews must use the same fitted vectorizer.",
    },
    "evaluation": {
        "title": "Measure how good it is",
        "intro": "Finally, compare the 600 predictions with the true labels. Accuracy is the fraction the model got right: this model gets 500 of 600, or 83.3%. One number can hide a lot, so the classification report also shows recall: for each label, the share of those reviews the model caught. Here it catches 86% of positive reviews but only 80% of negative ones.",
        "intro_items": [
            "Calculate accuracy: correct ÷ total",
            "Read recall for each label in the report",
            "Look at reviews the model got wrong",
        ],
        "target": "an assessment of classifier performance",
        "analogy": "Accuracy is a loop over two parallel String arrays: count the positions where y_pred[i].equals(y_test[i]), then divide by the length. Recall does the same count, but only over the positions whose true label is, say, negative.",
        "everyday": "Mark the judge's 600 verdicts against the real answers: 500 ticks is 83%. Then check separately: of the 300 genuinely unhappy customers, how many did they spot? 241. That second check, recall, shows they're better at spotting happy customers than unhappy ones.",
        "concept": "Accuracy = correct ÷ total. Recall for a class = correctly predicted members of that class ÷ all true members of it. On a balanced test set accuracy is informative, but on an imbalanced one a model can score high by always predicting the majority class, which per-class recall exposes. Precision, the other main column, asks: of everything predicted as this class, how much really was?",
        "example": "The real results for this model on the 600 test reviews.",
        "example_items": [
            "# Measure | Value | How it's worked out",
            "accuracy | 0.833 | 500 correct ÷ 600 reviews",
            "recall, negative | 0.80 | 241 of 300 negative reviews caught",
            "recall, positive | 0.86 | 259 of 300 positive reviews caught",
            "support | 300 each | How many test reviews have each label",
            "A miss | \"The battery life is highly unacceptable.\" | Truly negative, predicted positive",
        ],
        "result": "The code prints Accuracy: 0.8333… and then the report: a row per label with precision, recall, f1-score and support, followed by overall averages.",
        "why": "Accuracy can mislead when one label is much more common. On a test set that's 95% positive, a model that always says positive scores 95% while missing every negative review; its negative recall would be 0. Always check the per-label numbers, and read a few mistakes.",
        "code_explanation": [
            "accuracy_score(y_test, y_pred) — the fraction of test reviews whose prediction matches the true label.",
            "classification_report(y_test, y_pred, ...) — a table with precision, recall, F1 and support for each label.",
            "recall column — for each label, the share of those reviews the model caught.",
            "support column — how many test reviews have each label: 300 and 300 here.",
            "zero_division=0 — avoids a warning if a label is never predicted.",
        ],
        "review": "Accuracy = correct ÷ total, here 83.3%. Check recall per label too: this model catches 86% of positive reviews but 80% of negative.",
    },
}


CNN_STAGES: dict[str, dict[str, object]] = {
    "load_images": {
        "title": "Turn rows of numbers into images",
        "intro": "A computer doesn't see a picture; it sees numbers. Each row of images.csv holds 64 brightness values from 0 (black) to 16 (white), plus the digit the picture shows. Laid out as 8 rows of 8, those 64 numbers make a tiny image of a handwritten digit. In this stage you load all 5,620 rows and reshape each one into the 8 × 8 grid a CNN expects.",
        "intro_items": [
            "Load images.csv with pandas",
            "Reshape each row of 64 pixels into a 1 × 8 × 8 image",
            "Keep every image paired with its digit label",
        ],
        "target": "a labeled dataset of 8 × 8 image tensors",
        "analogy": "In Java you might store a picture as an int[8][8] array: 8 rows, each holding 8 brightness values. The file stores each picture flattened into one row of 64 numbers, and reshape(-1, 1, 8, 8) folds every row back into that grid. The extra 1 is the number of colour channels: one, because the images are grayscale.",
        "everyday": "Think of a mosaic made of 64 tiles, each a shade of grey. If someone reads the shades out to you as one long list, you can rebuild the picture by placing them 8 to a row. Reshaping does exactly that for every image in the file, and each finished mosaic keeps a note saying which digit it shows.",
        "concept": "A CNN works on images, so each example must keep its layout: which pixel sits next to which. A flat row of 64 values loses that, so the data is reshaped to (N, C, H, W): N images, C channels, H rows and W columns. Here that is (5620, 1, 8, 8). The labels stay in a separate array, in the same order as the images.",
        "example": "How the data is laid out, followed by one real image from the file, labeled 7.",
        "example_items": [
            "# Part | Value | What it means",
            "N | 5,620 | The number of images in the file",
            "C | 1 | Channels: one, because the images are grayscale",
            "H × W | 8 × 8 | Rows and columns of pixels in each image",
            "label | 0 to 9 | The digit each image shows, stored in the same order",
        ],
        "result": "The code prints Images: (5620, 1, 8, 8) Classes: 10. That is 5,620 grayscale 8 × 8 images covering the ten digits.",
        "why": "The CNN looks for patterns among neighbouring pixels, so the grid layout matters. If the 64 numbers are folded the wrong way, pixels that touch in the real picture end up apart, and the strokes the network looks for disappear. Depending on the mistake, PyTorch may not complain at all.",
        "code_explanation": [
            "df[pixel_columns].to_numpy(...) — takes the 64 pixel columns as one array of numbers, one row per image.",
            ".reshape(-1, 1, 8, 8) — folds each row into 1 channel of 8 × 8. The -1 tells NumPy to work out N itself.",
            'df["label"].to_numpy(dtype="int64") — the digit for each image, as whole numbers.',
            "TensorDataset(images, labels) — pairs image i with label i so they stay together from now on.",
            "len(np.unique(labels)) — counts the different digits in the file. It should print 10.",
        ],
        "review": "Each image is a grid of numbers. Reshape the 64 values into (1, 8, 8) and keep every image paired with its digit label.",
    },
    "normalize_split": {
        "title": "Split, scale and batch the images",
        "intro": "As in the earlier tasks, some images are kept aside for testing: 80% of the 5,620 images (4,496) train the model and 20% (1,124) test it. This stage also covers two things that are new with neural networks: scaling pixel values from 0–16 down to 0–1, and feeding the model images in small groups called batches.",
        "intro_items": [
            "Split the images 80/20 into training and test sets",
            "Wrap each set in a DataLoader that serves batches",
            "Know where the divide-by-16 scaling happens",
        ],
        "target": "training and test DataLoaders",
        "analogy": "A DataLoader is like a Java Iterator over a List: each step hands you the next chunk. Here each chunk, or batch, is 128 images and their 128 labels, and training walks through the batches the way for (Batch b : loader) would in Java. When the iterator runs out, one full pass, called an epoch, is done.",
        "everyday": "Imagine marking a pile of 4,496 worksheets. You don't check them all at once; you take 128 at a time, notice the mistakes, adjust your teaching, then take the next 128. A batch is one of those piles. Scaling is like turning every score into a fraction of the top mark, so they all sit between 0 and 1.",
        "concept": "Neural networks train best when inputs are small numbers on a consistent scale, so each pixel is divided by 16 to map 0–16 onto 0–1. They also learn from mini-batches: the weights are updated after each batch, not after every image or once for the whole set. shuffle=True gives the training batches a new random order on each pass.",
        "example": "What the split and the batches look like for this dataset.",
        "example_items": [
            "# Item | Value | Why",
            "training images | 4,496 | 80% of 5,620, used to update the weights",
            "test images | 1,124 | 20%, kept aside until the very end",
            "full batches | 35 × 128 | 35 full batches use 4,480 images",
            "last batch | 16 images | The 16 left over: 4,496 − 4,480",
            "pixel 4 after scaling | 0.25 | 4 ÷ 16. A 0 stays 0 and a 16 becomes 1.0",
        ],
        "result": "The code prints Training images: 4496 Test images: 1124, then Training batches: 36 Images per batch: 128. 35 batches are full and the last holds the 16 left over. Each full batch has shape (128, 1, 8, 8).",
        "why": "The divide-by-16 isn't in this stage's code. It happens as images enter the model, written images_batch / 16.0, in both training and prediction. A common mistake is scaling in one place and forgetting the other: the model then sees inputs 16 times larger than it learned on, and its predictions fall apart without any error.",
        "code_explanation": [
            "torch.Generator().manual_seed(42) — fixes the randomness so everyone gets the same split and order.",
            "random_split(dataset, [train_size, test_size], ...) — randomly divides the images into 4,496 for training and 1,124 for testing.",
            "DataLoader(train_dataset, batch_size=128, shuffle=True) — serves training images 128 at a time, in a new random order each pass.",
            "DataLoader(test_dataset, batch_size=256) — serves test images in bigger batches. Their order doesn't matter.",
            "len(train_loader) — the batches in one pass: 35 full ones plus the leftover.",
        ],
        "review": "Train on 80%, test on 20%. Batches feed the model 128 images at a time, and every image is divided by 16 as it goes in.",
    },
    "build_cnn": {
        "title": "Build the network, layer by layer",
        "intro": "A CNN is a stack of layers, each transforming the output of the one before. Early layers look for small patterns such as edges and stroke ends; the last layer turns everything found into 10 scores, one per digit. In this stage you build that stack and follow one image's shape through every layer, from 1 × 8 × 8 down to 10 scores.",
        "intro_items": [
            "Know the job of each layer",
            "Trace an image's shape through the network",
            "Explain why the last layer has 10 outputs",
        ],
        "target": "an untrained ten-class CNN",
        "analogy": "nn.Sequential works like chained calls in a Java Stream: the output of one step is the input to the next. Each layer is an object with its own fields, the weights, and a method that transforms its input. Building the model creates those objects with random weights; it doesn't train them.",
        "everyday": "Picture a team checking a small picture. The first worker slides a 3 × 3 stencil over it and marks where short lines and curves appear. The next keeps only the strongest mark in each 2 × 2 patch, shrinking the sheet. The last reads all the marks and gives each digit a score. For now the stencils are blank; training will shape them.",
        "concept": "Conv2d slides 16 learnable 3 × 3 filters across the image, and each produces a feature map showing where its pattern appears. ReLU keeps positive values and sets negative ones to 0. MaxPool2d(2) keeps the largest value in each 2 × 2 block, halving height and width. Flatten lines the maps up into one list, and Linear turns it into 10 class scores.",
        "example": "Follow one image's shape through the network. ReLU sits after Conv2d and doesn't change the shape.",
        "example_items": [
            "# After | Shape per image | What happened",
            "input | 1 × 8 × 8 | One grayscale image",
            "Conv2d(1, 16, 3, padding=1) | 16 × 8 × 8 | 16 filters, each makes an 8 × 8 map",
            "MaxPool2d(2) | 16 × 4 × 4 | Each 2 × 2 block becomes one value",
            "Flatten | 256 | 16 × 4 × 4 values in one row",
            "Linear(256, 10) | 10 | One score per digit",
        ],
        "result": "The code prints Scores for one image: (1, 10), one score per digit, and Learnable numbers: 2730. That's 160 in the 16 filters (9 weights and a bias each) and 2,570 in the Linear layer, all random until training.",
        "why": "Every layer's size must match the one before it. The 16 * 4 * 4 in nn.Linear(16 * 4 * 4, 10) comes straight from the shape trace: 16 maps of 4 × 4 after pooling. Change the number of filters or the pooling and that number changes too. Get it wrong and PyTorch stops with a shape mismatch error.",
        "code_explanation": [
            "nn.Conv2d(1, 16, kernel_size=3, padding=1) — 1 input channel, 16 filters of 3 × 3. padding=1 adds a border so the maps stay 8 × 8.",
            "nn.ReLU() — keeps positive values and turns negative ones into 0. The shape doesn't change.",
            "nn.MaxPool2d(2) — keeps the largest value in each 2 × 2 block, so each 8 × 8 map becomes 4 × 4.",
            "nn.Flatten() — lines up 16 × 4 × 4 values into one list of 256 numbers.",
            "nn.Linear(16 * 4 * 4, 10) — combines all 256 values into 10 scores, one per digit.",
            "sum(p.numel() for p in model.parameters()) — counts every learnable number in the network.",
        ],
        "review": "A CNN filters, pools, flattens and scores. Track the shape at every layer: 1×8×8 → 16×8×8 → 16×4×4 → 256 → 10.",
    },
    "train_network": {
        "title": "Train the network",
        "intro": "The model starts with random filters, so its first guesses are right only about 1 time in 10. Training improves that one batch at a time: the model scores 128 images, a loss measures how wrong those scores were, PyTorch works out how to nudge every weight, and the optimizer makes the nudge. This code makes one pass over the training set, called an epoch: 36 nudges in all.",
        "intro_items": [
            "Know what each of the four training calls does",
            "Read the loss as a measure of how wrong the model is",
            "Keep test images out of training",
        ],
        "target": "a CNN with learned weights",
        "analogy": "Think of a Java loop that tunes a field until a method's output matches the expected value: compare the result with the answer, work out which way to adjust, update the field, repeat. Training does this for thousands of weights at once. loss.backward() works out the adjustments and optimizer.step() applies them.",
        "everyday": "Think of learning darts. You throw a handful (one batch), see how far off you were (the loss), work out whether to aim higher or lower (backward), then adjust your aim (step). Before the next round you forget the old adjustment and judge the new throws fresh (zero_grad). Round after round, the darts land closer.",
        "concept": "Training minimises a loss, here cross-entropy, which is small when the score for the correct digit is high. For each batch, loss.backward() computes a gradient for every weight: the direction that would increase the loss. optimizer.step() moves each weight a small step the other way. Adam is the rule that sizes each step, and lr=0.01 sets the overall scale.",
        "example": "One training step for one batch of 128 images, in order.",
        "example_items": [
            "# Call | Job | If you skip it",
            "optimizer.zero_grad() | Clears the last batch's adjustments | Old adjustments pile up and training goes wrong",
            "loss_fn(...) | Scores the batch and measures how wrong it was | There's nothing to learn from",
            "loss.backward() | Works out how to nudge every weight | The next call has no direction to use",
            "optimizer.step() | Applies the nudges to the weights | The model never improves",
        ],
        "result": "The code prints Final batch loss: followed by a number. Lower is better. A model guessing at random scores about 2.3 on this loss, so a value well below that means it has learned something.",
        "why": "Only training batches should ever reach the update. If test images were used to change the weights, the final test score would partly measure memory instead of skill. Notice the images_batch / 16.0 inside the loop too: prediction has to scale its inputs in exactly the same way.",
        "code_explanation": [
            "loss_fn = nn.CrossEntropyLoss() — measures how wrong the 10 scores are. It's small when the correct digit scores highest.",
            "torch.optim.Adam(model.parameters(), lr=0.01) — the optimizer that will change every weight. lr sets the step size.",
            "model.train() — puts the model into training mode.",
            "for images_batch, labels_batch in train_loader — loops over the 36 training batches once: one epoch.",
            "zero_grad(), backward(), step() — clear the old adjustments, work out new ones from the loss, apply them.",
            "loss.item() — turns the last batch's loss into a plain number to print.",
        ],
        "review": "For each batch: zero_grad, compute the loss, backward, step. Only training images should ever update the weights.",
    },
    "classify_images": {
        "title": "Predict digits the model hasn't seen",
        "intro": "Now the trained model is used on the 1,124 test images. For each image it outputs 10 scores, one per digit, and the prediction is simply the digit with the highest score. Two lines make sure this is pure prediction: model.eval() switches off training behaviour, and torch.no_grad() tells PyTorch not to track adjustments, because nothing is being learned here.",
        "intro_items": [
            "Run the trained model on the test images",
            "Pick each image's digit with argmax",
            "Make sure prediction changes nothing in the model",
        ],
        "target": "predicted digits for unseen images",
        "analogy": "Picking the prediction is like finding the index of the largest element in a double[10] array: loop over the scores, remember where the biggest one is, and return that position. Because the positions run from 0 to 9, the position is the digit. argmax(dim=1) does this for every image in the batch at once.",
        "everyday": "Imagine ten judges, one for each digit, each holding up a score for how much the picture looks like their digit. You don't care about the exact numbers; you pick the judge with the highest score. Their seat number, 0 to 9, is the answer.",
        "concept": "Inference runs the network forward without learning. model.eval() switches layers to evaluation behaviour, and torch.no_grad() skips gradient tracking, which saves memory and guarantees no update. The output for each image is a vector of 10 scores, often called logits. argmax(dim=1) returns the index of the largest score, which is the predicted class.",
        "example": "Example scores for one test image. Position 5 holds the highest score, so the prediction is 5.",
        "example_items": [
            "# Positions | Scores | Note",
            "0 to 4 | 0.4, −1.2, 0.9, 0.3, 0.2 | Lower scores",
            "5 | 3.1 | The highest score, so argmax returns 5",
            "6 to 9 | 0.7, −0.5, 1.4, 0.1 | Lower scores",
            "prediction | 5 | The position of the highest score, not the score",
        ],
        "result": "The code prints First predictions: followed by 10 digits, the predicted digit for each of the first 10 test images. y_pred holds a prediction for every one of the 1,124 test images.",
        "why": "argmax returns the position of the highest score, not the score itself. Mixing those up is the most common slip. Notice images_batch / 16.0 again as well: prediction must scale inputs exactly as training did. Skip it and the model sees numbers up to 16 after learning on 0 to 1, and its predictions degrade with no error.",
        "code_explanation": [
            "model.eval() — switches the model from training mode to prediction mode.",
            "with torch.no_grad(): — inside this block PyTorch doesn't track adjustments, because nothing is being learned.",
            "model(images_batch / 16.0) — scales the test images as in training and returns 10 scores per image.",
            ".argmax(dim=1) — for each image, the position of the highest of its 10 scores: the predicted digit.",
            "torch.cat(prediction_batches) — joins the per-batch results into one tensor of 1,124 predictions.",
        ],
        "review": "Prediction only runs forward: eval(), no_grad(), the same / 16 scaling, then argmax picks the position of the highest score.",
    },
    "evaluate_cnn": {
        "title": "Measure accuracy",
        "intro": "Finally, the 1,124 predictions are compared with the true digits. Accuracy is the fraction that match: correct predictions divided by all predictions. Because these images were never used in training, it tells you how well the CNN is likely to do on new handwriting. For comparison, random guessing would score about 10%.",
        "intro_items": [
            "Compute accuracy from predictions and true labels",
            "Read it as an estimate for new images",
            "Look past the single number to the digits it confuses",
        ],
        "target": "held-out classification accuracy",
        "analogy": "Accuracy is like looping over two int arrays of the same length, counting the positions where the values are equal, and dividing by the length. (y_pred == y_test) builds that true/false array in one step, .float() turns true into 1 and false into 0, and .mean() divides the count by the total.",
        "everyday": "It's like marking a test: compare each answer with the answer key, count the ticks, and divide by the number of questions. 18 right out of 20 is 90%. Because the model never saw these questions while it studied, the score is a fair guess at how it would do on new ones.",
        "concept": "Test accuracy is correct predictions divided by total test examples. It estimates performance on new data from the same source, and it's only valid because the test images never updated the weights. With ten roughly balanced classes, chance is about 10%. One overall number can hide classes the model handles badly, so check which digits get confused.",
        "example": "How the accuracy line works, step by step, with an example result of 90%.",
        "example_items": [
            "# Step | Value | What it means",
            "y_pred == y_test | True, True, False, … | One True for each correct prediction",
            ".float() | 1.0, 1.0, 0.0, … | True becomes 1, False becomes 0",
            ".mean() | 0.9, for example | The fraction correct: 90%",
            "mistakes at 90% | about 112 | 10% of the 1,124 test images",
            "random guessing | about 0.1 | One right in ten: the score to beat",
        ],
        "result": "The code prints Test accuracy: followed by a number between 0 and 1, rounded to 3 decimals. Multiply by 100 for a percentage. Your exact number depends on how training went.",
        "why": "Accuracy is honest only because the test images never updated the weights. If they had, the score would partly measure memory. One number can also hide problems: a model might handle most digits well but keep confusing 3 with 8, or 1 with 7. Look at a few wrong predictions before trusting the score.",
        "code_explanation": [
            "(y_pred == y_test) — compares each prediction with the true digit, giving True or False for every test image.",
            ".float() — turns True into 1.0 and False into 0.0.",
            ".mean() — averages those 1s and 0s, which gives the fraction of correct predictions.",
            ".item() — turns the result into a plain Python number.",
            "round(accuracy, 3) — keeps three decimal places for printing.",
        ],
        "review": "Accuracy is correct ÷ total on images the model never trained on. Compare it with chance (10%) and check which digits it confuses.",
    },
}


REGRESSION_STAGES: dict[str, dict[str, object]] = {
    "prepare_housing_data": {
        "title": "Prepare the housing data",
        "intro": "This task predicts a number, a house's sale price, instead of a category like positive or negative. That's called regression. houses.csv holds 2,930 real home sales from Ames, Iowa. Each has four details (bedrooms, bathrooms, size in square feet and age in years) plus the price it sold for. In this stage you load the file and separate the details, X, from the price, y.",
        "intro_items": [
            "Load houses.csv and drop incomplete rows",
            "Put the four house details into X",
            "Put the sale price into y",
        ],
        "target": "house features X paired with prices y",
        "analogy": "In Java you might model a sale as record Sale(int bedrooms, double bathrooms, int squareFeet, int ageYears, int price). Training needs that split in two: the four inputs the model may look at, and the one value it must learn to predict. X is like a list of the first four fields; y is a list of the prices, in the same order.",
        "everyday": "Think of a stack of property listings. Each card shows a home's bedrooms, bathrooms, size and age on the front, and what it sold for on the back. To learn pricing, you study the fronts and check against the backs. X is the front of every card; y is the back, kept in the same order.",
        "concept": "Regression learns a function from features to a continuous target: a number that can take any value, rather than one of a few labels. Here the feature matrix X has 4 columns per house and the target y has one price per house. Rows with missing values are dropped first, so every remaining row has complete features and a known price.",
        "example": "The first house in the file, which you'll see at the top of df.head(), split into features and target.",
        "example_items": [
            "# Column | Value | Role",
            "bedrooms, bathrooms | 3, 2.0 | Features: they go into X",
            "square_feet | 1,656 | Feature: goes into X",
            "age_years | 50 | Feature: goes into X",
            "price | $215,000 | Target: goes into y. Never a feature.",
            "All 2,930 rows are complete, so dropna() removes none here. It's a safety step for messier data.",
        ],
        "result": "df.head() shows the first five houses with all five columns. X now holds 2,930 rows × 4 feature columns, and y holds 2,930 prices.",
        "why": "Never put the price in X. If the answer is one of the inputs, the model just copies it and looks perfect, then has nothing to work with on a new house whose price isn't known yet. dropna() matters too: it removes the whole row if any value is missing, because a house with gaps can't be a complete example.",
        "code_explanation": [
            'pd.read_csv("houses.csv").dropna() — loads the sales and drops any row with a missing value in any column.',
            "feature_columns = [...] — the four house details the model is allowed to use.",
            "X = df[feature_columns] — a table with one row per house and the 4 feature columns.",
            'y = df["price"] — the sale prices, one per house, in the same order as X.',
            "df.head() — shows the first five houses so you can check the columns look right.",
        ],
        "review": "X holds the four house details and y holds the price, in the same order. The price is the answer, never an input.",
    },
    "split_housing_data": {
        "title": "Keep some houses aside",
        "intro": "To find out whether the model can price houses it has never seen, some are held back: 20% of the 2,930, which is 586 houses, form a test set, and the other 2,344 train the model. If you did the sentiment task, this will look familiar. The one rule that matters: X and y are split together, so every house keeps its own price.",
        "intro_items": [
            "Split X and y into training and test sets",
            "Check the sizes: 2,344 and 586",
            "Keep every house paired with its price",
        ],
        "target": "training and test houses",
        "analogy": "It's like cutting two parallel Java arrays at the same random positions: shuffle one list of indices, then use it to pick from both the features array and the prices array. train_test_split(X, y, ...) does that in one call, which is why X and y go in together.",
        "everyday": "An estate agent who wants to test their instinct sets aside a pile of recent sales without looking at the prices, practises on everything else, then checks their guesses for the set-aside pile at the end. That pile is the test set.",
        "concept": "Performance on training data overstates how a model will do on new data, so a random 20% is held out. train_test_split shuffles the row indices once and applies them to X and y, so features and targets stay aligned. random_state=42 makes the shuffle repeatable.",
        "example": "The four outputs of train_test_split for this dataset.",
        "example_items": [
            "# Output | Size | What it holds",
            "X_train | 2,344 × 4 | Features of the houses used for learning",
            "y_train | 2,344 | Their sale prices",
            "X_test | 586 × 4 | Features of the houses kept aside",
            "y_test | 586 | Their prices, used only to check predictions",
        ],
        "result": "The code prints Training houses: 2344 Test houses: 586.",
        "why": "Split X and y in one call. Splitting them separately, or shuffling one of them, would give most houses someone else's price. Nothing would crash, but the model would learn from nonsense and its error would mean nothing.",
        "code_explanation": [
            "train_test_split(X, y, ...) — shuffles the houses once and splits features and prices together.",
            "test_size=0.2 — keeps 20% of the houses, 586 of them, aside for testing.",
            "random_state=42 — makes the shuffle the same every run, so results can be reproduced.",
            "X_train, X_test, y_train, y_test — the four results, always in this order.",
            "len(X_train), len(X_test) — counts the houses in each part.",
        ],
        "review": "Split X and y together: 2,344 houses to learn from and 586 kept aside, so the error measures new houses, not memory.",
    },
    "scale_features": {
        "title": "Put the features on the same scale",
        "intro": "The four features use very different ranges: bedrooms run from 0 to 8, but square feet run from 334 to 5,642. Scaling turns every feature into the same kind of number: how far a house is from the average, measured in typical spreads. A scaled 0 means average, +1 means one spread above average, and a negative number means below average.",
        "intro_items": [
            "Learn each feature's average and spread from the training houses",
            "Turn every feature into spreads from the average",
            "Reuse the same scaler on the test houses",
        ],
        "target": "standardized training and test features",
        "analogy": "StandardScaler is like a Java object with two fields per feature, mean and spread, set once by fit. transform is a method that uses those stored fields to convert any house: (value − mean) / spread. Calling fit again on other data would overwrite the fields, which is exactly what you must not do with the test houses.",
        "everyday": "Comparing a house's size and its age directly is like comparing a height in centimetres with a weight in kilograms. Instead, describe each as how unusual it is: a bit above average, well below average. That puts everything on one scale. The averages come from the houses you're learning from.",
        "concept": "StandardScaler standardizes each feature: z = (x − mean) / standard deviation, using the training set's mean and standard deviation. On the training data each scaled feature then has mean 0 and standard deviation 1. The fitted statistics are reused through transform on the test set, so nothing about the test houses leaks into preprocessing.",
        "example": "Square feet before and after scaling. Training houses average about 1,500 sq ft, with a typical spread of about 505.",
        "example_items": [
            "# House | Square feet | Scaled value",
            "First house in the file | 1,656 | About +0.31: a little above average",
            "A smaller house | 896 | About −1.19: well below average",
            "An average house | 1,500 | About 0: right on the average",
            "A larger house | 2,005 | About +1: one spread above average",
        ],
        "result": "The code prints the first training house, 3 bedrooms, 2 bathrooms, 1,370 sq ft and 33 years old, and the same house after scaling: [0.19, -0.25, -0.24, -0.14]. Its size is below the training average of 1,493 sq ft, so its scaled size is negative. The price, y, isn't scaled.",
        "why": "Fit the scaler on the training houses only, then transform the test houses with it. Fitting on the test houses too would let their averages shape the preprocessing, so the test isn't fully unseen any more. Nothing breaks, which is why this leak is so easy to miss.",
        "code_explanation": [
            "StandardScaler() — creates a scaler that hasn't learned anything yet.",
            "scaler.fit_transform(X_train) — learns each feature's average and spread from the training houses, then scales them.",
            "scaler.transform(X_test) — scales the test houses with the training averages and spreads. Nothing new is learned.",
            "X_train_scaled, X_test_scaled — the scaled features, each value now in spreads from the training average.",
            "X_train_scaled[0] — the first training house after scaling, one value per feature.",
        ],
        "review": "A scaled value is spreads from the training average: 0 is average, negative is below. Fit on training houses, transform test houses.",
    },
    "train_regression": {
        "title": "Fit the price model",
        "intro": "A linear regression prices a house with a simple formula: start from a base price, then add or subtract an amount for each feature. Training, with fit, finds the base price (the intercept) and the amount for each feature (the coefficients) that bring the predictions closest to the real prices of the 2,344 training houses.",
        "intro_items": [
            "Create a LinearRegression model",
            "Fit it to the scaled training houses and their prices",
            "Read what it learned: an intercept and 4 coefficients",
        ],
        "target": "a fitted linear regression model",
        "analogy": "After fit, the model is like a Java object with a double intercept field and a double[] coef field holding one number per feature. Its predict method returns intercept + coef[0] * x0 + coef[1] * x1 + ... for any house. fit is the method that chooses those five numbers from the training data.",
        "everyday": "Think of a valuer's rule of thumb: start at a typical price, add something for extra size, take something off for age. Training works out exactly how much to add or subtract for each detail by checking against thousands of real sales.",
        "concept": "LinearRegression models price as intercept + Σ coefficient × feature, and fit chooses these parameters to minimise squared error on the training set. Because the features are standardized, each coefficient is the price change for a one-standard-deviation increase in that feature with the others held fixed, and the intercept is the predicted price of an average house.",
        "example": "What the fitted model holds. The exact numbers come from training; the Try it step prints yours.",
        "example_items": [
            "# Part | What it means | What to look for",
            "intercept | The predicted price of a perfectly average house | Close to the average training price",
            "square_feet coefficient | Price change for one extra spread of size | Positive: bigger houses cost more",
            "age_years coefficient | Price change for one extra spread of age | Its sign: does age add or remove value?",
            "one spread of size | About 505 sq ft | Coefficients are per spread, not per square foot",
        ],
        "result": "The code prints one coefficient per feature and the intercept: bedrooms -15618, bathrooms 8570, square_feet 51680, age_years -25674, intercept 178582. Size adds the most. Bedrooms is negative because, at the same size, more bedrooms means smaller rooms.",
        "why": "The coefficients are per spread, not per original unit, because the features were scaled. A square_feet coefficient of 40,000 means about $40,000 for each extra ~505 sq ft, not $40,000 per square foot. Also remember that creating LinearRegression() learns nothing; only fit does.",
        "code_explanation": [
            "LinearRegression() — creates an untrained model with no intercept or coefficients yet.",
            "model.fit(X_train_scaled, y_train) — finds the intercept and coefficients that best match the training prices.",
            "model.coef_ — after fitting, four numbers: one per feature, in the order of feature_columns.",
            "model.intercept_ — after fitting, the predicted price of a house that is average on every feature.",
            "zip(feature_columns, model.coef_) — pairs each feature name with its learned coefficient.",
        ],
        "review": "fit finds an intercept (an average house's price) plus one coefficient per feature: the price change per spread.",
    },
    "predict_prices": {
        "title": "Predict prices for unseen houses",
        "intro": "Now the fitted model prices the 586 test houses it never saw. For each one it applies its formula, intercept plus each coefficient times the house's scaled feature, and returns a dollar amount. The real prices in y_test aren't used here; they're kept so the next stage can check the predictions.",
        "intro_items": [
            "Predict a price for every test house",
            "Compare a few predictions with the real prices",
            "Work out one house's error",
        ],
        "target": "estimated prices for held-out houses",
        "analogy": "model.predict(X_test_scaled) is like calling a pure Java method on every element of an array: it reads the stored coefficients, computes a price for each house, and returns a double[] of 586 results. It never changes the model's fields.",
        "everyday": "The valuer now prices new listings with the rule they worked out, without peeking at what the houses actually sold for. Afterwards, you compare their estimates with the real sale prices.",
        "concept": "Inference applies the fitted parameters to new inputs: predicted price = intercept + Σ coefficient × scaled feature. The inputs must be transformed with the training-fitted scaler, exactly as in training. y_test isn't an input; it's kept for evaluation.",
        "example": "How to read one printed line, using an example prediction.",
        "example_items": [
            "# Item | Value | Meaning",
            "actual | $215,000 | The real sale price, from y_test",
            "predicted | $203,500 | The model's estimate (an example value)",
            "error | −$11,500 | Predicted − actual: the model guessed low",
            "size of the error | $11,500 | The error without its sign, used in the next stage",
        ],
        "result": "The code prints 10 lines in the form actual=$…, predicted=$…, one for each of the first 10 test houses. y_pred holds a prediction for all 586.",
        "why": "Prediction must use the same preparation as training: features scaled by the scaler fitted on training houses. Passing unscaled features gives wildly wrong prices with no error, because the model expects spreads, not square feet. And a real new house has no price yet, so the price can never be an input.",
        "code_explanation": [
            "model.predict(X_test_scaled) — returns one predicted price for each of the 586 test houses.",
            "zip(y_test, y_pred) — pairs each house's real price with its prediction.",
            "[:10] — prints only the first 10 pairs; all 586 predictions still exist.",
            'f"actual=${actual:,.0f}, ..." — formats each price with commas and no cents.',
        ],
        "review": "predict applies the formula to scaled test features. Error = predicted − actual; real prices are only used to check.",
    },
    "evaluate_regression": {
        "title": "Measure the error",
        "intro": "One number now sums up how far off the model is: the mean absolute error, or MAE. Take each test house's error, drop the sign so a $10,000 overestimate and a $10,000 underestimate count the same, then average over all 586 houses. The result is in dollars: on average, predictions miss by about this much.",
        "intro_items": [
            "Calculate MAE by hand for a few houses",
            "Read MAE in dollars",
            "Compare models fairly, on the same test houses",
        ],
        "target": "mean absolute error on held-out houses",
        "analogy": "MAE is a loop you could write in Java: for each house, add Math.abs(actual − predicted) to a running total, then divide by the number of houses. mean_absolute_error(y_test, y_pred) does exactly that.",
        "everyday": "Imagine checking a valuer's estimates against 586 real sales. Note how far each estimate was off, ignoring whether it was too high or too low, then average those gaps. That average tells you how much to trust their next estimate.",
        "concept": "MAE = (1/n) Σ |actual − predicted|. Taking absolute values stops positive and negative errors cancelling out. It's in the target's units, dollars here, and it's an average, so individual errors can be much larger. Lower is better, and MAE values are only comparable when they come from the same test set.",
        "example": "MAE worked out by hand for three example houses.",
        "example_items": [
            "# House | Actual → predicted | Size of error",
            "A | $150,000 → $162,000 | $12,000",
            "B | $240,000 → $225,000 | $15,000",
            "C | $98,000 → $101,000 | $3,000",
            "MAE | (12,000 + 15,000 + 3,000) ÷ 3 | $10,000",
            "For scale: the typical house in this dataset sold for about $160,000.",
        ],
        "result": "The code prints Mean absolute error: $ followed by the model's MAE across all 586 test houses.",
        "why": "Always drop the signs before averaging. Otherwise errors of +$20,000 and −$20,000 average to $0 and the model looks perfect. And compare MAEs only on the same test houses: a lower MAE on an easier test set doesn't make a better model.",
        "code_explanation": [
            "mean_absolute_error(y_test, y_pred) — averages the size of each error across all 586 test houses.",
            'f"Mean absolute error: ${mae:,.0f}" — prints the MAE in dollars, with commas and no cents.',
        ],
        "review": "MAE: drop each error's sign, then average. It's in dollars, lower is better, and only comparable on the same test houses.",
    },
}


STAGES_BY_TASK: dict[str, dict[str, dict[str, object]]] = {
    "sentiment_classification": STAGES,
    "cnn": CNN_STAGES,
    "regression": REGRESSION_STAGES,
}

def _stable_shuffle(options: list[str], key: str) -> list[str]:
    """Keep authored options reproducible while distributing correct positions."""
    if len(options) < 2:
        return options
    ordered = list(options)
    digest = sha256(key.encode()).digest()
    for index in range(len(ordered) - 1, 0, -1):
        swap = digest[index % len(digest)] % (index + 1)
        ordered[index], ordered[swap] = ordered[swap], ordered[index]
    return ordered


def _stage(task: str, stage: str) -> dict[str, object]:
    if task == "sentiment":
        task = "sentiment_classification"
    if task not in STAGES_BY_TASK or stage not in STAGES_BY_TASK[task]:
        raise AuthoredContentUnavailable(f"No authored tutor content exists for {task}/{stage}")
    return STAGES_BY_TASK[task][stage]


def _lesson(request: TutorGenerationRequest, data: dict[str, object]) -> GeneratedLessonContent:
    code = fixed_lesson_code(request.task, request.stage)
    analogy_type = "concept" if request.analogy_preference == "pure_ml" else "analogy"
    if analogy_type == "concept":
        analogy_body = str(data["concept"])
    elif request.analogy_preference == "everyday":
        analogy_body = str(data["everyday"])
    else:
        analogy_body = str(data["analogy"])
    sections = [
        GeneratedLessonSection(type="meaning", title="What this stage means", body=str(data["intro"]), items=list(data.get("intro_items", [])), code=None, language=None),  # type: ignore[arg-type]
        GeneratedLessonSection(type=analogy_type, title="Connect the idea", body=analogy_body, items=[], code=None, language=None),
        GeneratedLessonSection(type="example", title="A small example", body=str(data["example"]), items=list(data.get("example_items", [])), code=None, language=None),  # type: ignore[arg-type]
        GeneratedLessonSection(type="result", title="What the code produces", body=str(data["result"]), items=[], code=None, language=None),
        GeneratedLessonSection(type="code", title="Try the code", body="Run the code, then check that the output matches what it produces.", items=[], code=code.code, language=code.language),
        GeneratedLessonSection(type="why_it_matters", title="Why it matters", body=str(data["why"]), items=[], code=None, language=None),
    ]
    experiments = fixed_code_experiments(request.task, request.stage)
    return GeneratedLessonContent(
        title=str(data["title"]), introduction=str(data["intro"]), sections=sections,
        code_explanation=list(data.get("code_explanation", [])),  # type: ignore[arg-type]
        try_this=[{
            "title": experiment.title, "find": experiment.find, "replace": experiment.replace,
            "expected_change": experiment.expected_change,
        } for experiment in experiments[:1]],
        key_takeaway=str(data["review"]),
    )


ACTION_POOLS = {
    "concept_matching": "boundary", "misconception_diagnosis": "boundary", "concept_summary": "boundary",
    "comparison_selection": "variable", "error_identification": "code",
    "analogy_mapping": "transfer", "novel_transfer": "transfer",
    "pipeline_ordering": "ordering",
}
# The boundary pool serves all three steps, so each step starts on a different variant.
STEP_VARIANT_OFFSET = {"connect": 0, "practice": 1, "review": 2}


def _question(request: TutorGenerationRequest, data: dict[str, object], variant: int) -> TutorContent:
    action = request.action_type.value.rsplit(".", 1)[-1]
    task = "sentiment_classification" if request.task == "sentiment" else request.task
    pool = QUESTIONS[task][request.stage][ACTION_POOLS.get(action, "operation")]
    prompt, correct, options, explanation, hint = pool[(STEP_VARIANT_OFFSET.get(request.step, 0) + variant) % len(pool)]
    return TutorContent(
        question=prompt, options=_stable_shuffle(list(options), f"{request.task}.{request.stage}.{prompt}"),
        expected_answer=correct, hint=hint, explanation=explanation,
        concepts_tested=list(request.learning_objectives) or [str(data["target"])],
    )


def authored_tutor_content(request: TutorGenerationRequest, instance_id: str | None = None, variant: int = 0) -> TutorGenerationResponse:
    """variant picks among a stage's alternative questions; callers pass how many the learner has already seen."""
    data = _stage(request.task, request.stage)
    effective_request = request.model_copy(update={"task": "sentiment_classification" if request.task == "sentiment" else request.task})
    lesson = _lesson(effective_request, data)
    content = _question(request, data, variant)
    return TutorGenerationResponse(
        content_instance_id=instance_id or f"authored-{uuid4()}", model="authored", prompt_version=AUTHORED_CONTENT_VERSION,
        code_version=fixed_lesson_code(effective_request.task, request.stage).version,
        dataset=dataset_for_task(effective_request.task).public(), lesson=lesson, content=content,
    )
