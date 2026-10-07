"""Versioned, canonical code shown in generated LEAP lessons."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FixedLessonCode:
    version: str
    language: str
    code: str


CODE_VERSION = "real_datasets_pytorch_v2"
EXPERIMENT_VERSION = "fixed_stage_experiments_v1"


@dataclass(frozen=True)
class FixedCodeExperiment:
    title: str
    find: str
    replace: str
    expected_change: str


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
'''),
        "tfidf_vectorization": _python('''
from sklearn.feature_extraction.text import TfidfVectorizer

vectorizer = TfidfVectorizer()
X_train_tfidf = vectorizer.fit_transform(X_train)
X_test_tfidf = vectorizer.transform(X_test)
'''),
        "model_training": _python('''
from sklearn.linear_model import LogisticRegression

model = LogisticRegression(max_iter=1000, random_state=42)
model.fit(X_train_tfidf, y_train)
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
'''),
        "scale_features": _python('''
from sklearn.preprocessing import StandardScaler

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)
'''),
        "train_regression": _python('''
from sklearn.linear_model import LinearRegression

model = LinearRegression()
model.fit(X_train_scaled, y_train)
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
            "Preview just two reviews",
            'print(df.head())',
            'print(df.head(2))',
            "The preview shows two reviews instead of five. The total row count stays the same: head() only changes what you display.",
        ),),
        "train_test_split": (FixedCodeExperiment(
            "Reserve 30% for testing",
            '    test_size=0.2,\n    random_state=42,\n    stratify=df["sentiment"],\n)',
            '    test_size=0.3,\n    random_state=42,\n    stratify=df["sentiment"],\n)\nprint("Training reviews:", len(X_train), "Test reviews:", len(X_test))',
            "The added print shows 2,100 training reviews and 900 test reviews, instead of the original 2,400/600 split. More test data leaves less data for learning.",
        ),),
        "tfidf_vectorization": (FixedCodeExperiment(
            "Limit the vocabulary to 100 words",
            'vectorizer = TfidfVectorizer()\nX_train_tfidf = vectorizer.fit_transform(X_train)\nX_test_tfidf = vectorizer.transform(X_test)',
            'vectorizer = TfidfVectorizer(max_features=100)\nX_train_tfidf = vectorizer.fit_transform(X_train)\nX_test_tfidf = vectorizer.transform(X_test)\nprint("Training matrix:", X_train_tfidf.shape)\nprint("Test matrix:", X_test_tfidf.shape)',
            "Both printed shapes have 100 columns, one per selected word. Row counts still reflect the training and test reviews. The vocabulary is learned only from training data.",
        ),),
        "model_training": (FixedCodeExperiment(
            "Inspect five learned word weights",
            'model.fit(X_train_tfidf, y_train)',
            'model.fit(X_train_tfidf, y_train)\nfor word, weight in list(zip(vectorizer.get_feature_names_out(), model.coef_[0]))[:5]:\n    print(word, round(weight, 3))',
            "Five vocabulary words now appear with learned weights. Positive weights push toward model.classes_[1], negative weights toward model.classes_[0]. Fitting learns these numbers from the training reviews.",
        ),),
        "prediction": (FixedCodeExperiment(
            "Show only three predictions",
            'for review, prediction in list(zip(X_test, y_pred))[:10]:',
            'for review, prediction in list(zip(X_test, y_pred))[:3]:',
            "Only three labeled reviews are printed instead of ten. model.predict() still makes predictions for the entire test set; the slice only limits the display.",
        ),),
        "evaluation": (FixedCodeExperiment(
            "Show more detail in the report",
            'print(classification_report(y_test, y_pred, zero_division=0))',
            'print(classification_report(y_test, y_pred, zero_division=0, digits=4))',
            "Precision, recall, and F1 are displayed with four decimal places instead of two. This reveals rounding detail without changing the model or its predictions.",
        ),),
    },
    "regression": {
        "prepare_housing_data": (FixedCodeExperiment(
            "Preview two houses",
            'df.head()',
            'print(df.head(2))',
            "The output lists two houses instead of five, including their features and sale prices. X and y still contain all prepared rows.",
        ),),
        "split_housing_data": (FixedCodeExperiment(
            "Reserve 30% of houses for testing",
            '    X, y, test_size=0.2, random_state=42\n)',
            '    X, y, test_size=0.3, random_state=42\n)\nprint("Training houses:", len(X_train), "Test houses:", len(X_test))',
            "The added print shows the new split sizes. About 30% of the prepared houses are now held out, leaving fewer examples to train the model. Features and prices remain paired.",
        ),),
        "scale_features": (FixedCodeExperiment(
            "Compare a house before and after scaling",
            'X_test_scaled = scaler.transform(X_test)',
            'X_test_scaled = scaler.transform(X_test)\nprint("Features:", feature_columns)\nprint("Before:", X_train.iloc[0].to_numpy())\nprint("After:", X_train_scaled[0].round(2))',
            "The same house now appears in original units and standardized units. After scaling, a negative value means below that feature's training-set average; a positive value means above it.",
        ),),
        "train_regression": (FixedCodeExperiment(
            "Inspect what the model learned",
            'model.fit(X_train_scaled, y_train)',
            'model.fit(X_train_scaled, y_train)\nfor feature, coefficient in zip(feature_columns, model.coef_):\n    print(feature, round(coefficient, 2))',
            "One learned coefficient is printed for each feature. Its sign shows the direction of the predicted price change, holding other features fixed. Because inputs were scaled, each coefficient is per one training standard deviation, not per original unit.",
        ),),
        "predict_prices": (FixedCodeExperiment(
            "Inspect three price predictions",
            'for actual, predicted in list(zip(y_test, y_pred))[:10]:',
            'for actual, predicted in list(zip(y_test, y_pred))[:3]:',
            "Three actual/predicted price pairs are printed instead of ten. Compare each pair to see individual errors; predictions for the full test set still exist in y_pred.",
        ),),
        "evaluate_regression": (FixedCodeExperiment(
            "Look at the errors behind the average",
            'print(f"Mean absolute error: ${mae:,.0f}")',
            'print(f"Mean absolute error: ${mae:,.0f}")\nfor actual, predicted in list(zip(y_test, y_pred))[:3]:\n    print(f"Absolute error: ${abs(actual - predicted):,.0f}")',
            "Three individual absolute errors appear below MAE. Each is a nonnegative dollar difference; MAE averages such errors across all test houses, not just these three.",
        ),),
    },
    "cnn": {
        "load_images": (FixedCodeExperiment(
            "Inspect one image as numbers",
            'print("Images:", images.shape, "Classes:", len(np.unique(labels)))',
            'print("Images:", images.shape, "Classes:", len(np.unique(labels)))\nprint("First label:", labels[0])\nprint(images[0, 0])',
            "The output adds the first image's digit label and its 8×8 grid of pixel intensities. These numbers, not an image filename, are what the CNN receives.",
        ),),
        "normalize_split": (FixedCodeExperiment(
            "Use smaller training batches",
            'train_loader = DataLoader(train_dataset, batch_size=128, shuffle=True, generator=generator)',
            'train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True, generator=generator)\nprint("Images per full training batch:", train_loader.batch_size)\nprint("Training batches:", len(train_loader))',
            "The loader reports batches of 32 images and 141 training batches instead of 36. The training/test split is unchanged; smaller batches mean more optimizer updates per pass during training.",
        ),),
        "build_cnn": (FixedCodeExperiment(
            "Inspect the network's layers",
            '    nn.Linear(16 * 4 * 4, 10),\n)',
            '    nn.Linear(16 * 4 * 4, 10),\n)\nprint(model)',
            "The network's layers are printed in order: convolution, activation, pooling, flattening, and a linear layer with 10 outputs. Building this structure does not train its weights yet.",
        ),),
        "train_network": (FixedCodeExperiment(
            "Try a smaller learning rate",
            'optimizer = torch.optim.Adam(model.parameters(), lr=0.01)',
            'optimizer = torch.optim.Adam(model.parameters(), lr=0.001)',
            "Run the original first and note its final batch loss, then compare this run. The learning rate is ten times smaller. Loss may change; a smaller rate is not guaranteed to improve it after only one pass.",
        ),),
        "classify_images": (FixedCodeExperiment(
            "Show three predicted digits",
            'print("First predictions:", y_pred[:10].tolist())',
            'print("First predictions:", y_pred[:3].tolist())',
            "The printed list contains three predicted digits instead of ten. The network still classifies every test image, and all predictions remain available for evaluation.",
        ),),
        "evaluate_cnn": (FixedCodeExperiment(
            "Display accuracy as a percentage",
            'print("Test accuracy:", round(accuracy, 3))',
            'print(f"Test accuracy: {accuracy:.1%}")',
            "Accuracy is displayed as a percentage with one decimal place instead of a fraction. The same correct predictions and test images are counted; only formatting changes.",
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
