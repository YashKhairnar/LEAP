"""Small, isolated evaluator process. It receives code on stdin and emits JSON."""
from __future__ import annotations

import ast
import json
import sys
import types

ALLOWED_IMPORTS = {"pandas", "sklearn.model_selection", "sklearn.feature_extraction.text", "sklearn.linear_model", "sklearn.metrics", "sklearn.preprocessing", "tensorflow.keras", "tensorflow.keras.layers", "tensorflow.keras.utils"}
BLOCKED_NAMES = {"breakpoint", "compile", "eval", "exec", "globals", "input", "locals", "open", "vars", "__import__"}


class Value:
    def __init__(self, name: str): self.name = name
    def __getitem__(self, key): return Value(f"{self.name}[{key!r}]")
    def dropna(self, **kwargs): return Value(f"{self.name}.dropna({kwargs!r})")


class Recorder:
    def __init__(self):
        self.calls: list[tuple[str, tuple, dict]] = []
        self.outputs: dict[str, object] = {}
    def record(self, name, *args, **kwargs):
        self.calls.append((name, args, kwargs))


def validate(tree: ast.AST) -> None:
    forbidden = (ast.AsyncFor, ast.AsyncFunctionDef, ast.Await, ast.ClassDef, ast.Delete, ast.For, ast.FunctionDef, ast.Global, ast.Lambda, ast.Nonlocal, ast.Raise, ast.Try, ast.While, ast.With, ast.Yield, ast.YieldFrom)
    for node in ast.walk(tree):
        if isinstance(node, forbidden): raise ValueError("Use direct statements only; loops, functions, classes, and file operations are disabled.")
        if isinstance(node, ast.Import):
            if any(alias.name not in ALLOWED_IMPORTS for alias in node.names): raise ValueError("Only the libraries shown in the starter code are available.")
        if isinstance(node, ast.ImportFrom):
            if node.module not in ALLOWED_IMPORTS or node.level: raise ValueError("Only the libraries shown in the starter code are available.")
        if isinstance(node, ast.Name) and node.id in BLOCKED_NAMES: raise ValueError(f"{node.id} is disabled in this exercise.")
        if isinstance(node, ast.Attribute) and node.attr.startswith("_"): raise ValueError("Private attributes are disabled in this exercise.")


def run(evaluator: str, source: str) -> tuple[bool, str]:
    tree = ast.parse(source, mode="exec")
    validate(tree)
    recorder = Recorder()

    def read_csv(path):
        recorder.record("read_csv", path); recorder.outputs["df"] = Value("loaded_dataframe"); return recorder.outputs["df"]
    def split(x, y, **kwargs):
        recorder.record("split", x, y, **kwargs)
        values = tuple(Value(f"split_{name}") for name in ("X_train", "X_test", "y_train", "y_test"))
        recorder.outputs.update(dict(zip(("X_train", "X_test", "y_train", "y_test"), values)))
        return values
    class Vectorizer:
        def __init__(self, **kwargs): recorder.record("vectorizer_init", **kwargs)
        def fit_transform(self, value): recorder.record("fit_transform", value); recorder.outputs["X_train_tfidf"] = Value("train_matrix"); return recorder.outputs["X_train_tfidf"]
        def transform(self, value): recorder.record("transform", value); recorder.outputs["X_test_tfidf"] = Value("test_matrix"); return recorder.outputs["X_test_tfidf"]
    class Logistic:
        def __init__(self, **kwargs): recorder.record("model_init", **kwargs)
        def fit(self, x, y): recorder.record("fit", x, y); return self
    class LinearRegression(Logistic): pass
    class StandardScaler:
        def fit_transform(self, value): recorder.record("scale_fit_transform", value); recorder.outputs["X_train_scaled"] = Value("train_scaled"); return recorder.outputs["X_train_scaled"]
        def transform(self, value): recorder.record("scale_transform", value); recorder.outputs["X_test_scaled"] = Value("test_scaled"); return recorder.outputs["X_test_scaled"]
    class Layer:
        def __init__(self, *args, **kwargs): self.args, self.kwargs = args, kwargs
    class Rescaling(Layer):
        def __init__(self, factor, *args, **kwargs): super().__init__(factor, *args, **kwargs); recorder.record("rescaling", factor)
    class Conv2D(Layer):
        def __init__(self, *args, **kwargs): super().__init__(*args, **kwargs); recorder.record("conv2d", *args, **kwargs)
    class MaxPooling2D(Layer):
        def __init__(self, *args, **kwargs): super().__init__(*args, **kwargs); recorder.record("pool", *args, **kwargs)
    class Sequential:
        def __init__(self, layers): self.layers = layers; recorder.record("sequential", layers)
        def fit(self, data, **kwargs): recorder.record("cnn_fit", data, **kwargs); recorder.outputs["history"] = Value("history"); return recorder.outputs["history"]
        def predict(self, data): recorder.record("cnn_predict", data); recorder.outputs["probabilities"] = Value("probabilities"); return recorder.outputs["probabilities"]
        def evaluate(self, data): recorder.record("cnn_evaluate", data); values = (Value("test_loss"), Value("test_accuracy")); recorder.outputs.update({"test_loss": values[0], "test_accuracy": values[1]}); return values
    class ExistingModel:
        def predict(self, x): recorder.record("predict", x); recorder.outputs["y_pred"] = Value("predictions"); return recorder.outputs["y_pred"]
        def fit(self, x, y=None, **kwargs): recorder.record("cnn_fit", x, y, **kwargs); recorder.outputs["history"] = Value("history"); return recorder.outputs["history"]
        def evaluate(self, x): recorder.record("cnn_evaluate", x); values = (Value("test_loss"), Value("test_accuracy")); recorder.outputs.update({"test_loss": values[0], "test_accuracy": values[1]}); return values
    def accuracy_score(y, pred): recorder.record("accuracy", y, pred); recorder.outputs["accuracy"] = 0.75; return recorder.outputs["accuracy"]
    def mean_absolute_error(y, pred): recorder.record("mae", y, pred); recorder.outputs["mae"] = 10.0; return recorder.outputs["mae"]
    def image_loader(path, **kwargs): recorder.record("image_loader", path, **kwargs); recorder.outputs["train_ds"] = Value("loaded_images"); return recorder.outputs["train_ds"]

    modules = {
        "pandas": types.SimpleNamespace(read_csv=read_csv),
        "sklearn.model_selection": types.SimpleNamespace(train_test_split=split),
        "sklearn.feature_extraction.text": types.SimpleNamespace(TfidfVectorizer=Vectorizer),
        "sklearn.linear_model": types.SimpleNamespace(LogisticRegression=Logistic, LinearRegression=LinearRegression),
        "sklearn.metrics": types.SimpleNamespace(accuracy_score=accuracy_score, mean_absolute_error=mean_absolute_error),
        "sklearn.preprocessing": types.SimpleNamespace(StandardScaler=StandardScaler),
        "tensorflow.keras": types.SimpleNamespace(Sequential=Sequential),
        "tensorflow.keras.layers": types.SimpleNamespace(Rescaling=Rescaling, Conv2D=Conv2D, MaxPooling2D=MaxPooling2D),
        "tensorflow.keras.utils": types.SimpleNamespace(image_dataset_from_directory=image_loader),
    }
    def safe_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name not in modules: raise ImportError("That module is unavailable in this exercise.")
        return modules[name]
    safe_builtins = {"__import__": safe_import, "len": len, "print": lambda *args, **kwargs: None, "range": range}
    env = {"__builtins__": safe_builtins, "df": Value("df"), "X": Value("X"), "y": Value("y"), "X_train": Value("X_train"), "X_test": Value("X_test"), "y_train": Value("y_train"), "y_test": Value("y_test"), "X_train_tfidf": Value("X_train_tfidf"), "X_test_tfidf": Value("X_test_tfidf"), "X_train_scaled": Value("X_train_scaled"), "X_test_scaled": Value("X_test_scaled"), "y_pred": Value("y_pred"), "train_ds": Value("train_ds"), "test_ds": Value("test_ds"), "model": ExistingModel()}
    exec(compile(tree, "<student-code>", "exec"), env, env)
    calls = recorder.calls
    call = lambda name: next((entry for entry in calls if entry[0] == name), None)
    names = lambda entry: tuple(getattr(value, "name", None) for value in entry[1]) if entry else ()

    assigned = lambda name: name in recorder.outputs and env.get(name) is recorder.outputs[name]
    if evaluator == "data_loading": ok = call("read_csv") is not None and call("read_csv")[1] == ("reviews.csv",) and assigned("df")
    elif evaluator == "train_test_split": ok = names(call("split")) == ("df['text']", "df['sentiment']") and call("split")[2].get("test_size") == 0.2 and all(assigned(name) for name in ("X_train", "X_test", "y_train", "y_test"))
    elif evaluator == "tfidf_vectorization": ok = call("vectorizer_init") is not None and names(call("fit_transform")) == ("X_train",) and names(call("transform")) == ("X_test",) and all(assigned(name) for name in ("X_train_tfidf", "X_test_tfidf"))
    elif evaluator == "model_training": ok = call("model_init") is not None and names(call("fit")) == ("X_train_tfidf", "y_train") and isinstance(env.get("model"), Logistic)
    elif evaluator == "prediction": ok = names(call("predict")) == ("X_test_tfidf",) and assigned("y_pred")
    elif evaluator == "evaluation": ok = names(call("accuracy")) == ("y_test", "y_pred") and assigned("accuracy")
    elif evaluator == "cnn_load_images": ok = call("image_loader") is not None and call("image_loader")[1] == ("images",) and call("image_loader")[2].get("image_size") == (128, 128) and assigned("train_ds")
    elif evaluator == "cnn_normalize": ok = call("rescaling") is not None and call("rescaling")[1] == (1 / 255,) and isinstance(env.get("normalizer"), Rescaling)
    elif evaluator == "cnn_build": ok = call("sequential") is not None and call("conv2d") is not None and call("pool") is not None and isinstance(env.get("model"), Sequential)
    elif evaluator == "cnn_train": ok = names(call("cnn_fit"))[:1] == ("train_ds",) and call("cnn_fit")[2].get("epochs") == 5 and assigned("history")
    elif evaluator == "cnn_predict": ok = names(call("predict")) == ("test_ds",) and env.get("probabilities") is recorder.outputs.get("y_pred")
    elif evaluator == "cnn_evaluate": ok = names(call("cnn_evaluate")) == ("test_ds",) and assigned("test_loss") and assigned("test_accuracy")
    elif evaluator == "reg_load_data": ok = call("read_csv") is not None and call("read_csv")[1] == ("houses.csv",) and isinstance(env.get("df"), Value) and ".dropna" in env["df"].name and "price" in env["df"].name
    elif evaluator == "reg_split": ok = names(call("split")) == ("X", "y") and call("split")[2].get("test_size") == 0.2 and all(assigned(name) for name in ("X_train", "X_test", "y_train", "y_test"))
    elif evaluator == "reg_scale": ok = names(call("scale_fit_transform")) == ("X_train",) and names(call("scale_transform")) == ("X_test",) and assigned("X_train_scaled") and assigned("X_test_scaled")
    elif evaluator == "reg_train": ok = call("model_init") is not None and names(call("fit")) == ("X_train_scaled", "y_train") and isinstance(env.get("model"), LinearRegression)
    elif evaluator == "reg_predict": ok = names(call("predict")) == ("X_test_scaled",) and assigned("y_pred")
    elif evaluator == "reg_evaluate": ok = names(call("mae")) == ("y_test", "y_pred") and assigned("mae")
    else: raise ValueError("Unknown evaluator.")
    return ok, "All required operations were detected." if ok else "The code ran, but it did not complete every required operation. Check the variable names and inputs in the prompt."


def main() -> None:
    payload = json.loads(sys.stdin.read())
    try:
        correct, feedback = run(sys.argv[1], payload["code"])
        print(json.dumps({"correct": correct, "feedback": feedback}))
    except (SyntaxError, ValueError, ImportError, NameError, TypeError, AttributeError) as error:
        print(json.dumps({"correct": False, "feedback": f"{type(error).__name__}: {error}"}))


if __name__ == "__main__": main()
