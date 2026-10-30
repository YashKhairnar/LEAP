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
from .lesson_code import fixed_code_experiments, fixed_lesson_code

AUTHORED_CONTENT_VERSION = "authored_content_v4"


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
        # Each pool holds (prompt, correct, options, explanation, hint). Variants rotate so a
        # learner who asks for a similar question, or reaches the same pool on a later step,
        # sees a different item.
        "questions": {
            "operation": [
                ("Which line reads reviews.csv into a table you can work with?", 'df = pd.read_csv("reviews.csv")', ['df = pd.read_csv("reviews.csv")', 'df = open("reviews.csv")', "print(df.head())"],
                 "pd.read_csv parses the file into a DataFrame with named columns. open() only gives you the raw file to read line by line, and head() shows rows that are already loaded.",
                 "You need a line that reads the file and turns it into rows and columns."),
                ('After loading, print("Rows:", len(df)) shows 3000. What does 3000 count?', "Reviews, one per row", ["Reviews, one per row", "Words across all the reviews", "Columns in the file"],
                 "len(df) counts rows, and each row holds one review, so 3,000 reviews were loaded. It doesn't count words, and the file has only three columns.",
                 "Think about what one row of the DataFrame holds."),
            ],
            "variable": [
                ("Which column is the input the model reads?", "review", ["review", "sentiment", "the row number"],
                 "The review text is the input. Sentiment is the answer the model learns to give, and the row number is just a position in the table.",
                 "The input is what the model looks at. The label is what it should answer."),
                ("Why look at df.head() before going further?", "To check the columns and labels look right", ["To check the columns and labels look right", "To train the model on five reviews", "To remove the rows you looked at"],
                 "head() only displays rows. It is a quick check that the file loaded with the columns and labels you expect. Nothing is trained or removed.",
                 "Does head() change df, or does it only show part of it?"),
            ],
            "boundary": [
                ("A classmate sorts the review column alphabetically but leaves sentiment as it is. What goes wrong?", "Reviews end up next to the wrong labels", ["Reviews end up next to the wrong labels", "Nothing, because sentiment does not depend on order", "pandas raises an error and stops"],
                 "The pairing is kept by row position. Sorting one column on its own moves the reviews but not their labels, so most reviews now sit beside another review's answer. pandas gives no warning.",
                 "How does a DataFrame know which label belongs to which review?"),
                ("Why does each review need its sentiment in the same row?", "The model learns by comparing text with answers", ["The model learns by comparing text with answers", "pandas cannot load a file without labels", "It makes the file smaller to store"],
                 "Training shows the model a review and its correct answer, thousands of times. Without the matching label there is nothing to learn from. pandas would happily load a file with no labels.",
                 "Think about what the model needs to see in order to learn."),
                ("Which change would break the data before training?", "Shuffling only the sentiment column", ["Shuffling only the sentiment column", "Shuffling whole rows together", "Printing the first ten rows"],
                 "Shuffling whole rows moves each review with its label, so the pairs survive, and printing changes nothing. Shuffling only the sentiment column scrambles which answer goes with which review.",
                 "Which option moves a label without its review?"),
            ],
            "ordering": [
                ("What is the right order for this stage?", "import pandas → read the CSV → check rows", ["import pandas → read the CSV → check rows", "check rows → import pandas → read the CSV", "read the CSV → import pandas → check rows"],
                 "pandas must be imported before you can call pd.read_csv, and you can only check rows once the data is loaded.",
                 "Which step needs the step before it to have run?"),
                ("Where does loading fit in the whole sentiment pipeline?", "load → split → text to numbers → train", ["load → split → text to numbers → train", "train → load → split → text to numbers", "split → load → train → text to numbers"],
                 "Every later step works on the loaded data: you split it into training and test sets, turn the text into numbers, then train. Nothing can be split or trained before the data exists.",
                 "Which steps need the data to exist already?"),
            ],
            "transfer": [
                ("A help desk wants to sort tickets into billing or technical. What should one training row hold?", "One ticket's text and its category", ["One ticket's text and its category", "Only the ticket's text", "The total number of tickets"],
                 "It's the same idea as reviews: the ticket text is the input and its category is the label. Without the category, the model has no answer to learn from.",
                 "Map it onto reviews: what plays the role of the review, and what plays the sentiment?"),
                ("Your spam file has 2,000 emails, but only 1,200 are marked spam or not spam. Which can teach the model?", "The 1,200 marked emails", ["The 1,200 marked emails", "All 2,000 emails equally", "The 800 unmarked emails"],
                 "A model learns from examples with known answers. The 800 unmarked emails have no label, so they can't show the model what the right answer is.",
                 "What does every training example need besides the input?"),
            ],
        },
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
        "result": "This code prints nothing. It creates X_train and y_train (2,400 reviews and labels) and X_test and y_test (600). Each set is exactly half positive and half negative.",
        "why": "Split reviews and labels in one call. Splitting them separately, or shuffling one list, would pair most reviews with someone else's label; nothing crashes, the model just learns nonsense. And never let test reviews into training: a score on reviews the model has seen measures memory, not skill.",
        "code_explanation": [
            'train_test_split(df["review"], df["sentiment"], ...) — splits reviews and labels together, at the same random positions.',
            "test_size=0.2 — keeps 20% of the 3,000 reviews, 600 of them, for testing.",
            "random_state=42 — makes the split the same every run.",
            'stratify=df["sentiment"] — keeps the positive/negative mix equal in both sets.',
        ],
        "questions": {
            "operation": [
                ("How many reviews end up in X_test?", "600", ["600", "2,400", "20"],
                 "test_size=0.2 keeps 20% of the 3,000 reviews: 600. 2,400 is the training set, and 20 is the percentage, not a count.",
                 "One fifth of 3,000."),
                ("A dataset has 1,000 reviews and test_size=0.25. How many are used for training?", "750", ["750", "250", "1,000"],
                 "25%, or 250 reviews, are held out, leaving 750 to train on. Every review goes into exactly one of the two sets.",
                 "Training gets whatever isn't held out."),
            ],
            "variable": [
                ("What does y_train hold?", "The labels of the 2,400 training reviews", ["The labels of the 2,400 training reviews", "The text of the 2,400 training reviews", "The predictions for the test set"],
                 "y holds labels: y_train has positive or negative for each training review, in the same order as X_train. The text is in X_train, and predictions don't exist yet.",
                 "X is the text; y is the answer."),
                ("How many of the test reviews are positive?", "300", ["300", "600", "1,200"],
                 "The dataset is half positive and stratify keeps that mix, so 300 of the 600 test reviews are positive. 600 is the whole test set, and 1,200 is the positive count in training.",
                 "Half of the test set."),
            ],
            "boundary": [
                ("Someone shuffles y_train on its own after splitting. What happens?", "Reviews get the wrong labels, with no error", ["Reviews get the wrong labels, with no error", "pandas raises an error", "Nothing; labels don't depend on order"],
                 "X_train and y_train are paired by position. Shuffling one of them attaches most reviews to another review's label. The lengths still match, so nothing complains.",
                 "How does each review know its label?"),
                ("A random split puts 340 positive and 260 negative reviews in the test set. What would have prevented that?", 'stratify=df["sentiment"]', ['stratify=df["sentiment"]', "random_state=42", "test_size=0.3"],
                 "stratify keeps each set's positive/negative mix equal to the whole dataset's, so the test set would be 300/300. random_state only makes a split repeatable, and test_size changes the size, not the mix.",
                 "Which argument is about the mix of labels?"),
                ("Which reviews may the model learn from?", "Only the 2,400 training reviews", ["Only the 2,400 training reviews", "All 3,000 reviews", "Only the 600 test reviews"],
                 "The 600 test reviews must stay unseen so the final score is honest. Every later learning step, TF-IDF included, uses the training reviews only.",
                 "Which set is kept for the final check?"),
            ],
            "ordering": [
                ("Where does the split belong?", "After loading, before TF-IDF and training", ["After loading, before TF-IDF and training", "After training, before evaluation", "After calculating accuracy"],
                 "TF-IDF and training must learn only from training reviews, so the split has to come first. Splitting later would let test reviews leak in.",
                 "Which later steps must not see the test reviews?"),
            ],
            "transfer": [
                ("A photo dataset has 5,000 cats and 5,000 dogs. With test_size=0.2 and stratify, how many test cats?", "1,000", ["1,000", "2,000", "500"],
                 "The test set is 20% of 10,000 = 2,000 photos, and stratify keeps it half cats: 1,000. 2,000 is the whole test set.",
                 "Find the test-set size, then keep the 50/50 mix."),
            ],
        },
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
        "result": "This code prints nothing. X_train_tfidf is a 2,400 × 4,558 table and X_test_tfidf is 600 × 4,558: the same columns, in the same order.",
        "why": "Fit the vectorizer on training reviews only, then transform the test reviews with it. If test reviews help build the vocabulary and word rarity, the test isn't truly unseen any more. A separate fit on test text would also create different columns, so the numbers wouldn't line up with what the model learned.",
        "code_explanation": [
            "TfidfVectorizer() — creates a vectorizer that hasn't learned any vocabulary yet.",
            "vectorizer.fit_transform(X_train) — learns the vocabulary and word rarity from training reviews, then converts them.",
            "vectorizer.transform(X_test) — converts test reviews with the training vocabulary. Words never seen in training are ignored.",
            "X_train_tfidf, X_test_tfidf — tables with one row per review and one column per vocabulary word.",
        ],
        "questions": {
            "operation": [
                ("How many columns does X_test_tfidf have?", "4,558, the same as X_train_tfidf", ["4,558, the same as X_train_tfidf", "600, one per test review", "As many as the test vocabulary"],
                 "transform reuses the training vocabulary, so the test table has the same 4,558 columns. 600 is the number of rows, and a test-only vocabulary would break the alignment.",
                 "Which reviews decided the columns?"),
                ("Which call learns the vocabulary?", "vectorizer.fit_transform(X_train)", ["vectorizer.fit_transform(X_train)", "vectorizer.transform(X_test)", "TfidfVectorizer()"],
                 "fit_transform learns the vocabulary and word rarity from training reviews and converts them. transform only applies what was learned, and the constructor creates an empty vectorizer.",
                 "Learning is the 'fit' part."),
            ],
            "variable": [
                ("In \"The mic is great.\", why does 'mic' get a higher weight than 'the'?", "'mic' is rare across reviews; 'the' is everywhere", ["'mic' is rare across reviews; 'the' is everywhere", "'mic' appears more often in this review", "Longer words get higher weights"],
                 "Both appear once in this review, so their term frequency is equal. IDF makes the difference: 'mic' is in very few reviews (IDF 7.69) while 'the' is in most (1.81). Word length plays no part.",
                 "Both words appear once. What else differs?"),
                ("What does a 0 in a review's TF-IDF row mean?", "That word doesn't appear in the review", ["That word doesn't appear in the review", "The word is negative", "The value is missing"],
                 "Each column is a vocabulary word, and a short review uses only a few of the 4,558, so almost every entry is 0. It isn't a sentiment and it isn't missing data.",
                 "Most words aren't in any one review."),
            ],
            "boundary": [
                ("A test review contains a word never seen in training. What does transform do with it?", "Ignores it: there's no column for it", ["Ignores it: there's no column for it", "Adds a new column", "Raises an error"],
                 "The columns were fixed by the training vocabulary. transform simply skips unknown words, which keeps the test table aligned with the training table.",
                 "Can transform change the vocabulary?"),
                ("Why is the score less trustworthy if test reviews shaped the vocabulary?", "The test reviews were no longer fully unseen", ["The test reviews were no longer fully unseen", "The vocabulary becomes too small", "TF-IDF can't handle test reviews"],
                 "If test reviews helped decide the columns and word rarity, the pipeline was prepared with knowledge of them, which can flatter the score. Vocabulary size and TF-IDF's abilities aren't the problem.",
                 "What makes a test fair?"),
                ("'the' appears in most reviews. What weight does TF-IDF tend to give it?", "A low weight", ["A low weight", "A high weight", "Always exactly 1"],
                 "Words that appear almost everywhere say little about any one review, so their IDF, and therefore their weight, is low. In the running review 'the' gets 0.20, the smallest.",
                 "Does a word found in every review tell you much?"),
            ],
            "ordering": [
                ("Which order avoids leaking test information?", "split → fit_transform train → transform test", ["split → fit_transform train → transform test", "fit_transform all reviews → split", "transform test → split → fit_transform train"],
                 "Split first so the vectorizer only learns from training reviews, then reuse it on the test reviews. Vectorizing everything before splitting lets test reviews shape the vocabulary.",
                 "When does the vectorizer first see any text?"),
            ],
            "transfer": [
                ("For spam detection, what would one row of the TF-IDF table represent?", "One email as word weights", ["One email as word weights", "One word across all emails", "Whether the email is spam"],
                 "Rows are documents and columns are words, so one row is one email described by its word weights. The spam label is separate, in y.",
                 "Rows are documents; columns are words."),
            ],
        },
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
        "result": "This code prints nothing. model now holds 4,558 learned word weights. The Try it step prints a few of them.",
        "why": "Creating LogisticRegression() learns nothing; only fit does, and only from the training reviews and their labels. The weights also show the model's limits: it scores words one at a time, so it can't tell that 'not bad' is praise. 'not' and 'bad' are both strongly negative.",
        "code_explanation": [
            "LogisticRegression(max_iter=1000, random_state=42) — creates an untrained classifier. max_iter allows enough learning steps.",
            "model.fit(X_train_tfidf, y_train) — learns one weight per word from the training reviews and their labels.",
            "model.coef_ — after fitting, the 4,558 word weights. Positive means 'pushes towards positive'.",
            "model.classes_ — after fitting, ['negative', 'positive']: the two labels it can predict.",
        ],
        "questions": {
            "operation": [
                ("Which call fills in the word weights?", "model.fit(X_train_tfidf, y_train)", ["model.fit(X_train_tfidf, y_train)", "LogisticRegression(max_iter=1000)", "vectorizer.transform(X_test)"],
                 "fit is where weights are learned from the training features and labels. The constructor only creates an empty model, and transform converts text.",
                 "Which call sees both the features and the labels?"),
                ("A review's only word is 'great', with TF-IDF 1.0. Ignoring the bias, which way is it pushed?", "Strongly towards positive", ["Strongly towards positive", "Strongly towards negative", "Neither; one word isn't enough"],
                 "Its score is 4.92 × 1.0, a large positive number, so the model leans strongly positive. A negative weight would push the other way.",
                 "Is the weight for 'great' above or below 0?"),
            ],
            "variable": [
                ("What does y_train provide during fit?", "The correct label for each training review", ["The correct label for each training review", "The TF-IDF weights", "The test reviews"],
                 "fit compares its guesses with these labels and adjusts the weights. The features come from X_train_tfidf, and test reviews are never used here.",
                 "fit needs the right answers to learn from."),
                ("How many word weights does the model learn?", "4,558, one per vocabulary word", ["4,558, one per vocabulary word", "2,400, one per review", "2, one per label"],
                 "There's one weight for each column of the TF-IDF table, which is one per vocabulary word. Reviews are the examples it learns from, not the things it learns.",
                 "Weights match the columns, not the rows."),
            ],
            "boundary": [
                ("Why does the model call 'The food was not bad at all.' negative?", "It scores words separately; 'not' and 'bad' are negative", ["It scores words separately; 'not' and 'bad' are negative", "The review is too short", "It never trained on food reviews"],
                 "Each word adds its own weight: 'not' (−4.60) and 'bad' (−3.42) both push negative, so the total is negative even though together they mean 'good'. The model doesn't see word pairs or order, and it did train on Yelp food reviews.",
                 "Does the model look at words one at a time, or in pairs?"),
                ("Which data should fit see?", "Only the training features and labels", ["Only the training features and labels", "The training and test reviews", "The test labels"],
                 "The test reviews and labels must stay unseen so the final accuracy is honest. Fitting on them would tune the weights to the very answers being checked.",
                 "Which set is kept for the final check?"),
                ("'and' gets a weight of +2.10. Why might a common word get a big weight?", "It appears more in positive training reviews", ["It appears more in positive training reviews", "The model knows 'and' is a happy word", "Common words always get large weights"],
                 "The model only learns patterns in the data. In these reviews 'and' turns up more in positive ones (people list things they liked), so it picked up a positive weight. The model doesn't understand meaning, and common words aren't weighted up automatically.",
                 "The model only sees which words go with which labels."),
            ],
            "ordering": [
                ("Which order trains the classifier?", "TF-IDF on train → create model → fit", ["TF-IDF on train → create model → fit", "create model → fit → TF-IDF on train", "fit → create model → TF-IDF on train"],
                 "fit needs numeric features and an existing model, so vectorize first, create the model, then fit.",
                 "fit needs both the model and numeric features."),
            ],
            "transfer": [
                ("A spam classifier is trained the same way. Which word would likely get a large spam weight?", "A word common in spam, like 'free'", ["A word common in spam, like 'free'", "A word in all emails, like 'the'", "A word that never appears"],
                 "Weights reflect which label a word tends to appear with. Words frequent in spam but rare in normal email get large spam weights; words used everywhere get small ones, and absent words get none.",
                 "Weights come from which label a word appears with."),
            ],
        },
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
        "questions": {
            "operation": [
                ("Which call produces the labels for the test reviews?", "model.predict(X_test_tfidf)", ["model.predict(X_test_tfidf)", "model.fit(X_test_tfidf, y_test)", "vectorizer.fit_transform(X_test)"],
                 "predict applies the learned weights and returns labels. fit on the test set would train on the answers, and fit_transform on test text would rebuild the vocabulary.",
                 "You want to apply the model, not train it."),
                ("How many labels are in y_pred?", "600", ["600", "10", "2,400"],
                 "predict ran on all 600 test reviews; the loop just prints the first 10. 2,400 is the training set.",
                 "Which reviews were passed to predict?"),
            ],
            "variable": [
                ("What does y_pred contain?", "A predicted label for each test review", ["A predicted label for each test review", "The true labels of the test reviews", "The word weights"],
                 "y_pred holds the model's guesses. The true labels are in y_test, which predict never sees, and the weights live inside the model.",
                 "Is it the model's answer or the real one?"),
                ("predict_proba gives [0.12, 0.88] for \"The mic is great.\". What does 0.88 mean?", "88% probability of positive", ["88% probability of positive", "88% of its words are positive", "88% of the test set is done"],
                 "The second column is the positive class, because classes_ is ['negative', 'positive'], so the model gives it 88%. predict picks the class with the higher probability: positive.",
                 "classes_ lists negative first, then positive."),
            ],
            "boundary": [
                ("A teammate fits a new TfidfVectorizer on one review before predicting. Why is that wrong?", "Its columns won't match the model's weights", ["Its columns won't match the model's weights", "One review is too short to predict", "predict only works on 600 reviews"],
                 "The weights belong to the 4,558 training columns. A vectorizer fitted on one review has a handful of different columns, so the numbers no longer line up with the weights. Reuse the fitted vectorizer's transform.",
                 "Which columns do the weights belong to?"),
                ("Does predict change the model's weights?", "No; it only applies them", ["No; it only applies them", "Yes, a little for each review", "Yes, when it gets one wrong"],
                 "Learning happens only in fit. predict reads the weights and returns labels; it can't even tell whether it was right, because it never sees y_test.",
                 "Does predict see the true labels?"),
                ("A review uses only words never seen in training. What happens?", "Its row is all zeros, so it's a guess", ["Its row is all zeros, so it's a guess", "The vectorizer adds the new words", "predict raises an error"],
                 "transform ignores unknown words, so every column is 0 and no word weights contribute. The model falls back on its built-in starting point, which is effectively a guess. Nothing is added and nothing crashes.",
                 "What does transform do with unknown words?"),
            ],
            "ordering": [
                ("Which order classifies a brand-new review?", "transform with fitted vectorizer → predict", ["transform with fitted vectorizer → predict", "predict → transform with fitted vectorizer", "fit a new vectorizer → predict"],
                 "The new review must be turned into the same 4,558 columns with the fitted vectorizer before the model can score it. Fitting a new vectorizer would create different columns.",
                 "The model only understands the training columns."),
            ],
            "transfer": [
                ("This model sees the review 'Not good.' What does it predict?", "negative", ["negative", "positive", "It can't decide"],
                 "'not' has the strongest negative weight (−4.60) and outweighs 'good' (+3.30), so it predicts negative. That's right here, unlike 'not bad at all', where both words push the same way.",
                 "Compare the weights of the two words."),
            ],
        },
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
        "questions": {
            "operation": [
                ("Out of 600 test reviews, 150 were misclassified. What is the accuracy?", "0.75 (75%)", ["0.75 (75%)", "0.25 (25%)", "150"],
                 "450 of the 600 are right, and 450 ÷ 600 = 0.75. 0.25 is the error rate, and 150 is the count of mistakes.",
                 "Accuracy counts the right answers."),
                ("Of 300 negative test reviews, the model labels 241 negative. What is negative recall?", "About 0.80", ["About 0.80", "About 0.40", "241"],
                 "Recall = caught ÷ all true negatives = 241 ÷ 300 ≈ 0.80. 241 is the count, and 0.40 divides by all 600 reviews instead of the 300 negative ones.",
                 "Divide by the number of truly negative reviews."),
            ],
            "variable": [
                ("What does the support column show?", "How many test reviews have each label", ["How many test reviews have each label", "How confident the model is", "How many predictions were right"],
                 "Support is just the count of true examples per label: 300 negative and 300 positive. It tells you how much evidence each row of the report rests on.",
                 "It's a count of true labels."),
                ("What is y_test during evaluation?", "The true labels of the test reviews", ["The true labels of the test reviews", "The model's predictions", "The training labels"],
                 "y_test is the answer key the predictions are compared against. Predictions are in y_pred, and training labels aren't used for evaluation.",
                 "What do you compare the predictions with?"),
            ],
            "boundary": [
                ("Positive recall is 0.98 but negative recall is 0.40. What does that tell you?", "It misses most negative reviews", ["It misses most negative reviews", "It's an excellent model overall", "There are more negative reviews"],
                 "Negative recall of 0.40 means only 40% of truly negative reviews are caught; the other 60% are called positive. High positive recall, or high accuracy, can hide that.",
                 "Recall is about catching each label's own reviews."),
                ("Which reviews should accuracy be measured on?", "The 600 test reviews the model never saw", ["The 600 test reviews the model never saw", "The 2,400 training reviews", "All 3,000 reviews"],
                 "Training reviews flatter the model because it learned from them. Only unseen test reviews show how it handles new ones.",
                 "Which reviews are new to the model?"),
                ("The model is 83% accurate. Does every review have an 83% chance of being right?", "No; some reviews are much harder than others", ["No; some reviews are much harder than others", "Yes, exactly", "No; it means 83 reviews were right"],
                 "83% is an average over the test set. Plain reviews like 'I loved it.' are easy; negation, sarcasm and rare words, like 'not bad at all' or 'unacceptable', are much harder. And it's a fraction, not a count.",
                 "Is every review equally easy?"),
            ],
            "ordering": [
                ("Which order completes the sentiment pipeline?", "fit → predict test reviews → compare with y_test", ["fit → predict test reviews → compare with y_test", "compare with y_test → fit → predict test reviews", "predict test reviews → fit → compare with y_test"],
                 "You need a fitted model to predict, and predictions to compare. Evaluating before predicting has nothing to measure.",
                 "What does evaluation need to exist first?"),
            ],
            "transfer": [
                ("A medical test finds 95% of sick patients but flags many healthy ones too. Which number is the 95%?", "Recall for 'sick'", ["Recall for 'sick'", "Overall accuracy", "Support for 'healthy'"],
                 "Recall for a class is the share of its true members that are caught: 95% of sick patients. Accuracy mixes both classes, and support is just a count.",
                 "Which measure is 'how many of this class were caught'?"),
            ],
        },
        "review": "Accuracy = correct ÷ total, here 83.3%. Check recall per label too: this model catches 86% of positive reviews but 80% of negative.",
    },
}


# Each pool holds (prompt, correct, options, explanation, hint); see the sentiment pilot stage.
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
        "questions": {
            "operation": [
                ("Which call turns each row of 64 pixel values into an 8 × 8 image?", "reshape(-1, 1, 8, 8)", ["reshape(-1, 1, 8, 8)", "reshape(-1, 64)", "argmax(dim=1)"],
                 "reshape(-1, 1, 8, 8) folds each row into one channel of 8 rows and 8 columns. reshape(-1, 64) keeps the flat row, and argmax picks the largest score much later, at prediction time.",
                 "You want 1 channel, 8 rows and 8 columns."),
                ("The file has 5,620 rows. What size does the -1 in reshape(-1, 1, 8, 8) become?", "5620", ["5620", "64", "Nothing; -1 makes an empty array"],
                 "-1 asks NumPy to work out that size from the others. 5,620 × 1 × 8 × 8 uses every number, so N becomes 5,620. 64 is the pixels in one image, not the number of images.",
                 "Every other size is fixed. How many images are there?"),
            ],
            "variable": [
                ("A pixel in images.csv has the value 0. What does that mean?", "That pixel is black", ["That pixel is black", "That pixel is white", "That pixel's value is missing"],
                 "Brightness runs from 0 (black) to 16 (white). A 0 is a real reading, not missing data; most of the border of every image is 0.",
                 "Brightness goes from 0 to 16. Which end is dark?"),
                ("What does labels[42] hold?", "The digit shown in image 42", ["The digit shown in image 42", "The brightness of pixel 42", "How many images are labeled 42"],
                 "labels has one entry per image, in the same order as images, so labels[42] is the digit that image 42 shows. Pixel values live in images, not labels.",
                 "labels has one entry for each image."),
            ],
            "boundary": [
                ("Why reshape to 8 × 8 instead of keeping 64 numbers in a row?", "The CNN needs to know which pixels are neighbours", ["The CNN needs to know which pixels are neighbours", "It makes the file smaller", "PyTorch can't store more than 8 numbers per row"],
                 "Strokes are made of nearby pixels. In an 8 × 8 grid, a pixel's neighbours above and below stay next to it; in a flat row of 64 they end up 8 places away. The file size doesn't change.",
                 "In a flat row, how far apart are two pixels that sit on top of each other?"),
                ("What must stay true after loading?", "Image i is paired with label i", ["Image i is paired with label i", "The labels are sorted from 0 to 9", "Every image shows the same digit"],
                 "TensorDataset pairs images and labels by position. Sorting the labels on their own would attach the wrong digit to most images, and the network would learn nonsense without any error.",
                 "How does the dataset know which digit goes with which image?"),
                ("Which statement about the raw pixel values is correct?", "They are brightness readings from 0 to 16", ["They are brightness readings from 0 to 16", "They are already scaled between 0 and 1", "They are the digit labels"],
                 "The file stores brightness from 0 to 16. Scaling to 0–1 happens later, when images go into the model. The labels are a separate column.",
                 "Look at the numbers in the example image."),
            ],
            "ordering": [
                ("Which order loads the images correctly?", "read CSV → reshape pixels → pair with labels", ["read CSV → reshape pixels → pair with labels", "pair with labels → read CSV → reshape pixels", "reshape pixels → read CSV → pair with labels"],
                 "You need the numbers before you can reshape them, and you can only pair images with labels once both arrays exist.",
                 "Which step needs the step before it to have run?"),
            ],
            "transfer": [
                ("A colour photo is 32 × 32 pixels with red, green and blue values. What is its shape?", "(3, 32, 32)", ["(3, 32, 32)", "(1, 32, 32)", "(32, 32, 3, 1)"],
                 "Colour images have three channels, one each for red, green and blue, and PyTorch puts channels first: (C, H, W) = (3, 32, 32). One channel would mean grayscale.",
                 "Channels come first. How many colour values does each pixel have?"),
            ],
        },
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
        "result": "This code prints nothing. It creates train_loader and test_loader, which the next stages loop over. Each full training batch has shape (128, 1, 8, 8).",
        "why": "The divide-by-16 isn't in this stage's code. It happens as images enter the model, written images_batch / 16.0, in both training and prediction. A common mistake is scaling in one place and forgetting the other: the model then sees inputs 16 times larger than it learned on, and its predictions fall apart without any error.",
        "code_explanation": [
            "torch.Generator().manual_seed(42) — fixes the randomness so everyone gets the same split and order.",
            "random_split(dataset, [train_size, test_size], ...) — randomly divides the images into 4,496 for training and 1,124 for testing.",
            "DataLoader(train_dataset, batch_size=128, shuffle=True) — serves training images 128 at a time, in a new random order each pass.",
            "DataLoader(test_dataset, batch_size=256) — serves test images in bigger batches. Their order doesn't matter.",
        ],
        "questions": {
            "operation": [
                ("A pixel has the value 8. What goes into the CNN?", "0.5", ["0.5", "8", "128"],
                 "Every pixel is divided by 16 before it reaches the model, so 8 becomes 0.5. The model never sees the raw 8, and 128 is the batch size, not a pixel value.",
                 "Divide by the largest possible pixel value."),
                ("A loader has 50 images and batch_size=16. How many batches does it serve?", "4", ["4", "3", "16"],
                 "50 = 3 × 16 + 2, so there are three full batches of 16 and a fourth, smaller batch with the 2 left over. Leftover images still get a batch.",
                 "Do the full batches use up all 50 images?"),
            ],
            "variable": [
                ("What shape is one full batch from train_loader?", "(128, 1, 8, 8)", ["(128, 1, 8, 8)", "(4496, 1, 8, 8)", "(1, 8, 8)"],
                 "Each batch holds 128 images, and each is still 1 × 8 × 8. (4496, 1, 8, 8) is the whole training set, and (1, 8, 8) is a single image.",
                 "A batch is a group of images, not the whole set."),
                ("What is test_loader used for?", "Checking the model after training", ["Checking the model after training", "Updating the weights during training", "Choosing the batch size"],
                 "The test images never update the weights. They're used only at the end, to see how the model does on images it hasn't learned from.",
                 "Which set must stay unseen while the model learns?"),
            ],
            "boundary": [
                ("Training divides images by 16, but the prediction code forgets to. What happens?", "Predictions get much worse, with no error", ["Predictions get much worse, with no error", "PyTorch raises an error", "Nothing; the CNN adjusts automatically"],
                 "The model learned on values from 0 to 1. Raw values up to 16 are far outside that range, so its scores go wrong, but the shapes still match, so nothing crashes. The model has no way to rescale inputs by itself.",
                 "Does dividing by 16 change the shape of the input?"),
                ("Why shuffle the training batches but not the test batches?", "Shuffling helps learning; test order doesn't matter", ["Shuffling helps learning; test order doesn't matter", "Shuffling the test set would leak labels", "Test images cannot be shuffled"],
                 "A fresh random order stops the model picking up anything from the file's order while it trains. Testing just counts right and wrong answers, so order makes no difference there. Shuffling never leaks labels.",
                 "Does the order of the test images change the accuracy?"),
                ("Which images may update the CNN's weights?", "Only the 4,496 training images", ["Only the 4,496 training images", "All 5,620 images", "Only the 1,124 test images"],
                 "The test images must stay unseen until the end, or the test score would be too optimistic. Only training batches should ever reach the update step.",
                 "Which set is kept aside for the final check?"),
            ],
            "ordering": [
                ("Which order is right?", "split → build loaders → train on batches", ["split → build loaders → train on batches", "build loaders → train on batches → split", "train on batches → split → build loaders"],
                 "Each loader serves one of the already-split sets, and training loops over the training loader's batches. Training before splitting would let test images into training.",
                 "What does a DataLoader need before it can be built?"),
            ],
            "transfer": [
                ("A sensor reports values from 0 to 1,000. How would you scale them to 0–1?", "Divide each value by 1,000", ["Divide each value by 1,000", "Divide each value by 16", "Subtract 1,000 from each value"],
                 "Dividing by the largest possible value maps 0–1,000 onto 0–1, the same idea as dividing pixels by 16. The 16 is specific to these images, and subtracting would give negative numbers.",
                 "Why did we divide pixels by that particular number?"),
            ],
        },
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
        "result": "This code prints nothing. It creates model, a network with random starting weights. Its structure is now fixed; what each filter looks for is learned in the next stage.",
        "why": "Every layer's size must match the one before it. The 16 * 4 * 4 in nn.Linear(16 * 4 * 4, 10) comes straight from the shape trace: 16 maps of 4 × 4 after pooling. Change the number of filters or the pooling and that number changes too. Get it wrong and PyTorch stops with a shape mismatch error.",
        "code_explanation": [
            "nn.Conv2d(1, 16, kernel_size=3, padding=1) — 1 input channel, 16 filters of 3 × 3. padding=1 adds a border so the maps stay 8 × 8.",
            "nn.ReLU() — keeps positive values and turns negative ones into 0. The shape doesn't change.",
            "nn.MaxPool2d(2) — keeps the largest value in each 2 × 2 block, so each 8 × 8 map becomes 4 × 4.",
            "nn.Flatten() — lines up 16 × 4 × 4 values into one list of 256 numbers.",
            "nn.Linear(16 * 4 * 4, 10) — combines all 256 values into 10 scores, one per digit.",
            "torch.manual_seed(42) — fixes the random starting weights so everyone builds the same model.",
        ],
        "questions": {
            "operation": [
                ("Suppose Conv2d made 32 maps instead of 16. How long is the list Linear receives?", "512", ["512", "2,048", "128"],
                 "Pooling halves height and width, giving 32 × 4 × 4, and Flatten multiplies them out: 32 × 4 × 4 = 512. 2,048 is the count before pooling, and 128 would need only 8 maps.",
                 "Halve the height and width first, then multiply all three."),
                ("Which layer shrinks each 8 × 8 map to 4 × 4?", "nn.MaxPool2d(2)", ["nn.MaxPool2d(2)", "nn.ReLU()", "nn.Flatten()"],
                 "MaxPool2d(2) keeps the largest value in each 2 × 2 block, halving height and width. ReLU doesn't change the shape, and Flatten keeps every value, just in one line.",
                 "Which layer works on 2 × 2 blocks?"),
            ],
            "variable": [
                ("How many feature maps does nn.Conv2d(1, 16, kernel_size=3) make per image?", "16", ["16", "3", "1"],
                 "The second argument is the number of filters, and each filter makes its own map. The 3 is the filter size and the 1 is the number of input channels.",
                 "Read the arguments in order: input channels, output channels, filter size."),
                ("Just after nn.Sequential(...) runs, what are the filter weights?", "Random starting values", ["Random starting values", "Patterns learned from the digits", "All exactly zero"],
                 "Building the model only creates the layers. Weights start random (made repeatable by the seed) and only become useful patterns during training. All zeros would make every filter identical.",
                 "Has the model seen any images yet?"),
            ],
            "boundary": [
                ("Conv2d is changed to 32 filters, but nn.Linear(16 * 4 * 4, 10) is left alone. What happens?", "PyTorch raises a shape mismatch error", ["PyTorch raises a shape mismatch error", "The extra filters are quietly ignored", "Accuracy improves automatically"],
                 "Flatten now produces 32 × 4 × 4 = 512 values, but Linear expects 256, so PyTorch stops with a shape error. The fix is nn.Linear(32 * 4 * 4, 10).",
                 "How many values does Flatten produce now?"),
                ("What does ReLU do to a value of −0.4?", "Turns it into 0", ["Turns it into 0", "Turns it into 0.4", "Leaves it as −0.4"],
                 "ReLU keeps positive values and replaces negative ones with 0. It doesn't flip the sign, which would give 0.4, and it doesn't let negatives through.",
                 "ReLU keeps only the positive part."),
                ("What does padding=1 do in this Conv2d?", "It keeps each map at 8 × 8", ["It keeps each map at 8 × 8", "It adds a 17th filter", "It scales pixels to 0–1"],
                 "Without padding, a 3 × 3 filter can't centre on the edge pixels, so each map would shrink to 6 × 6. padding=1 adds a border of zeros so the maps stay 8 × 8, which is why later layers expect 16 × 4 × 4.",
                 "What happens at the edges when a 3 × 3 window slides across?"),
            ],
            "ordering": [
                ("Which order matches this model?", "Conv2d → ReLU → MaxPool2d → Flatten → Linear", ["Conv2d → ReLU → MaxPool2d → Flatten → Linear", "Flatten → Conv2d → MaxPool2d → ReLU → Linear", "Linear → Conv2d → ReLU → MaxPool2d → Flatten"],
                 "Filters need the image as a grid, so convolution comes first, and Flatten comes just before Linear, which needs one long list. Flattening first would throw away the grid the filters rely on.",
                 "Which layers need the image to still be a grid?"),
            ],
            "transfer": [
                ("This CNN is changed to read the letters A to Z. What must change?", "The last layer outputs 26 scores", ["The last layer outputs 26 scores", "The filters become 26 × 26", "The images need 26 channels"],
                 "The last layer has one score per class, so 26 letters need nn.Linear(256, 26). Filter size and channels describe the images, not how many answers there are.",
                 "Which layer has one output per possible answer?"),
            ],
        },
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
        "questions": {
            "operation": [
                ("Which call works out how each weight should change?", "loss.backward()", ["loss.backward()", "optimizer.zero_grad()", "model.eval()"],
                 "backward() computes a gradient for every weight: which way to nudge it. zero_grad() clears the previous gradients, and eval() switches the model to prediction mode.",
                 "It runs backwards from the loss through the network."),
                ("The training set has 4,496 images and batch_size=128. How many updates happen in one epoch?", "36", ["36", "35", "4,496"],
                 "There are 35 full batches plus one more with the 16 left over, and the update runs once per batch: 36 updates. Updates happen per batch, not per image.",
                 "Count the last, smaller batch too."),
            ],
            "variable": [
                ("What does labels_batch provide during training?", "The correct digit for each image in the batch", ["The correct digit for each image in the batch", "The model's predicted digits", "The 10 scores for each image"],
                 "The loss compares the model's scores with these correct digits. Predictions and scores come from the model; labels_batch is the answer key for this batch.",
                 "The loss needs something to compare the model's scores with."),
                ("One batch has a loss of 0.3 and a later one 0.2. What does that suggest?", "The model's scores are getting closer to correct", ["The model's scores are getting closer to correct", "The model got 20% of the batch right", "Training has finished"],
                 "A lower loss means the scores lean more towards the correct digits. Loss isn't a percentage, and training continues until the loop ends. Losses also bounce between batches, so look at the overall trend.",
                 "Is a lower loss better or worse?"),
            ],
            "boundary": [
                ("What happens if optimizer.zero_grad() is left out?", "Old adjustments pile up and training goes wrong", ["Old adjustments pile up and training goes wrong", "Nothing, because the update resets them", "PyTorch raises an error"],
                 "PyTorch adds new gradients to the old ones by default. Without zero_grad(), each update uses a growing sum of past batches, so the steps grow too big and point the wrong way. No error is raised.",
                 "Does PyTorch replace old gradients, or add to them?"),
                ("Why must test images never go through this training loop?", "They'd make the test score too optimistic", ["They'd make the test score too optimistic", "They are the wrong shape", "The loop only accepts 128 images"],
                 "Images that changed the weights aren't unseen any more, so the final test would partly measure memory. They're the same shape as training images, so PyTorch wouldn't stop you.",
                 "What is the test set meant to measure?"),
                ("Before any training, how often would the model pick the right digit?", "About 1 time in 10", ["About 1 time in 10", "About half the time", "Never"],
                 "With random weights the scores are close to random, and there are ten roughly equal-sized digit classes, so it's right about 10% of the time by luck. That's the baseline training has to beat.",
                 "How many digits are there to choose from?"),
            ],
            "ordering": [
                ("Which order completes one training step?", "zero_grad → loss → backward → step", ["zero_grad → loss → backward → step", "step → backward → loss → zero_grad", "loss → step → backward → zero_grad"],
                 "Clear the old gradients, measure how wrong this batch was, work out the adjustments, then apply them. Applying before working them out would use stale or empty adjustments.",
                 "You can't apply an adjustment before working it out."),
            ],
            "transfer": [
                ("The loop is changed to run for 3 epochs instead of 1. What changes?", "It sees every training image three times", ["It sees every training image three times", "It uses three times as many test images", "Each batch holds three times as many images"],
                 "An epoch is one pass over the training set, so 3 epochs means 3 passes and 3 × 36 = 108 updates. The test set and the batch size stay the same.",
                 "What is one epoch?"),
            ],
        },
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
        "questions": {
            "operation": [
                ("An image's 10 scores peak at 2.8, the second entry in the list. Which digit is predicted?", "1", ["1", "2", "2.8"],
                 "Positions count from 0, so the second entry is position 1, and argmax returns that position: digit 1. Answering 2 counts from 1 instead of 0, and 2.8 is the score, not the digit.",
                 "Positions start at 0."),
                ("Which call turns 10 scores per image into one predicted digit per image?", ".argmax(dim=1)", [".argmax(dim=1)", "torch.cat(...)", "model.eval()"],
                 "argmax picks each image's highest-scoring position. torch.cat joins the batch results together, and eval() switches the model's mode.",
                 "You want the position of the largest score."),
            ],
            "variable": [
                ("What does y_pred hold after this code runs?", "One predicted digit for each test image", ["One predicted digit for each test image", "10 scores for each test image", "The correct digit for each test image"],
                 "argmax reduced each image's 10 scores to a single digit, and torch.cat joined them into 1,124 predictions. The correct digits are in y_test.",
                 "What did argmax do to each image's 10 scores?"),
                ("What is y_test for in this stage?", "Kept to compare with y_pred later", ["Kept to compare with y_pred later", "An input to the model", "Used to update the weights"],
                 "The model only receives images. The true labels are collected alongside so the next stage can count how many predictions match. They never go into the model or change it.",
                 "Does the model need the answer to make a prediction?"),
            ],
            "boundary": [
                ("What would go wrong if prediction skipped the / 16.0?", "Inputs would be 16× too large; predictions worsen", ["Inputs would be 16× too large; predictions worsen", "PyTorch would raise a shape error", "Nothing; the model rescales inputs itself"],
                 "The model learned on values between 0 and 1. Raw pixels up to 16 throw its scores off, so many predictions go wrong. The shape is unchanged, so there's no error, and the model never rescales anything by itself.",
                 "Does dividing by 16 change the input's shape?"),
                ("Does running the test images through the model change its weights?", "No, prediction only runs forward", ["No, prediction only runs forward", "Yes, a little for each batch", "Yes, but only in eval mode"],
                 "There's no loss.backward() or optimizer.step() here, and torch.no_grad() turns off gradient tracking as well. The weights stay exactly as training left them.",
                 "Which calls changed the weights during training? Are they here?"),
                ("argmax returns 7 for an image of a 1. What does that tell you?", "The model scored 7 highest; this one is wrong", ["The model scored 7 highest; this one is wrong", "The image's label must be wrong", "argmax found the seventh-highest score"],
                 "argmax only reports which digit the model scored highest. Here that's 7, so this prediction is a mistake; 1s and 7s can look alike at 8 × 8. Nothing suggests the label is wrong, and argmax always finds the single highest score.",
                 "argmax reports the model's choice, not the truth."),
            ],
            "ordering": [
                ("Which order produces predictions?", "eval() → no_grad → scores → argmax", ["eval() → no_grad → scores → argmax", "argmax → scores → eval()", "scores → step() → argmax"],
                 "Switch to prediction mode, stop tracking gradients, run the images through to get scores, then pick each top position. step() belongs to training, not prediction.",
                 "Set up for prediction before running the images."),
            ],
            "transfer": [
                ("A weather model scores sunny, cloudy and rainy as [0.4, 1.7, −0.2]. What does it predict?", "cloudy", ["cloudy", "sunny", "rainy"],
                 "argmax picks position 1, the highest score (1.7), and position 1 is cloudy. The same rule works for any number of classes: the position of the highest score is the answer.",
                 "Find the biggest score, then the class in that position."),
            ],
        },
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
        "questions": {
            "operation": [
                ("You mark 20 of the model's predictions and find 2 mistakes. What accuracy is that?", "0.9 (90%)", ["0.9 (90%)", "0.1 (10%)", "2"],
                 "18 of the 20 are right, and 18 ÷ 20 = 0.9, or 90%. 0.1 is the error rate, the fraction wrong, and 2 is just the count of mistakes.",
                 "Accuracy counts the right answers, not the mistakes."),
                ("Accuracy on the 1,124 test images is 0.95. About how many were wrong?", "About 56", ["About 56", "About 5", "About 1,068"],
                 "If 95% were right, 5% were wrong, and 5% of 1,124 is about 56. Roughly 1,068 is how many were right, and 5 mixes up the percentage with a count.",
                 "If 95% are right, what fraction are wrong?"),
            ],
            "variable": [
                ("In (y_pred == y_test).float().mean(), what does .float() do?", "Turns True into 1 and False into 0", ["Turns True into 1 and False into 0", "Rounds each prediction to a decimal", "Converts digits into scores"],
                 "The comparison gives True or False for each image. As numbers, 1 and 0, their average is the fraction correct. Nothing is rounded and no scores are involved.",
                 "You can't average True and False directly."),
                ("What does y_test hold?", "The true digit for each test image", ["The true digit for each test image", "The model's predicted digits", "The training labels"],
                 "y_test is the answer key collected alongside the test images. y_pred holds the predictions, and the training labels were used earlier, never for scoring.",
                 "What do you compare the predictions against?"),
            ],
            "boundary": [
                ("Why must the test images never have updated the weights?", "Otherwise accuracy measures memory, not skill", ["Otherwise accuracy measures memory, not skill", "Otherwise accuracy can't be calculated", "Otherwise the shapes won't match"],
                 "If the model trained on these images, a high score could simply mean it remembers them. Accuracy can still be calculated and the shapes still match, which is why this mistake is easy to miss.",
                 "What is the test score supposed to tell you?"),
                ("A model scores 92% overall but gets only 60% of the 8s right. What does this show?", "One overall number can hide weak classes", ["One overall number can hide weak classes", "The 92% must be a mistake", "8s don't count towards accuracy"],
                 "Overall accuracy averages over every digit, so strong results on most can hide a weak one. Checking accuracy per digit, or which digits get confused, shows where the model struggles.",
                 "Is the 92% the same for every digit?"),
                ("A model scores 11% on this test set. What does that suggest?", "It's barely better than guessing", ["It's barely better than guessing", "It's doing well for ten classes", "Only 11% of the images are digits"],
                 "With ten roughly equal classes, random guessing scores about 10%. 11% means the model has learned almost nothing; perhaps training didn't run, or the / 16 scaling was missed somewhere.",
                 "What would random guessing score with ten digits?"),
            ],
            "ordering": [
                ("Which order completes the digit pipeline?", "train → predict test images → compare → accuracy", ["train → predict test images → compare → accuracy", "accuracy → train → predict test images", "predict test images → accuracy → train"],
                 "You need a trained model to predict, predictions to compare, and comparisons to count. Accuracy before training has nothing to measure.",
                 "What does accuracy need to exist first?"),
            ],
            "transfer": [
                ("Two digit models score 94% and 96%, each on a different test set. Which is better?", "Can't tell; they need the same test images", ["Can't tell; they need the same test images", "The 96% model", "The 94% model"],
                 "One test set might simply be easier than the other. Scores are only comparable on the same held-out images; then the higher accuracy wins.",
                 "Could one test set be easier than the other?"),
            ],
        },
        "review": "Accuracy is correct ÷ total on images the model never trained on. Compare it with chance (10%) and check which digits it confuses.",
    },
}


# Each pool holds (prompt, correct, options, explanation, hint); see the sentiment pilot stage.
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
        "questions": {
            "operation": [
                ("Which line creates the prices the model learns to predict?", 'y = df["price"]', ['y = df["price"]', "X = df[feature_columns]", "df.head()"],
                 "y holds the target: one sale price per house. X holds the four features, and head() only displays rows.",
                 "The target is the value the model must learn to give."),
                ("The file had 2,930 rows and dropna() removed none. How many rows does X have?", "2,930", ["2,930", "4", "2,926"],
                 "With no rows dropped, every house stays, so X has 2,930 rows. 4 is the number of feature columns, not rows, and nothing was removed to make 2,926.",
                 "Rows are houses; columns are features."),
            ],
            "variable": [
                ("What does one row of X describe?", "One house's four details", ["One house's four details", "One house's sale price", "The average of all houses"],
                 "Each row of X is a single house: bedrooms, bathrooms, square feet and age. Its price sits in the matching position of y, and nothing is averaged here.",
                 "X holds features, not the price."),
                ("Why is regression the right name for this task?", "The answer is a number, not a category", ["The answer is a number, not a category", "The data comes from a CSV file", "There are exactly four features"],
                 "Regression predicts a numeric value such as a price. Predicting a category, like positive or negative, is classification. The file format and the number of features don't decide it.",
                 "What kind of answer does the model give?"),
            ],
            "boundary": [
                ("A teammate adds price to feature_columns. What goes wrong?", "The model copies the answer, useless for new houses", ["The model copies the answer, useless for new houses", "Nothing; more features always help", "pandas raises an error"],
                 "With the price as an input, the model learns to read it straight back and looks perfect in testing. A new house has no price yet, so there's nothing to copy. pandas won't stop you.",
                 "When you price a new house, is its sale price known?"),
                ("dropna() removed 0 rows from this file. Why keep the line?", "It guards against incomplete rows in other data", ["It guards against incomplete rows in other data", "It speeds up training", "It removes duplicate houses"],
                 "This file happens to be complete, but the same code on new data could meet missing values. dropna() makes sure every row has all four features and a price. It doesn't remove duplicates or change speed.",
                 "Will every future file be this clean?"),
                ("Which statement about X and y is correct?", "Row i of X matches price i of y", ["Row i of X matches price i of y", "X and y can be sorted separately", "y has four columns"],
                 "X and y are paired by position. Sorting one without the other would give houses the wrong prices, with no error. y is a single column of prices.",
                 "How does the model know which price belongs to which house?"),
            ],
            "ordering": [
                ("Which order prepares the data?", "load → drop incomplete rows → pick X and y", ["load → drop incomplete rows → pick X and y", "pick X and y → load → drop incomplete rows", "drop incomplete rows → pick X and y → load"],
                 "You need the data before you can clean it, and X and y should come from the cleaned rows so they stay the same length and paired.",
                 "Should X and y include rows you're about to drop?"),
            ],
            "transfer": [
                ("A model predicts tomorrow's temperature from today's weather. Which is the target?", "Tomorrow's temperature", ["Tomorrow's temperature", "Today's humidity", "Today's wind speed"],
                 "The target is the number you want to predict, like price here. Today's readings are the features, like bedrooms and size.",
                 "Which value plays the role of the price?"),
            ],
        },
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
        "result": "This code prints nothing. It creates X_train, X_test, y_train and y_test: 2,344 training houses and 586 test houses.",
        "why": "Split X and y in one call. Splitting them separately, or shuffling one of them, would give most houses someone else's price. Nothing would crash, but the model would learn from nonsense and its error would mean nothing.",
        "code_explanation": [
            "train_test_split(X, y, ...) — shuffles the houses once and splits features and prices together.",
            "test_size=0.2 — keeps 20% of the houses, 586 of them, aside for testing.",
            "random_state=42 — makes the shuffle the same every run, so results can be reproduced.",
            "X_train, X_test, y_train, y_test — the four results, always in this order.",
        ],
        "questions": {
            "operation": [
                ("With 2,930 houses and test_size=0.2, how many go into the test set?", "586", ["586", "2,344", "20"],
                 "20% of 2,930 is 586. 2,344 is the training set, the other 80%, and 20 is the percentage, not a count.",
                 "Take one fifth of the total."),
                ("test_size is changed to 0.3. About how many training houses are left?", "About 2,051", ["About 2,051", "About 879", "About 2,344"],
                 "30% of 2,930 is 879 test houses, leaving 2,051 to train on. 2,344 was the training size with the original 20% split.",
                 "The training set is whatever isn't held out."),
            ],
            "variable": [
                ("What does y_test hold?", "The real prices of the 586 test houses", ["The real prices of the 586 test houses", "The model's predicted prices", "The features of the test houses"],
                 "y_test is the answer key for the test houses. Predictions come later, in y_pred, and the test houses' features are in X_test.",
                 "y always holds prices."),
                ("What does random_state=42 do?", "Makes the same split every time", ["Makes the same split every time", "Puts 42 houses in the test set", "Sets the price of the first house"],
                 "It fixes the random shuffle so every run, for everyone, picks the same training and test houses. It isn't a count of houses.",
                 "It's about the randomness, not a quantity."),
            ],
            "boundary": [
                ("Why check the model on houses it didn't train on?", "To see how it prices houses it hasn't seen", ["To see how it prices houses it hasn't seen", "To make training faster", "Because test houses are more expensive"],
                 "A model can do well on houses it learned from just by fitting them closely. Unseen houses show how it will do on real new listings. The split doesn't change speed, and test houses are picked at random.",
                 "What will the model face once it's used for real?"),
                ("Which test set is fair?", "A random 20% of houses, chosen before training", ["A random 20% of houses, chosen before training", "The 586 houses the model prices best", "The 586 cheapest houses"],
                 "The test set must be chosen at random and before training, so it looks like the houses the model will meet. Picking the ones it already prices well flatters it, and picking only cheap houses tests one kind of home.",
                 "Should the test set depend on the model's results?"),
                ("Error is low on the training houses but high on the test houses. What does that suggest?", "It fits its training houses too closely", ["It fits its training houses too closely", "The test prices are wrong", "The split should be undone"],
                 "A gap like this means the model learned details of its own training houses that don't carry over to new ones. The test set is doing its job by revealing that.",
                 "Which number tells you about new houses?"),
            ],
            "ordering": [
                ("Where does the split belong?", "After picking X and y, before scaling and training", ["After picking X and y, before scaling and training", "After training, before predicting", "After calculating the error"],
                 "You need X and y to split, and every later step, scaling included, should learn only from the training part. Splitting after training would let test houses into training.",
                 "Which later steps must not see the test houses?"),
            ],
            "transfer": [
                ("You're predicting rents for 1,000 flats with test_size=0.2. How many are tested?", "200", ["200", "800", "20"],
                 "20% of 1,000 is 200 test flats, and the other 800 train the model. It's the same rule as with houses.",
                 "Take one fifth."),
            ],
        },
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
        "result": "This code prints nothing. X_train_scaled and X_test_scaled hold the same houses as before, with every feature now measured in spreads from the training average. The price, y, isn't scaled.",
        "why": "Fit the scaler on the training houses only, then transform the test houses with it. Fitting on the test houses too would let their averages shape the preprocessing, so the test isn't fully unseen any more. Nothing breaks, which is why this leak is so easy to miss.",
        "code_explanation": [
            "StandardScaler() — creates a scaler that hasn't learned anything yet.",
            "scaler.fit_transform(X_train) — learns each feature's average and spread from the training houses, then scales them.",
            "scaler.transform(X_test) — scales the test houses with the training averages and spreads. Nothing new is learned.",
            "X_train_scaled, X_test_scaled — the scaled features, each value now in spreads from the training average.",
        ],
        "questions": {
            "operation": [
                ("Training houses average 36 years old, with a spread of 30. A house is 66. Its scaled age is about:", "+1", ["+1", "−1", "66"],
                 "(66 − 36) ÷ 30 = 1: one spread older than average. A negative value would mean younger than average, and 66 is the age before scaling.",
                 "Subtract the average, then divide by the spread."),
                ("Which call learns the averages and spreads?", "scaler.fit_transform(X_train)", ["scaler.fit_transform(X_train)", "scaler.transform(X_test)", "StandardScaler()"],
                 "fit_transform learns from the training houses and scales them in one go. transform only applies what was already learned, and StandardScaler() just creates an empty scaler.",
                 "Learning is the 'fit' part."),
            ],
            "variable": [
                ("A house's scaled bedrooms value is 0. What does that mean?", "It has about the average number of bedrooms", ["It has about the average number of bedrooms", "It has no bedrooms", "The value was missing"],
                 "After scaling, 0 means exactly the training average. A house with no bedrooms at all would get a large negative scaled value, and incomplete rows were dropped earlier.",
                 "What does 0 mean once values are scaled?"),
                ("Is the price, y, scaled in this stage?", "No, only the four features are", ["No, only the four features are", "Yes, along with the features", "Only the test prices are"],
                 "The scaler is fitted on X_train and applied to X_test. y_train and y_test stay in dollars, which is why the predictions later come out in dollars.",
                 "Which variables are passed to the scaler?"),
            ],
            "boundary": [
                ("Why not call fit_transform on the test houses as well?", "Test houses would shape the scaling, leaking information", ["Test houses would shape the scaling, leaking information", "fit_transform only works on training data", "It would make the test set larger"],
                 "Fitting on the test houses lets their averages influence preprocessing, so the evaluation isn't fully unseen. fit_transform works on any data, which is why the leak is easy to make, and it doesn't change the set's size.",
                 "Which houses should the scaler learn from?"),
                ("Why scale the features at all?", "So features with big numbers don't dominate", ["So features with big numbers don't dominate", "So the prices become smaller", "So the file loads faster"],
                 "Square feet are in the thousands while bedrooms are under 10. Scaling puts them on equal footing, which also makes the coefficients easier to compare. Prices aren't scaled, and loading isn't affected.",
                 "Compare the ranges of square feet and bedrooms."),
                ("After scaling, which statement is true?", "Each row still describes the same house", ["Each row still describes the same house", "Bigger houses now have smaller numbers", "Every house now has the same values"],
                 "Scaling changes the units, not the order: a bigger house still has a bigger scaled size. Houses keep their differences; they're just measured in spreads instead of square feet.",
                 "Does scaling change which house is bigger?"),
            ],
            "ordering": [
                ("Which order avoids leaking test information?", "split → fit scaler on train → transform test", ["split → fit scaler on train → transform test", "fit scaler on all houses → split → train", "transform test → split → fit scaler on train"],
                 "Split first so the scaler learns from training houses only, then reuse it on the test houses. Fitting on all houses before splitting lets the test houses shape the scaling.",
                 "When does the scaler first see any data?"),
            ],
            "transfer": [
                ("A fitness model uses steps per day (thousands) and hours of sleep (under 12). What helps?", "Scale both using training averages and spreads", ["Scale both using training averages and spreads", "Remove the steps feature", "Multiply sleep by 1,000"],
                 "It's the square feet versus bedrooms problem again: very different ranges. Standardizing with training statistics puts both on one scale; deleting a feature throws information away, and multiplying by hand only guesses the scale.",
                 "This is the square feet versus bedrooms problem."),
            ],
        },
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
        "result": "This code prints nothing. model now holds an intercept and four coefficients. The Try it step prints the coefficients so you can read them.",
        "why": "The coefficients are per spread, not per original unit, because the features were scaled. A square_feet coefficient of 40,000 means about $40,000 for each extra ~505 sq ft, not $40,000 per square foot. Also remember that creating LinearRegression() learns nothing; only fit does.",
        "code_explanation": [
            "LinearRegression() — creates an untrained model with no intercept or coefficients yet.",
            "model.fit(X_train_scaled, y_train) — finds the intercept and coefficients that best match the training prices.",
            "model.coef_ — after fitting, four numbers: one per feature, in the order of feature_columns.",
            "model.intercept_ — after fitting, the predicted price of a house that is average on every feature.",
        ],
        "questions": {
            "operation": [
                ("Intercept $180,000; square_feet coefficient $40,000. An otherwise average house is one spread larger. Predicted price?", "$220,000", ["$220,000", "$180,000", "$40,000"],
                 "Start at the intercept, $180,000, and add the size coefficient once for one spread of extra size: $220,000. The other features are average, so their scaled values are 0 and add nothing.",
                 "Average features scale to 0, so they add nothing."),
                ("Which line does the learning?", "model.fit(X_train_scaled, y_train)", ["model.fit(X_train_scaled, y_train)", "model = LinearRegression()", "scaler.transform(X_test)"],
                 "fit is where the intercept and coefficients are calculated from the training houses. Creating the model only sets it up, and transform scales features.",
                 "Which call sees both the houses and their prices?"),
            ],
            "variable": [
                ("What does y_train provide during fit?", "The real prices the model tries to match", ["The real prices the model tries to match", "The scaled features", "The predicted prices"],
                 "fit compares the formula's output with these real prices and adjusts the coefficients to get close. Features come from X_train_scaled, and predictions don't exist yet.",
                 "fit needs the right answers to learn from."),
                ("What does a negative age_years coefficient mean?", "Older houses are predicted to cost less", ["Older houses are predicted to cost less", "Some houses have a negative age", "The model failed to train"],
                 "A negative coefficient lowers the prediction as that feature increases, with the others held fixed. Ages are never negative, and negative coefficients are perfectly normal.",
                 "What happens to the predicted price as age goes up?"),
            ],
            "boundary": [
                ("What does a square_feet coefficient of 40,000 mean?", "About $40,000 more per ~505 extra sq ft", ["About $40,000 more per ~505 extra sq ft", "$40,000 more per extra square foot", "Every house costs $40,000"],
                 "The features were scaled, so coefficients are per spread, about 505 sq ft here, not per square foot. $40,000 per square foot would price even a small house in the tens of millions.",
                 "Remember the features were scaled."),
                ("You call model.predict before model.fit. What happens?", "An error: nothing has been learned yet", ["An error: nothing has been learned yet", "It predicts the average price", "It predicts $0 for every house"],
                 "scikit-learn raises a NotFittedError because there are no coefficients yet. It doesn't fall back to an average or to zero.",
                 "What do the coefficients hold before fit runs?"),
                ("Which houses should fit see?", "Only the 2,344 training houses", ["Only the 2,344 training houses", "All 2,930 houses", "Only the 586 test houses"],
                 "The test houses must stay unseen so the error in the last stage is honest. Fitting on every house would let the model tune itself to the test prices.",
                 "Which houses are kept for checking?"),
            ],
            "ordering": [
                ("Which order trains the model correctly?", "scale features → create model → fit on training data", ["scale features → create model → fit on training data", "fit on training data → create model → scale features", "create model → fit on test data → scale features"],
                 "fit needs scaled features and an existing model. Scaling afterwards would mean the model learned on different numbers from the ones it will be given.",
                 "fit needs both the model and the scaled features."),
            ],
            "transfer": [
                ("A linear model predicts energy use from temperature. The temperature coefficient is negative. Meaning?", "Warmer days are predicted to use less energy", ["Warmer days are predicted to use less energy", "Temperature isn't used", "Energy use is negative"],
                 "Read it like a negative age coefficient: as temperature rises, predicted energy use falls, with other features fixed.",
                 "Read it like the age coefficient."),
            ],
        },
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
        "questions": {
            "operation": [
                ("A house sold for $150,000 and the model predicted $162,000. What is the error?", "+$12,000: it guessed high", ["+$12,000: it guessed high", "−$12,000: it guessed high", "$312,000"],
                 "Error is predicted minus actual: 162,000 − 150,000 = +12,000, a guess that's too high. A negative error would mean too low, and adding the two prices means nothing.",
                 "Subtract the real price from the prediction."),
                ("How many predictions does y_pred hold?", "586", ["586", "10", "2,344"],
                 "predict ran on all 586 test houses. The loop prints only 10 of them, and 2,344 is the size of the training set.",
                 "Which houses were passed to predict?"),
            ],
            "variable": [
                ("What does model.predict receive here?", "Scaled features of the test houses", ["Scaled features of the test houses", "The real test prices", "Unscaled features of the test houses"],
                 "The model learned on scaled features, so it needs X_test_scaled. The real prices are only for checking, and unscaled features would be in the wrong units.",
                 "Use the same kind of input the model trained on."),
                ("Changing [:10] to [:3] in the print loop does what?", "Shows 3 pairs; all 586 predictions still exist", ["Shows 3 pairs; all 586 predictions still exist", "Predicts only 3 houses", "Retrains the model on 3 houses"],
                 "The slice only limits what's printed. y_pred was already computed for every test house before the loop ran.",
                 "Is the slice applied to predict, or to the printout?"),
            ],
            "boundary": [
                ("What happens if you pass X_test instead of X_test_scaled?", "Prices come out badly wrong, with no error", ["Prices come out badly wrong, with no error", "scikit-learn raises an error", "Nothing; the model scales them itself"],
                 "Unscaled square feet are in the thousands, but the model expects values near 0, so its predictions are wildly off. There are still 4 columns, so nothing crashes, and the model never rescales inputs itself.",
                 "Does the model know the inputs weren't scaled?"),
                ("Does predict change the coefficients?", "No, it only applies them", ["No, it only applies them", "Yes, it refines them on each house", "Yes, if the error is large"],
                 "Learning happens only in fit. predict reads the coefficients and computes prices; you could call it a thousand times and the model wouldn't change.",
                 "Which method set the coefficients?"),
                ("The model predicts $210,000 for a house that sold for $205,000. Is it broken?", "No; small errors are normal", ["No; small errors are normal", "Yes; it should match exactly", "Yes; it ignored the price"],
                 "Four details can't capture everything about a house's price, so predictions are rarely exact. A $5,000 miss on a $205,000 house is small. The next stage measures how big the errors are on average.",
                 "Can four details fully explain a sale price?"),
            ],
            "ordering": [
                ("Which order prices a brand-new house?", "scale with the training scaler → predict", ["scale with the training scaler → predict", "predict → scale with the training scaler", "fit a scaler on the house → predict"],
                 "The new house's features must be converted with the same scaler as the training houses, then passed to predict. Fitting a scaler on a single house would give meaningless averages.",
                 "The model only understands scaled features."),
            ],
            "transfer": [
                ("A delivery-time model predicts 34 minutes; the delivery took 30. What's the error?", "+4 minutes", ["+4 minutes", "−4 minutes", "64 minutes"],
                 "Predicted minus actual: 34 − 30 = +4, a guess 4 minutes too long. It's the same rule as with prices.",
                 "Subtract the real value from the prediction."),
            ],
        },
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
        "questions": {
            "operation": [
                ("Errors on three test houses: +$4,000, −$8,000, +$6,000. Find the mean absolute error.", "$6,000", ["$6,000", "$667", "$18,000"],
                 "Drop the signs: 4,000 + 8,000 + 6,000 = 18,000, then divide by 3 to get $6,000. $667 comes from letting the negative error cancel, and $18,000 forgot to divide.",
                 "Make every error positive before averaging."),
                ("One house is off by $30,000 and three are exactly right. What is the MAE?", "$7,500", ["$7,500", "$30,000", "$0"],
                 "(30,000 + 0 + 0 + 0) ÷ 4 = 7,500. One big miss is spread across all four houses, which is why an average can hide large individual errors.",
                 "Average over all four houses."),
            ],
            "variable": [
                ("What does y_test provide here?", "The real prices to measure errors against", ["The real prices to measure errors against", "The model's predictions", "The training prices"],
                 "MAE compares the predictions in y_pred with the true prices of the same houses in y_test. Training prices aren't used for evaluation.",
                 "Errors are measured against what?"),
                ("What units is MAE reported in?", "Dollars, like the prices", ["Dollars, like the prices", "A percentage", "Square feet"],
                 "Absolute errors are differences between prices, so their average is in dollars too. That's what makes MAE easy to explain.",
                 "What is the difference between two prices measured in?"),
            ],
            "boundary": [
                ("Why drop the sign of each error?", "So over- and under-estimates don't cancel out", ["So over- and under-estimates don't cancel out", "Because prices can't be negative", "To make the MAE larger"],
                 "Errors of +$20,000 and −$20,000 would average to $0 and hide two big misses. Taking absolute values counts both as $20,000. It has nothing to do with prices being positive.",
                 "What's the average of +20,000 and −20,000?"),
                ("A model has a low MAE on its training houses. Is that good evidence?", "No; only test-house MAE shows performance on new houses", ["No; only test-house MAE shows performance on new houses", "Yes, a low MAE is always good", "Yes, if the training set is large"],
                 "The model has already seen the training houses, so its error there is flattering. The test houses were kept aside precisely to measure how it does on new ones.",
                 "Which houses did the model learn from?"),
                ("Model P has MAE $11,000 on one test set; Q has $9,000 on another. Which is better?", "Can't tell without the same test houses", ["Can't tell without the same test houses", "Q, because its MAE is lower", "P, because its MAE is higher"],
                 "One test set might contain easier houses to price. MAE values are only comparable when both models are tested on the same houses; then the lower one is better.",
                 "Could one set of test houses be easier to price?"),
            ],
            "ordering": [
                ("Which order completes the regression pipeline?", "fit → predict test houses → MAE", ["fit → predict test houses → MAE", "MAE → fit → predict test houses", "predict test houses → fit → MAE"],
                 "You need a fitted model to predict, and predictions to measure. MAE before any predictions has nothing to compare.",
                 "What does MAE need to exist first?"),
            ],
            "transfer": [
                ("A weather model's MAE for daily high temperature is 2°C. What does that mean?", "Forecasts miss by about 2°C on average", ["Forecasts miss by about 2°C on average", "Every forecast is 2°C too high", "2% of forecasts are wrong"],
                 "MAE is the average size of the error, in the units of what's predicted: degrees here. Some days miss by more and some by less, and it says nothing about direction.",
                 "MAE is in the same units as what's predicted."),
            ],
        },
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
    "comparison_selection": "variable", "error_identification": "variable",
    "analogy_mapping": "transfer", "novel_transfer": "transfer",
    "pipeline_ordering": "ordering",
}
# The boundary pool serves all three steps, so each step starts on a different variant.
STEP_VARIANT_OFFSET = {"connect": 0, "practice": 1, "review": 2}


def _question(request: TutorGenerationRequest, data: dict[str, object], variant: int) -> TutorContent:
    action = request.action_type.value.rsplit(".", 1)[-1]
    pool = data["questions"][ACTION_POOLS.get(action, "operation")]  # type: ignore[index]
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
