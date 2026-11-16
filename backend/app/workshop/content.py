"""Content for the Colab-based "Classifying Restaurant Reviews" workshop.

This is a transcription of the SJSU CSED research lab's Colab notebook
("Primary-Python_AI_ML_Study_Colab", 15 Nov). Wording, step order, cell code
and the Check-your-understanding questions follow the notebook. Only the parts
that refer to Google Colab or Google Drive have been adapted to this platform;
those adaptations are marked with "Adapted:" comments below.

Inline markup used in text: `code`, **bold**, *italic* and [label](url).
A box item starting with "pre:" is shown as a line of program output.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

WORKSHOP_ID = "colab_ml_workshop"
WORKSHOP_VERSION = "colab_ml_workshop_v1"
WORKSHOP_TITLE = "Machine Learning Workshop: Classifying Restaurant Reviews"
DATASET_FILENAME = "workshop_restaurant_reviews_v1.csv"
RUNTIME_DATASET_FILENAME = "dataset.csv"

DEFAULT_INSTRUCTIONS = (
    "1. Copy the code below → 2. Paste it into the empty code cell underneath → 3. Click ▶ Run to run it",
)
PASTE_PLACEHOLDER = "# ✍️ Paste the code here, then click ▶ Run"
OWN_REVIEW_PLACEHOLDERS = ("Write a positive review here", "Write a negative review here", "Write a tricky review here")


@dataclass(frozen=True)
class WorkshopCell:
    cell_id: str
    stage_id: str
    label: str
    title: str
    code: str
    kind: str = "standard"  # standard | upload | own_reviews
    instructions: tuple[str, ...] = DEFAULT_INSTRUCTIONS

    def public(self) -> dict[str, Any]:
        return {
            "cell_id": self.cell_id, "stage_id": self.stage_id, "label": self.label, "title": self.title,
            "code": self.code, "kind": self.kind, "instructions": list(self.instructions),
            "paste_placeholder": PASTE_PLACEHOLDER,
        }


@dataclass(frozen=True)
class WorkshopQuestion:
    question_id: str
    stage_id: str
    prompt: str

    def public(self) -> dict[str, Any]:
        return {"question_id": self.question_id, "stage_id": self.stage_id, "prompt": self.prompt}


@dataclass(frozen=True)
class WorkshopStage:
    stage_id: str
    nav_label: str
    short_label: str
    title: str
    blocks: tuple[dict[str, Any], ...]
    cells: tuple[WorkshopCell, ...] = field(default_factory=tuple)
    questions: tuple[WorkshopQuestion, ...] = field(default_factory=tuple)

    def public(self) -> dict[str, Any]:
        return {
            "stage_id": self.stage_id, "nav_label": self.nav_label, "short_label": self.short_label,
            "title": self.title, "blocks": list(self.blocks),
            "cells": [cell.public() for cell in self.cells],
            "questions": [question.public() for question in self.questions],
        }


# Block helpers keep the transcription readable.
def P(text: str) -> dict[str, Any]:
    return {"type": "paragraph", "text": text}


def H(text: str, level: int = 3) -> dict[str, Any]:
    return {"type": "heading", "text": text, "level": level}


def QUOTE(text: str, cite: str | None = None) -> dict[str, Any]:
    return {"type": "quote", "text": text, "cite": cite}


def ASIDE(text: str) -> dict[str, Any]:
    return {"type": "aside", "text": text}


def LIST(*items: str, ordered: bool = False) -> dict[str, Any]:
    return {"type": "list", "ordered": ordered, "items": list(items)}


def BOX(variant: str, title: str | None, *items: str) -> dict[str, Any]:
    """variant: see (blue), did (blue), check (amber), warning (red), plain (grey)."""
    return {"type": "box", "variant": variant, "title": title, "items": list(items)}


def SEE(*items: str) -> dict[str, Any]:
    return BOX("see", "What you should see", *items)


def CELL(cell_id: str) -> dict[str, Any]:
    return {"type": "cell", "cell_id": cell_id}


def TABLE(columns: list[str], rows: list[list[str]]) -> dict[str, Any]:
    return {"type": "table", "columns": columns, "rows": rows}


QUESTIONS_BLOCK = {"type": "questions"}


def _cell(stage_id: str, cell_id: str, label: str, title: str, code: str, **extra: Any) -> WorkshopCell:
    return WorkshopCell(cell_id=cell_id, stage_id=stage_id, label=label, title=title, code=code.strip("\n"), **extra)


# ---------------------------------------------------------------------------
# Before you start + What is machine learning?
# ---------------------------------------------------------------------------
START_CELLS = (
    _cell("start", "practice", "Practice cell", "Try it now",
          'print("Hello there, Welcome to our machine learning research workshop!")'),
)

START = WorkshopStage(
    stage_id="start", nav_label="Start here", short_label="Before you start", title="Before You Start",
    cells=START_CELLS,
    blocks=(
        {
            "type": "banner",
            "title": WORKSHOP_TITLE,
            "items": [
                "**Research project by:** SJSU Computer Science Education Research Lab",
                "**Purpose:** to investigate how undergraduate students transfer knowledge from imperative programming to artificial intelligence and machine learning concepts.",
            ],
            "note": "This material is based upon work supported by the U.S. National Science Foundation under Grant No. 2451781.",
        },
        P("In this workshop you will build a machine learning model that reads a restaurant review and decides whether it is **positive** or **negative**, even for reviews it has never seen. You will build it yourself, one small piece of code at a time."),
        P("Each section explains an idea first. Then it gives you a short piece of code, called a **cell**, to copy and run."),
        # Adapted: the Colab asks learners to save a copy in Google Drive. Work is saved to the account here.
        H("Your work is saved as you go"),
        BOX("plain", None,
            "Every cell you run and every answer you type is saved under your research ID.",
            "You can close this page and come back later: enter the same research ID and you will continue where you left off."),
        H("How to run each cell"),
        BOX("plain", None,
            "Every time you see a green **YOUR TURN** box, do these three things:",
            "**1. Copy** the code in the grey box (select it, then `Ctrl + C`, or `Cmd + C` on a Mac).",
            "**2. Paste** it into the empty code cell underneath, the one that says **Paste the code here** (`Ctrl + V`, or `Cmd + V` on a Mac).",
            "**3. Run:** click the **▶ Run** button under that cell.",
            "The result appears under the cell. Compare it with the blue **What you should see** box."),
        H("Try it now: a practice cell"),
        CELL("practice"),
        SEE("This message printed under the cell:",
            "pre:Hello there, Welcome to our machine learning research workshop!",
            "A number like `[1]` on the left: the order in which cells were run."),
        # Adapted: rules 1 and 3 refer to Colab's runtime; cells here unlock in order and are remembered.
        BOX("plain", "Three rules that save you trouble",
            "**1. One cell at a time, in order.** Each cell's ▶ Run button unlocks once the cell above it has run.",
            "**2. Read before you run.** Knowing what a cell does is the point.",
            "**3. Came back later?** Your earlier cells are remembered, so carry on from where you stopped.",
            "Each step ends with **Check your understanding**: answer in your own words before moving on."),
        ASIDE("Explanations follow Müller & Guido, **Introduction to Machine Learning with Python** (O'Reilly, 2017), Ch. 1 and 7, applied to our review data. Book quotes include page numbers."),
        H("What Is Machine Learning?", 2),
        QUOTE("Machine learning is about extracting knowledge from data.", "Müller & Guido, p. 1"),
        P("You already use it every day: film and music recommendations, spam filters and phone cameras that recognise faces all rely on machine learning."),
        H("Writing rules by hand"),
        P('Before machine learning, "intelligent" programs were built from hand-written `if` and `else` rules (p. 1). For our task, a rule-based program might say:'),
        BOX("plain", None,
            'if a review contains "love" or "delicious" → **positive**',
            'if a review contains "hate" or "cold" → **negative**'),
        BOX("warning", "Why hand-written rules fail",
            "**1. They only fit one task.** Change the task slightly, and you may rewrite everything.",
            "**2. You must already know how to decide.** Someone has to spell out every rule.",
            "*(Müller & Guido, p. 2)*",
            '*"I didn\'t love it."* contains "love", but it is **not** positive.',
            '*"Friendly staff, would return."* matches **none** of the rules.'),
        H("Learning from examples instead"),
        P("Machine learning takes a different approach. Instead of writing the rules, we give the computer many reviews **together with the correct answer** for each one, and it works out the rules itself."),
        P('Müller and Guido call this **supervised learning**: the algorithm learns from pairs of inputs and correct outputs, and can then produce an output *"for an input it has never seen before without any help from a human"* (p. 2). It is called *supervised* because the correct answers act like a teacher.'),
        H("Key words you will meet"),
        TABLE(["Word", "Meaning in our workshop"], [
            ["Sample", "One review: one row of our data"],
            ["Label", "The correct answer: positive or negative"],
            ["Feature", "Information the model uses about a review (later: the numbers made from its words)"],
            ["Training", "The model learns from labelled reviews"],
            ["Prediction", "The model's best guess for a new review; it can be wrong"],
            ["Generalisation", "Doing well on new reviews, not just the ones it learned from"],
        ]),
        H("What we will build, step by step"),
        BOX("plain", None,
            "**Step 1. Import the libraries** – bring in ready-made tools",
            "**Step 2. Load and look at the data** – read the reviews into a table",
            "**Step 3. Split the data** – keep some reviews aside for testing",
            "**Step 4. Turn text into numbers** – so a model can use the reviews",
            "**Step 5. Train the model** – it learns from the training reviews",
            "**Step 6. Evaluate the model** – how often is it right on new reviews?"),
    ),
)


# ---------------------------------------------------------------------------
# Step 1: Import the libraries
# ---------------------------------------------------------------------------
STEP1_CELLS = (
    _cell("import_libraries", "imports", "Cell 2", "Import the libraries", """
import io
import numpy as np
import pandas as pd
import sklearn
"""),
    # The Colab labels this cell "Cell 2" as well; kept as written.
    _cell("import_libraries", "versions", "Cell 2", "Check the versions", """
print("NumPy version:", np.__version__)
print("pandas version:", pd.__version__)
print("scikit-learn version:", sklearn.__version__)
"""),
)

STEP1 = WorkshopStage(
    stage_id="import_libraries", nav_label="Step 1", short_label="Import the libraries", title="Step 1: Import the Libraries",
    cells=STEP1_CELLS,
    questions=(WorkshopQuestion("q1_1", "import_libraries", "In your own words, what does each of the three libraries do in this task?"),),
    blocks=(
        P("A **library** is ready-made code that someone else wrote and tested. An `import` statement makes a library available in your program, so you can use its tools without writing them yourself. Müller and Guido build everything in their book on the same few libraries we use here."),
        BOX("did", "The three libraries we use",
            "**pandas** (nickname `pd`): loads the review file as a table, called a **DataFrame**",
            "**NumPy** (nickname `np`): stores data as fast **arrays**, the form scikit-learn needs",
            "**scikit-learn** (nickname `sklearn`): the ML library to split data, train and measure"),
        CELL("imports"),
        SEE("Nothing. No output and no error means the imports worked."),
        LIST("`as np` and `as pd` give the libraries short nicknames, so later we can write `pd.read_csv(...)` instead of `pandas.read_csv(...)`. Almost all machine learning code uses these nicknames.",
             "`io` is a small library built into Python. We need it in Step 2 to read the file you upload."),
        CELL("versions"),
        SEE("Three lines, each with a version number.", "The exact numbers do not matter."),
        ASIDE("*Müller and Guido print the versions they used at the start of their book too, because code can behave slightly differently in different versions.*"),
        P("Importing does none of the task's work yet: it does not load data or train a model. It only makes the tools available."),
        QUESTIONS_BLOCK,
    ),
)


# ---------------------------------------------------------------------------
# Step 2: Load and look at the data
# ---------------------------------------------------------------------------
STEP2_CELLS = (
    _cell("load_data", "upload", "Cell 3", "Upload the file", """
from google.colab import files

uploaded = files.upload()
""", kind="upload"),
    _cell("load_data", "keep_contents", "Cell 4", "Keep the file's contents", """
file_name = list(uploaded.keys())[0]
dataset_csv = uploaded[file_name]
print("File uploaded:", file_name)
"""),
    _cell("load_data", "read_data", "Cell 5", "Read the data", """
df = pd.read_csv(io.BytesIO(dataset_csv))
print("Data loaded.")
"""),
    _cell("load_data", "view_data", "Cell 6", "View the data", "df.head()"),
)

STEP2 = WorkshopStage(
    stage_id="load_data", nav_label="Step 2", short_label="Load and look at the data", title="Step 2: Load and Look at the Data",
    cells=STEP2_CELLS,
    questions=(
        WorkshopQuestion("q2_1", "load_data", "Look at the table you printed with df.head(). What does each row of the table represent?"),
        WorkshopQuestion("q2_2", "load_data", "Which column is the input, and which is the label?"),
    ),
    blocks=(
        P('A model can only learn from data the program can reach, so first we load the review file into the notebook. Then, before building anything, we **look at the data**. Müller and Guido call this "First Things First: Look at Your Data":'),
        QUOTE("Before building a machine learning model it is often a good idea to inspect the data, to see if the task is easily solvable without machine learning, or if the desired information might not be contained in the data.", "p. 19"),
        P('They add that *"inconsistencies in the data and unexpected measurements are very common"* (p. 19). So in this step we upload, read, and then look carefully, each in its own cell.'),
        H("2.1 Upload the review file"),
        P("Go to our lab website: [csed-research-lab.org/projects](https://csed-research-lab.org/projects). Find this workshop and click **[Dataset CSV]** to download the restaurant review file. Save it somewhere easy to find, such as your **Downloads** folder."),
        {"type": "dataset_download"},
        P("The file is in **CSV** format: plain text where each line is one row, and commas separate the columns."),
        CELL("upload"),
        SEE("1. A **Choose Files** button appears under the cell.",
            "2. Click it and select **dataset.csv**, the file you downloaded from our website.",
            "3. When the upload finishes, it looks like this:",
            "pre:dataset.csv(text/csv) - 1366043 bytes, last modified: n/a - 100% done",
            "pre:Saving dataset.csv to dataset.csv",
            "**100% done** means the whole file arrived. The cell is finished when the ▶ Run button returns."),
        CELL("keep_contents"),
        SEE("`File uploaded:` followed by your file's name.", "The variable `dataset_csv` now holds the file's contents."),
        H("2.2 Read the file into a table"),
        P("`pd.read_csv()` reads the CSV contents and turns them into a **DataFrame**: a table that Python can search, inspect and change. We call our table `df` (short for *DataFrame*)."),
        CELL("read_data"),
        SEE("`Data loaded.` The reviews are now in the table `df`.", "We have not looked at them yet: that is the next cell."),
        H("2.3 View the data"),
        P("Now look at the reviews you just loaded. `df.head()` shows the first five rows of the table."),
        CELL("view_data"),
        SEE("A table of five reviews with two columns: `text` and `sentiment`.",
            "Numbers 0 to 4 on the left: each row's position (its **index**)."),
        H("How to read the table"),
        LIST("**Each row is one sample:** a single review.",
             "**`text` is the input:** what the model will read.",
             "**`sentiment` is the label:** the correct answer the model learns from. A model can only learn what is in the data: if labels are wrong, it learns the wrong thing."),
        P("Remember: loading and looking at the data does **not** train the model. The model has not seen anything yet."),
        QUESTIONS_BLOCK,
    ),
)


# ---------------------------------------------------------------------------
# Step 3: Split the data into training and testing sets
# ---------------------------------------------------------------------------
STEP3_CELLS = (
    _cell("split_data", "make_xy", "Cell 7", "Create X and y, and look at them", """
X = np.asarray(df["text"])          # inputs: the reviews
y = np.asarray(df["sentiment"])     # labels: the correct answers

print("First review:", X[0])
print("Its label:", y[0])
print("Number of reviews:", len(X))
print("Number of labels:", len(y))
"""),
    _cell("split_data", "split", "Cell 8", "Split the data", """
from sklearn.model_selection import train_test_split

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y)
"""),
    _cell("split_data", "four_parts", "Cell 9", "Look at the four parts", """
print("Training reviews:", len(X_train), "| Training labels:", len(y_train))
print("Testing reviews:", len(X_test), "| Testing labels:", len(y_test))

print()
print("First training review (X_train[0]):", X_train[0])
print("Its label (y_train[0]):", y_train[0])
print()
print("First testing review (X_test[0]):", X_test[0])
print("Its label (y_test[0]):", y_test[0])
"""),
)

STEP3 = WorkshopStage(
    stage_id="split_data", nav_label="Step 3", short_label="Split the data", title="Step 3: Split the Data into Training and Testing Sets",
    cells=STEP3_CELLS,
    questions=(
        WorkshopQuestion("q3_1", "split_data", "Why can't we test the model on the same reviews it learned from?"),
        WorkshopQuestion("q3_2", "split_data", "What would go wrong if the reviews and their labels were shuffled separately?"),
    ),
    blocks=(
        P("Before we build a model, we need a way to know whether we can trust it on reviews it has **never seen**. Müller and Guido explain why we cannot test it on the reviews it learned from:"),
        QUOTE("Unfortunately, we cannot use the data we used to build the model to evaluate it. This is because our model can always simply remember the whole training set.", "p. 17"),
        P("Remembering is not the same as learning. So we split our labelled reviews into two parts:"),
        BOX("plain", None,
            "**Training set:** reviews the model learns from",
            "**Test set:** reviews hidden during training, used only to check the model at the end"),
        H("3.1 Separate the inputs from the labels"),
        P("scikit-learn borrows a naming habit from mathematics, where **f(x) = y**: x is the input and y is the output (p. 18). `X` (capital) holds the **inputs**, the review texts. `y` (lowercase) holds the **labels**, the correct answers."),
        CELL("make_xy"),
        SEE("The first review and its label, then two numbers that are **the same**.",
            "They match because every review has exactly one label."),
        BOX("did", "What the code did, piece by piece",
            '`df["text"]` picked one column from the table, by its name: all the reviews.',
            "`np.asarray(...)` turned it into a NumPy **array**: a plain list of values, the form scikit-learn expects.",
            "`X = ...` stored the reviews in X; the next line did the same for the labels, in y.",
            "X and y keep the same order: `X[0]` goes with `y[0]`, `X[1]` with `y[1]`, and so on."),
        H("3.2 Split into training and testing sets"),
        P("scikit-learn has a function that does the split for us: `train_test_split()`. It shuffles the reviews, then cuts them into a training set and a test set, keeping every review with its label."),
        CELL("split"),
        SEE("Nothing. The data is now split into four parts:",
            "`X_train`: reviews the model will learn from",
            "`y_train`: the correct labels for those reviews",
            "`X_test`: reviews hidden from the model until the end",
            "`y_test`: the correct labels for the hidden reviews"),
        BOX("did", "What the settings mean",
            "`test_size=0.2`: 20% of the reviews go to testing, 80% to training (20–30% is common).",
            "`random_state=42`: shuffles the reviews the same way every time, so everyone gets the same split.",
            "`stratify=y`: keeps the same mix of positive and negative reviews in both sets."),
        P("**Why shuffle?** Müller and Guido's example data was sorted by label, so taking the last part as the test set would have given examples of only one kind (p. 18). If our file listed all positive reviews first, the same thing would happen."),
        P("Now let's look at what the split made."),
        CELL("four_parts"),
        SEE("Two lines with sizes: in each line the two numbers match, one label per review.",
            "The training set is about four times the size of the test set.",
            "Then one training review with its label, and one testing review with its label.",
            "Notice: `X_train[0]` goes with `y_train[0]`. The split kept each review with its label."),
        P("The reviews are still text. Nothing has been turned into numbers yet: that is Step 4."),
        QUESTIONS_BLOCK,
    ),
)


# ---------------------------------------------------------------------------
# Step 4: Turn text into numbers
# ---------------------------------------------------------------------------
STEP4_CELLS = (
    _cell("text_to_numbers", "bag_of_words", "Cell 10", "Bag of words on three tiny reviews", """
from sklearn.feature_extraction.text import CountVectorizer

tiny_reviews = ["The food was delicious",
                "The soup was cold",
                "Delicious soup, friendly staff"]

counter = CountVectorizer()
counter.fit(tiny_reviews)                               # steps 1 and 2: split and build the vocabulary
print("Vocabulary:", counter.get_feature_names_out())
print(counter.transform(tiny_reviews).toarray())       # step 3: count
"""),
    _cell("text_to_numbers", "tfidf", "Cell 11", "Turn the real reviews into numbers", """
from sklearn.feature_extraction.text import TfidfVectorizer

vectorizer = TfidfVectorizer()
X_train_tfidf = vectorizer.fit_transform(X_train)    # learn the vocabulary and convert
X_test_tfidf = vectorizer.transform(X_test)           # convert only, same vocabulary

print("Vocabulary size:", len(vectorizer.get_feature_names_out()))
print("Training data shape:", X_train_tfidf.shape)
print("Test data shape:", X_test_tfidf.shape)
"""),
)

STEP4 = WorkshopStage(
    stage_id="text_to_numbers", nav_label="Step 4", short_label="Turn text into numbers", title="Step 4: Turn Text into Numbers",
    cells=STEP4_CELLS,
    questions=(
        WorkshopQuestion("q4_1", "text_to_numbers", "What does one row of `X_train_tfidf` represent? What does one column represent?"),
        WorkshopQuestion("q4_2", "text_to_numbers", "Why do we use `fit_transform` on the training reviews, but only `transform` on the test reviews?"),
    ),
    blocks=(
        P("A machine learning model works with numbers, not words. So each review must become a row of numbers before the model can learn from it. Müller and Guido start with the simplest way to do this, called **bag of words**, and try it on a tiny example first (p. 329). We will do the same."),
        P('Bag of words throws away word order, as if all the words were tipped into a bag, and *"only count[s] how often each word appears in each text"* (pp. 327–328). It has three steps (p. 328):'),
        BOX("plain", None,
            "**1. Split:** break each review into words, called **tokens**.",
            "**2. Build a vocabulary:** list every word that appears in any review.",
            "**3. Count:** for each review, count how often each vocabulary word appears."),
        CELL("bag_of_words"),
        SEE("pre:Vocabulary: ['cold' 'delicious' 'food' 'friendly' 'soup' 'staff' 'the' 'was']",
            "pre:[[0 1 1 0 0 0 1 1]",
            "pre: [1 0 0 0 1 0 1 1]",
            "pre: [0 1 0 1 1 1 0 0]]",
            "Read it like a table: each **row is a review**, each **column is a vocabulary word**.",
            'Row 1, "The food was delicious", has a 1 under *delicious*, *food*, *the* and *was*.',
            "Capitals and the comma are gone: words are made lowercase, and only words are kept."),
        P("That is the whole idea: **one review becomes one row of numbers, one column per word**. With real reviews the vocabulary has thousands of words, so each row is long and mostly zeros."),
        H("TF-IDF: giving informative words more weight"),
        P('Counting treats every word the same, but words like "the" and "was" appear in almost every review and say nothing about sentiment. **TF-IDF** fixes this: it gives *"high weight to any term that appears often in a particular document, but not in many documents"* (p. 336). In our tiny reviews, *friendly* and *staff* (in one review only) would get a higher weight than *delicious* and *soup* (in two reviews).'),
        P("Now we use TF-IDF on our real reviews. One rule matters: the vocabulary is learned from the **training reviews only**. The test reviews stay unseen, so we only convert them, using the vocabulary already learned (p. 336)."),
        CELL("tfidf"),
        SEE("The vocabulary size: the number of different words in the training reviews.",
            "Two shapes, written as (rows, columns): rows are reviews, columns are vocabulary words.",
            "Both shapes have the **same number of columns**, because both use the same vocabulary."),
        BOX("did", "What the code did",
            "`fit_transform`: learned the vocabulary from the training reviews **and** converted them.",
            "`transform`: converted the test reviews only, using the vocabulary already learned."),
        QUESTIONS_BLOCK,
    ),
)


# ---------------------------------------------------------------------------
# Step 5: Train the model
# ---------------------------------------------------------------------------
STEP5_CELLS = (
    _cell("train_model", "train", "Cell 12", "Create and train the model", """
from sklearn.svm import LinearSVC

clf = LinearSVC()                    # create the model object (nothing learned yet)
clf.fit(X_train_tfidf, y_train)      # train it on the training reviews and their labels
"""),
    _cell("train_model", "inside_model", "Cell 13", "Look inside the model", """
print("Classes:", clf.classes_)
print("Number of weights:", clf.coef_.shape[1])
print("First five weights:", clf.coef_[0][:5].round(2))
print("Intercept:", clf.intercept_.round(2))
"""),
)

STEP5 = WorkshopStage(
    stage_id="train_model", nav_label="Step 5", short_label="Train the model", title="Step 5: Train the Model",
    cells=STEP5_CELLS,
    questions=(
        WorkshopQuestion("q5_1", "train_model", "In your own words, what is stored inside `clf` after training?"),
        WorkshopQuestion("q5_2", "train_model", "What does `clf.fit(...)` do?"),
    ),
    blocks=(
        P("**Training** is where the model learns from the labelled training reviews. It works out a set of numbers that it will later use to decide whether a new review is positive or negative."),
        P('Every model in scikit-learn is a **class**, and *"before we can use the model, we need to instantiate the class into an object"* (p. 21). We use **LinearSVC**, a model that looks for the best **boundary** between positive and negative reviews. For text data like ours, linear models *"often work best"* (p. 332).'),
        CELL("train"),
        SEE("`LinearSVC()`. Training takes only a second or two."),
        BOX("did", "What the code did",
            "`clf = LinearSVC()` created a model object called `clf` (short for *classifier*).",
            "`clf.fit(...)` trained it on the training reviews and their labels (p. 21)."),
        H("What is inside the trained model?"),
        P('After training, the model object holds *"the information that the algorithm has extracted from the training data"* (p. 21). For LinearSVC, you can look at two attributes:'),
        BOX("plain", None,
            "`clf.coef_`: the model's **weights**, one for each word in the vocabulary",
            "`clf.intercept_`: one extra number, the starting point of the boundary",
            "The **underscore** at the end marks values learned during training, not set by you (p. 48)."),
        CELL("inside_model"),
        SEE("The two classes: `['negative' 'positive']`.",
            "The number of weights, then the first five weights: small positive and negative decimals.",
            "One intercept number."),
        P("**How LinearSVC makes a prediction:** it combines its weights with the words in a review, adds the intercept, and gets one score. A score above zero means **positive**; below zero, **negative**."),
        QUESTIONS_BLOCK,
    ),
)


# ---------------------------------------------------------------------------
# Step 6: Evaluate the model
# ---------------------------------------------------------------------------
STEP6_CELLS = (
    _cell("evaluate_model", "accuracy", "Cell 14", "Predict and measure accuracy", """
from sklearn.metrics import accuracy_score

y_pred = clf.predict(X_test_tfidf)        # the model's label for every test review

print("Model's labels:  ", y_pred[:10])
print("Correct labels:  ", y_test[:10])
print("Test accuracy: {:.2f}".format(accuracy_score(y_test, y_pred)))
"""),
    _cell("evaluate_model", "mistakes", "Cell 15", "Look at the mistakes", """
wrong = np.where(y_pred != y_test)[0]      # positions of the test reviews the model got wrong
print("Number of mistakes:", len(wrong))
print()

for i in wrong[:3]:                           # show up to three of them
    print("Review:", X_test[i])
    print("Correct:", y_test[i], "| Model said:", y_pred[i])
    print()
"""),
    _cell("evaluate_model", "own_reviews", "Cell 16", "Write your own reviews", """
my_reviews = ["Write a positive review here",
              "Write a negative review here",
              "Write a tricky review here"]

my_reviews_tfidf = vectorizer.transform(my_reviews)    # turn the new reviews into numbers
for review, label in zip(my_reviews, clf.predict(my_reviews_tfidf)):
    print(label, "->", review)
""", kind="own_reviews", instructions=(
        "1. Copy the code below → 2. Paste it into the empty code cell underneath",
        '3. Replace each **"Write ... here"** with your own restaurant review → 4. Click ▶ Run to run it',
    )),
)

STEP6 = WorkshopStage(
    stage_id="evaluate_model", nav_label="Step 6", short_label="Evaluate the model", title="Step 6: Evaluate the Model",
    cells=STEP6_CELLS,
    questions=(
        WorkshopQuestion("q6_1", "evaluate_model", "Why do we measure accuracy on the test reviews, not the training reviews?"),
        WorkshopQuestion("q6_2", "evaluate_model", "If the model labelled many reviews wrongly, what would you do to improve it? Why?"),
    ),
    blocks=(
        P('The model is trained, but can we trust it? This is where the test set from Step 3 comes in. The test reviews *"were not used to build the model"*, but we know the correct answer for each one (p. 22). So we let the model predict a label for every test review and count how often it is right.'),
        CELL("accuracy"),
        SEE("The model's labels for ten test reviews, above the ten correct labels.",
            "Where the two match, the model was right.",
            "Then the **test accuracy**: a number between 0 and 1."),
        BOX("did", "What the code did",
            "`clf.predict(...)` gave a label to every test review and stored them in `y_pred`.",
            "`accuracy_score` compared `y_pred` with `y_test`: 0.85 means 85% correct (p. 22)."),
        P("The accuracy tells us how often the model is right. Next, let's look at the reviews it got wrong."),
        CELL("mistakes"),
        SEE("The number of mistakes, then up to three reviews the model got wrong.",
            "Read them carefully. What do you notice about these reviews?",
            "If there are 0 mistakes, no reviews are shown: the model got every test review right."),
        P("The real goal is **generalisation**: labelling reviews nobody has seen before. New reviews are turned into numbers the same way as in Step 4, then the model predicts."),
        {
            "type": "own_reviews_guide",
            "items": [
                {"label": "For example, replace this positive placeholder:", "from": '"Write a positive review here"', "to": '"The pizza was hot and the waiter was so kind"'},
                {"label": "And this negative placeholder:", "from": '"Write a negative review here"', "to": '"We waited forever and the fries were soggy"'},
            ],
            "notes": [
                "**The tricky one is up to you:** write a review you think might fool the model.",
                'Only change the words **between the quotes**. Keep the `"` marks and the commas.',
                "Please write your own reviews; don't copy the examples above.",
            ],
        },
        CELL("own_reviews"),
        SEE("One line for each of your three reviews: the model's label, an arrow, then your review.",
            "For example:",
            "pre:positive -> The pizza was hot and the waiter was so kind",
            "pre:negative -> We waited forever and the fries were soggy",
            "Did the model agree with you? Change a review and click ▶ Run again to try another."),
        BOX("did", "What the code did",
            "`my_reviews = [...]` stored your three reviews in a list.",
            "`vectorizer.transform(...)` turned them into numbers, using the vocabulary from Step 4.",
            "`clf.predict(...)` gave each review a label: positive or negative.",
            "`zip(...)` paired each review with its label, and the `for` loop printed each pair."),
        # Adapted: the "/" and "\" note reflects this platform's code-safety check.
        BOX("warning", "Got an error?",
            'Each review must stay inside its own `"quotes"`, with a comma between reviews. Don\'t use `"` inside your review text.',
            "Also leave out the characters `/` and `\\` in your reviews."),
        QUESTIONS_BLOCK,
    ),
)


# ---------------------------------------------------------------------------
# Finish
# ---------------------------------------------------------------------------
FINISH = WorkshopStage(
    stage_id="finish", nav_label="Finish", short_label="Workshop complete", title="You Did It: Workshop Complete",
    blocks=(
        P("Congratulations! You built a machine learning model that reads restaurant reviews and labels them as positive or negative, including reviews it had never seen. You loaded and looked at real data, split it, turned text into numbers, trained a model, and evaluated it."),
        P("To finish, please complete the steps below."),
        # Adapted: the Colab's "Save your notebook to Google Drive" step is not needed; work is saved
        # under the learner's research ID, which replaces the notebook link.
        {"type": "post_survey"},
        {
            "type": "checklist",
            "title": "Your gift card: completion checklist",
            "intro": "You will receive your gift card once you have completed **all** of these:",
            "items": [
                {"text": "1. Completed the **pre-survey** before the workshop", "auto": None},
                {"text": "2. Ran **all 16 cells** in this workshop (Steps 1 to 6)", "auto": "cells"},
                {"text": "3. Answered every **Check your understanding** question (q1_1 to q6_2)", "auto": "answers"},
                {"text": "4. Completed the **post-survey** with the same research ID (Finish)", "auto": None},
            ],
            "note": "Questions? Ask a facilitator before you leave the room.",
        },
        P("Thank you for taking part in our research. We hope you enjoyed building your first machine learning model!"),
        ASIDE("*SJSU Computer Science Education Research Lab. This material is based upon work supported by the U.S. National Science Foundation under Grant No. 2451781.*"),
    ),
)

STAGES: tuple[WorkshopStage, ...] = (START, STEP1, STEP2, STEP3, STEP4, STEP5, STEP6, FINISH)
# Stages a learner completes; "finish" is the closing page shown after the last one.
LEARNING_STAGES: tuple[WorkshopStage, ...] = STAGES[:-1]
STAGE_IDS = tuple(stage.stage_id for stage in STAGES)
CELLS: tuple[WorkshopCell, ...] = tuple(cell for stage in STAGES for cell in stage.cells)
CELLS_BY_ID = {cell.cell_id: cell for cell in CELLS}
QUESTIONS: tuple[WorkshopQuestion, ...] = tuple(question for stage in STAGES for question in stage.questions)
QUESTIONS_BY_ID = {question.question_id: question for question in QUESTIONS}
STAGES_BY_ID = {stage.stage_id: stage for stage in STAGES}


def stage(stage_id: str) -> WorkshopStage:
    try:
        return STAGES_BY_ID[stage_id]
    except KeyError:
        raise ValueError(f"unknown workshop stage: {stage_id}") from None


def cell(cell_id: str) -> WorkshopCell:
    try:
        return CELLS_BY_ID[cell_id]
    except KeyError:
        raise ValueError(f"unknown workshop cell: {cell_id}") from None


def cells_before(cell_id: str) -> list[WorkshopCell]:
    """Every workshop cell that runs before this one, in notebook order."""
    index = CELLS.index(cell(cell_id))
    return list(CELLS[:index])


def next_stage_id(stage_id: str) -> str:
    index = STAGE_IDS.index(stage(stage_id).stage_id)
    return STAGE_IDS[min(index + 1, len(STAGE_IDS) - 1)]


def own_reviews_written(code: str) -> bool:
    """The last cell asks learners to replace all three placeholder reviews."""
    return not any(placeholder in code for placeholder in OWN_REVIEW_PLACEHOLDERS)
