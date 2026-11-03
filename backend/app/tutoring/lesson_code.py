"""Versioned, canonical code shown in generated LEAP lessons."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FixedLessonCode:
    version: str
    language: str
    code: str


CODE_VERSION = "real_datasets_pytorch_v3"
EXPERIMENT_VERSION = "fixed_stage_experiments_v2"


@dataclass(frozen=True)
class FixedCodeExperiment:
    title: str
    find: str
    replace: str
    prediction: str  # asked before the learner runs the edit
    expected_change: str  # revealed after they run it


def _python(code: str) -> FixedLessonCode:
    return FixedLessonCode(CODE_VERSION, "python", code.strip())


FIXED_LESSON_CODE: dict[str, dict[str, FixedLessonCode]] = {
    "sentiment_classification": {
        "data_loading_and_preparation": _python('''
import pandas as pd

df = pd.read_csv("reviews.csv")
print(df.head())
print("Rows:", len(df))
'''),
        "train_test_split": _python('''
from sklearn.model_selection import train_test_split

X_train, X_test, y_train, y_test = train_test_split(
    df["review"],
    df["sentiment"],
    test_size=0.2,
    random_state=42,
    stratify=df["sentiment"],
)
print("Training reviews:", len(X_train), "Test reviews:", len(X_test))
print("Test labels:", y_test.value_counts().to_dict())
'''),
        "tfidf_vectorization": _python('''
from sklearn.feature_extraction.text import TfidfVectorizer

vectorizer = TfidfVectorizer()
X_train_tfidf = vectorizer.fit_transform(X_train)
X_test_tfidf = vectorizer.transform(X_test)
print("Training matrix:", X_train_tfidf.shape, "Test matrix:", X_test_tfidf.shape)

words = vectorizer.get_feature_names_out()
example = vectorizer.transform(["The mic is great."]).toarray()[0]
print({str(word): round(float(example[i]), 2) for i, word in enumerate(words) if example[i] > 0})
'''),
        "model_training": _python('''
from sklearn.linear_model import LogisticRegression

model = LogisticRegression(max_iter=1000, random_state=42)
model.fit(X_train_tfidf, y_train)

words = vectorizer.get_feature_names_out()
order = model.coef_[0].argsort()
print("Most negative words:", [str(words[i]) for i in order[:5]])
print("Most positive words:", [str(words[i]) for i in order[-5:][::-1]])
'''),
        "prediction": _python('''
y_pred = model.predict(X_test_tfidf)

for review, prediction in list(zip(X_test, y_pred))[:10]:
    print(f"{prediction}: {review}")
'''),
        "evaluation": _python('''
from sklearn.metrics import accuracy_score, classification_report

accuracy = accuracy_score(y_test, y_pred)
print("Accuracy:", accuracy)
print(classification_report(y_test, y_pred, zero_division=0))
'''),
    },
    "regression": {
        "prepare_housing_data": _python('''
import pandas as pd

df = pd.read_csv("houses.csv").dropna()
feature_columns = ["bedrooms", "bathrooms", "square_feet", "age_years"]
X = df[feature_columns]
y = df["price"]
df.head()
'''),
        "split_housing_data": _python('''
from sklearn.model_selection import train_test_split

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)
print("Training houses:", len(X_train), "Test houses:", len(X_test))
'''),
        "scale_features": _python('''
from sklearn.preprocessing import StandardScaler

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

print("First training house:", X_train.iloc[0].to_dict())
print("After scaling:", X_train_scaled[0].round(2).tolist())
'''),
        "train_regression": _python('''
from sklearn.linear_model import LinearRegression

model = LinearRegression()
model.fit(X_train_scaled, y_train)

for feature, coefficient in zip(feature_columns, model.coef_):
    print(feature, round(coefficient))
print("intercept", round(model.intercept_))
'''),
        "predict_prices": _python('''
y_pred = model.predict(X_test_scaled)

for actual, predicted in list(zip(y_test, y_pred))[:10]:
    print(f"actual=${actual:,.0f}, predicted=${predicted:,.0f}")
'''),
        "evaluate_regression": _python('''
from sklearn.metrics import mean_absolute_error

mae = mean_absolute_error(y_test, y_pred)
print(f"Mean absolute error: ${mae:,.0f}")
'''),
    },
    "cnn": {
        "load_images": _python('''
import pandas as pd
import numpy as np
import torch
from torch.utils.data import TensorDataset

df = pd.read_csv("images.csv")
pixel_columns = [f"pixel_{index}" for index in range(64)]
images = df[pixel_columns].to_numpy(dtype="float32", copy=True).reshape(-1, 1, 8, 8)
labels = df["label"].to_numpy(dtype="int64")
dataset = TensorDataset(torch.from_numpy(images), torch.from_numpy(labels))
print("Images:", images.shape, "Classes:", len(np.unique(labels)))
'''),
        "normalize_split": _python('''
from torch.utils.data import DataLoader, random_split

generator = torch.Generator().manual_seed(42)
train_size = int(0.8 * len(dataset))
test_size = len(dataset) - train_size
train_dataset, test_dataset = random_split(
    dataset, [train_size, test_size], generator=generator
)
train_loader = DataLoader(train_dataset, batch_size=128, shuffle=True, generator=generator)
test_loader = DataLoader(test_dataset, batch_size=256)
print("Training images:", len(train_dataset), "Test images:", len(test_dataset))
print("Training batches:", len(train_loader), "Images per batch:", train_loader.batch_size)
'''),
        "build_cnn": _python('''
from torch import nn

torch.manual_seed(42)
model = nn.Sequential(
    nn.Conv2d(1, 16, kernel_size=3, padding=1),
    nn.ReLU(),
    nn.MaxPool2d(2),
    nn.Flatten(),
    nn.Linear(16 * 4 * 4, 10),
)
print("Scores for one image:", tuple(model(torch.zeros(1, 1, 8, 8)).shape))
print("Learnable numbers:", sum(p.numel() for p in model.parameters()))
'''),
        "train_network": _python('''
loss_fn = nn.CrossEntropyLoss()
optimizer = torch.optim.Adam(model.parameters(), lr=0.01)

model.train()
for images_batch, labels_batch in train_loader:
    optimizer.zero_grad()
    loss = loss_fn(model(images_batch / 16.0), labels_batch)
    loss.backward()
    optimizer.step()
print("Final batch loss:", round(loss.item(), 4))
'''),
        "classify_images": _python('''
model.eval()
prediction_batches = []
label_batches = []
with torch.no_grad():
    for images_batch, labels_batch in test_loader:
        prediction_batches.append(model(images_batch / 16.0).argmax(dim=1))
        label_batches.append(labels_batch)

y_pred = torch.cat(prediction_batches)
y_test = torch.cat(label_batches)
print("First predictions:", y_pred[:10].tolist())
'''),
        "evaluate_cnn": _python('''
accuracy = (y_pred == y_test).float().mean().item()
print("Test accuracy:", round(accuracy, 3))
'''),
    },
}


# Keep each edit beside the canonical curriculum. Tests check every exact match
# and run each experiment independently with the stage's canonical prerequisites.
FIXED_CODE_EXPERIMENTS: dict[str, dict[str, tuple[FixedCodeExperiment, ...]]] = {
    "sentiment_classification": {
        "data_loading_and_preparation": (FixedCodeExperiment(
            'Count reviews per website',
            'print("Rows:", len(df))',
            'print("Rows:", len(df))\nprint(df["source"].value_counts().to_dict())\nprint(df["sentiment"].value_counts().to_dict())',
            'The file has 3,000 reviews from three websites: Amazon, IMDb and Yelp. Predict: does each website supply the same number of reviews, and are there as many positive reviews as negative ones?',
            "Both are perfectly even: 1,000 reviews from each website, and 1,500 positive and 1,500 negative. A balanced dataset means a model can't score well just by favouring one label.",
        ),),
        "train_test_split": (FixedCodeExperiment(
            'Reserve 30% for testing',
            '    test_size=0.2,\n    random_state=42,\n    stratify=df["sentiment"],\n)',
            '    test_size=0.3,\n    random_state=42,\n    stratify=df["sentiment"],\n)',
            'Change test_size from 0.2 to 0.3. Predict: how many reviews end up in training and in testing, and how many of the test reviews are positive?',
            '2,100 training and 900 test reviews, and the test set is still exactly half positive: 450 and 450, because stratify keeps the mix. Holding more back leaves less to learn from.',
        ),),
        "tfidf_vectorization": (FixedCodeExperiment(
            'Limit the vocabulary to 100 words',
            'vectorizer = TfidfVectorizer()',
            'vectorizer = TfidfVectorizer(max_features=100)',
            "Keep only the 100 most common words with max_features=100. Predict: how many columns will the matrices have, and what happens to the rare word 'mic' in the example review?",
            "Both matrices shrink to 100 columns. 'mic' isn't among the 100 most common words, so it drops out, and the remaining words get bigger weights: great 0.76, is 0.52, the 0.38.",
        ),),
        "model_training": (FixedCodeExperiment(
            'Look up the weights of four words',
            'model.fit(X_train_tfidf, y_train)',
            'model.fit(X_train_tfidf, y_train)\nweights = dict(zip(vectorizer.get_feature_names_out(), model.coef_[0]))\nfor word in ["great", "not", "mic", "food"]:\n    print(word, round(float(weights[word]), 2))',
            "Predict the sign of each word's weight: great, not, mic and food. Which will be positive, which negative, and which close to 0?",
            'great is +4.92 and not is −4.6, the strongest each way. mic is 0.0 because it says nothing about sentiment. food is slightly negative (−0.51): it comes up more often in complaints.',
        ),),
        "prediction": (FixedCodeExperiment(
            'Classify reviews you write',
            'y_pred = model.predict(X_test_tfidf)',
            'y_pred = model.predict(X_test_tfidf)\nmy_reviews = ["The battery died after one day.", "Not bad at all, I would buy it again."]\nprint(model.predict(vectorizer.transform(my_reviews)))',
            'Classify two reviews of your own: "The battery died after one day." and "Not bad at all, I would buy it again." Predict the label the model gives each one.',
            "Both come out negative. The first is right. The second is wrong: the model sees 'not' and 'bad', two of its most negative words, and can't tell that together they mean something good. Word weights ignore word order.",
        ),),
        "evaluation": (FixedCodeExperiment(
            'Compare with always guessing positive',
            'print("Accuracy:", accuracy)',
            'print("Accuracy:", accuracy)\nprint("Always guessing positive:", accuracy_score(y_test, ["positive"] * len(y_test)))',
            'Add a lazy baseline that answers "positive" for every review. Predict its accuracy on this test set, and compare it with the model\'s 0.83.',
            "Always guessing positive scores 0.5, because the test set is half positive. The model's 0.83 is well above that, so it has learned something real. Always compare against a baseline like this.",
        ),),
    },
    "regression": {
        "prepare_housing_data": (FixedCodeExperiment(
            'Find the cheapest, typical and priciest house',
            'y = df["price"]',
            'y = df["price"]\nprint("Cheapest:", y.min(), "Median:", y.median(), "Priciest:", y.max())',
            'Print the cheapest, the median and the most expensive sale price. Predict roughly what each one is.',
            'Cheapest $12,789, median $160,000, priciest $755,000. The range is wide: a $30,000 miss is a big error on a $100,000 house but a small one on a $700,000 house. Keep that in mind when you measure errors later.',
        ),),
        "split_housing_data": (FixedCodeExperiment(
            'Reserve 30% of houses for testing',
            '    X, y, test_size=0.2, random_state=42\n)',
            '    X, y, test_size=0.3, random_state=42\n)',
            'Change test_size from 0.2 to 0.3. Predict how many of the 2,930 houses end up in training and in testing.',
            '2,051 training and 879 test houses. Each house keeps its own price, because X and y are split together.',
        ),),
        "scale_features": (FixedCodeExperiment(
            'See what the scaler learned',
            'X_test_scaled = scaler.transform(X_test)',
            'X_test_scaled = scaler.transform(X_test)\nprint("Averages learned:", scaler.mean_.round(0).tolist())\nprint("Scaled training averages:", X_train_scaled.mean(axis=0).round(2).tolist())',
            'Print the averages the scaler learned and the average of every scaled training column. Predict what the scaled averages will be.',
            'The scaler learned averages of about 3 bedrooms, 2 bathrooms, 1,493 sq ft and 37 years. Every scaled training average is 0 (−0.0 is a rounding artefact), because scaling subtracts exactly those averages.',
        ),),
        "train_regression": (FixedCodeExperiment(
            'Price a perfectly average house',
            'model.fit(X_train_scaled, y_train)',
            'model.fit(X_train_scaled, y_train)\nprint("Average house:", round(model.predict([[0, 0, 0, 0]])[0]))',
            'Ask the model to price a house that is exactly average on every feature: all zeros after scaling. Predict the price before you run it.',
            '$178,582, which is the intercept. With every scaled feature at 0, the coefficients add nothing, so the prediction is the average training price.',
        ),),
        "predict_prices": (FixedCodeExperiment(
            'Price a house you describe',
            'y_pred = model.predict(X_test_scaled)',
            'y_pred = model.predict(X_test_scaled)\nmy_house = pd.DataFrame([[3, 2, 2000, 10]], columns=feature_columns)\nprint("My house:", round(model.predict(scaler.transform(my_house))[0]))',
            "Price your own house: 3 bedrooms, 2 bathrooms, 2,000 sq ft, 10 years old. It is scaled with the same scaler first. Predict: above or below the average house's $178,582?",
            'About $248,493, well above average: it is bigger and newer than the typical house, and size and age have the largest coefficients.',
        ),),
        "evaluate_regression": (FixedCodeExperiment(
            'Compare with always guessing the average',
            'print(f"Mean absolute error: ${mae:,.0f}")',
            'print(f"Mean absolute error: ${mae:,.0f}")\nguess = [y_train.mean()] * len(y_test)\nprint(f"Always guessing the average: ${mean_absolute_error(y_test, guess):,.0f}")',
            "Add a baseline that predicts the average training price for every test house. Predict: will its error be larger or smaller than the model's $32,050?",
            "Always guessing the average misses by $64,611 on average, about twice the model's error. The four features cut the error roughly in half.",
        ),),
    },
    "cnn": {
        "load_images": (FixedCodeExperiment(
            'Count the images of each digit',
            'print("Images:", images.shape, "Classes:", len(np.unique(labels)))',
            'print("Images:", images.shape, "Classes:", len(np.unique(labels)))\nprint("Images per digit:", np.bincount(labels).tolist())',
            'Count the images of each digit, 0 to 9. Predict: are some digits much more common than others?',
            'All ten digits appear 554 to 572 times. With classes this balanced, overall accuracy is a fair summary.',
        ),),
        "normalize_split": (FixedCodeExperiment(
            'Use smaller training batches',
            'batch_size=128, shuffle=True',
            'batch_size=32, shuffle=True',
            'Change batch_size from 128 to 32. Predict how many training batches there will be.',
            '141 batches of 32 instead of 36 of 128 (4,496 ÷ 32 = 140.5, rounded up). The split is the same; smaller batches mean more weight updates in each pass.',
        ),),
        "build_cnn": (FixedCodeExperiment(
            'Use 8 filters instead of 16',
            '    nn.Conv2d(1, 16, kernel_size=3, padding=1),\n    nn.ReLU(),\n    nn.MaxPool2d(2),\n    nn.Flatten(),\n    nn.Linear(16 * 4 * 4, 10),',
            '    nn.Conv2d(1, 8, kernel_size=3, padding=1),\n    nn.ReLU(),\n    nn.MaxPool2d(2),\n    nn.Flatten(),\n    nn.Linear(8 * 4 * 4, 10),',
            'Use 8 filters instead of 16. Linear must change too, because 8 maps of 4 × 4 give 128 numbers. Predict the new number of learnable numbers (it was 2,730).',
            '1,370: 80 in the filters (8 × 9 weights + 8 biases) and 1,290 in Linear (128 × 10 + 10). Halving the filters halves both layers, because Linear takes everything the filters produce.',
        ),),
        "train_network": (FixedCodeExperiment(
            'Try a learning rate ten times smaller',
            'lr=0.01',
            'lr=0.001',
            'Make the learning rate ten times smaller: 0.001. Predict: will the final batch loss be higher or lower than 0.37 after one pass?',
            "Much higher: about 2.06, barely below random guessing (2.3). Smaller steps are safer but slower, so one pass isn't enough to learn much. A bigger rate isn't always better either: too big and training becomes unstable.",
        ),),
        "classify_images": (FixedCodeExperiment(
            "Find the model's mistakes",
            'print("First predictions:", y_pred[:10].tolist())',
            'print("First predictions:", y_pred[:10].tolist())\nwrong = (y_pred != y_test).nonzero().flatten()\nprint("Wrong:", len(wrong), "of", len(y_test))\nfor i in wrong[:3].tolist():\n    print("Predicted", y_pred[i].item(), "but it was", y_test[i].item())',
            "List the model's mistakes on the test images. Predict how many of the 1,124 it gets wrong, and which digits it confuses.",
            '89 wrong out of 1,124. The first three: a 7 read as 1, a 3 read as 8 and a 3 read as 1. These digits share strokes, so the mistakes make sense.',
        ),),
        "evaluate_cnn": (FixedCodeExperiment(
            'Find the hardest digit',
            'print("Test accuracy:", round(accuracy, 3))',
            'print("Test accuracy:", round(accuracy, 3))\nfor digit in range(10):\n    mask = y_test == digit\n    print(digit, round((y_pred[mask] == digit).float().mean().item(), 2))',
            'Print the accuracy for each digit separately. Predict which digits the model finds hardest.',
            '0 is perfect (1.0), while 3 (0.84), 8 (0.85) and 9 (0.85) are the hardest. The overall 0.921 hides that some digits are much harder than others.',
        ),),
    },
}


def fixed_code_experiments(task: str, stage: str) -> tuple[FixedCodeExperiment, ...]:
    normalized_task = "sentiment_classification" if task == "sentiment" else task
    try:
        return FIXED_CODE_EXPERIMENTS[normalized_task][stage]
    except KeyError:
        raise ValueError(f"no fixed code experiments are registered for {task}/{stage}") from None


def fixed_lesson_code(task: str, stage: str) -> FixedLessonCode:
    normalized_task = "sentiment_classification" if task == "sentiment" else task
    try:
        return FIXED_LESSON_CODE[normalized_task][stage]
    except KeyError:
        raise ValueError(f"no fixed lesson code is registered for {task}/{stage}") from None


def fixed_lesson_prerequisites(task: str, stage: str) -> list[str]:
    """Return canonical cells that must run before the requested stage.

    This is a recovery path for learners who resume a persisted lesson in a new
    browser session without session-scoped successful cell executions.
    """
    normalized_task = "sentiment_classification" if task == "sentiment" else task
    try:
        stages = FIXED_LESSON_CODE[normalized_task]
    except KeyError:
        raise ValueError(f"no fixed lesson code is registered for {task}") from None
    if stage not in stages:
        raise ValueError(f"no fixed lesson code is registered for {task}/{stage}")
    prerequisites: list[str] = []
    for stage_name, lesson_code in stages.items():
        if stage_name == stage:
            break
        prerequisites.append(lesson_code.code)
    return prerequisites
