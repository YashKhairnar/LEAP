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

AUTHORED_CONTENT_VERSION = "authored_content_v2"


class AuthoredContentUnavailable(ValueError):
    pass


STAGES: dict[str, dict[str, object]] = {
    "data_loading_and_preparation": {
        "title": "Load labeled reviews",
        "intro": "A classifier starts with rows that keep each review paired with its known sentiment.",
        "target": "a pandas DataFrame of labeled rows",
        "relationship": "one review becomes one row with an input and a label",
        "analogy": "In Java, you might keep Review objects in a List. Here, pandas loads each review into one DataFrame row and keeps its sentiment label beside it.",
        "example": "The review column is the text input. The sentiment column is the known answer the model will learn to predict.",
        "result": "read_csv creates df, then head displays sample rows and len(df) reports the number of loaded rows.",
        "why": "Every later stage depends on correctly paired review text and sentiment labels.",
        "operation": ("Which call loads the review dataset into a DataFrame?", "pd.read_csv(\"reviews.csv\")", ["pd.read_csv(\"reviews.csv\")", "model.fit(X, y)", "model.predict(X)"], "read_csv reads the CSV into a pandas DataFrame; fitting and prediction happen later."),
        "variable": ("What does the sentiment column provide?", "The known label for each review", ["The known label for each review", "The model's prediction", "The number of words in each review"], "Sentiment is the target label paired with each review."),
        "boundary": ("A correct preparation rule is:", "Keep each review paired with its sentiment label", ["Keep each review paired with its sentiment label", "Remove labels before splitting", "Use the row number as the label" ]),
        "ordering": ("Which order begins the pipeline correctly?", "load rows → inspect paired fields → split data", ["load rows → inspect paired fields → split data", "predict → load rows → fit", "evaluate → split → load rows"]),
        "transfer": ("In a support-ticket dataset, what would one labeled row contain?", "One ticket paired with its known category", ["One ticket paired with its known category", "Only the total number of tickets", "A trained classifier with no ticket" ]),
        "review": "Loading is successful only when each input review remains paired with its target sentiment.",
    },
    "train_test_split": {
        "title": "Separate learning from evaluation",
        "intro": "A held-out test set lets us measure performance on reviews the model did not learn from.",
        "target": "training and held-out test partitions",
        "relationship": "one collection becomes two purpose-specific subsets",
        "analogy": "A practice set supports learning; a separate final set checks whether the learning transfers.",
        "example": "With test_size=0.2, about one fifth of the reviews are reserved for testing while the remaining reviews train the pipeline.",
        "result": "train_test_split returns X_train, X_test, y_train, and y_test while keeping each review paired with its sentiment.",
        "why": "If test reviews influence training, the final score can look better than performance on genuinely unseen reviews.",
        "operation": ("Which function creates training and test partitions?", "train_test_split", ["train_test_split", "read_csv", "predict"], "train_test_split separates features and labels into training and held-out sets."),
        "variable": ("What does X_test contain?", "Held-out review text", ["Held-out review text", "Training labels", "Model predictions"], "X_test contains input text reserved for later evaluation."),
        "boundary": ("What must remain true during a fair split?", "Test reviews remain unseen during training", ["Test reviews remain unseen during training", "Test reviews are copied into training", "Splitting trains the classifier"], "The test set is for evaluation, not for learning model parameters."),
        "ordering": ("Which order protects the test set?", "load → split → fit preprocessing on training data", ["load → split → fit preprocessing on training data", "fit preprocessing → split → evaluate", "predict → split → load"]),
        "transfer": ("Why split a house-price dataset?", "To test on homes not used for learning", ["To test on homes not used for learning", "To remove every price", "To duplicate every home"], "A held-out set estimates how well the model transfers to unseen homes."),
        "review": "A fair split keeps held-out examples separate until the pipeline is ready to evaluate them.",
    },
    "tfidf_vectorization": {
        "title": "Turn review text into numeric features",
        "intro": "A classifier needs numbers, so TF-IDF represents each review using weighted term features.",
        "target": "a TF-IDF feature matrix",
        "relationship": "each review becomes a numeric vector",
        "analogy": "A Java Map<String, Double> can associate terms with weights; TF-IDF creates aligned numeric columns for reviews.",
        "example": "fit_transform learns vocabulary and weights from X_train. transform applies those same columns to X_test.",
        "result": "The vectorizer creates sparse numeric matrices whose columns have the same meaning for training and test reviews.",
        "why": "The model can learn from numeric features, but fitting the vocabulary on test text would leak held-out information.",
        "operation": ("Which call learns the vocabulary and transforms training text?", "fit_transform(X_train)", ["fit_transform(X_train)", "transform(y_train)", "predict(X_train)"], "fit_transform learns training vocabulary and weights, then creates the training matrix."),
        "variable": ("What does one row of X_train_tfidf represent?", "One review as numeric term weights", ["One review as numeric term weights", "One sentiment label", "One trained classifier"], "Each row is the numeric representation of one review."),
        "boundary": ("Which preprocessing boundary prevents leakage?", "Fit on training text; only transform test text", ["Fit on training text; only transform test text", "Fit a separate vocabulary on test text", "Let TF-IDF directly predict sentiment"], "Training statistics must not use held-out text."),
        "ordering": ("Which order keeps feature meanings aligned?", "split → fit_transform train → transform test", ["split → fit_transform train → transform test", "transform test → split → load", "predict → fit_transform → split"]),
        "transfer": ("For spam detection, what does TF-IDF produce?", "Numeric vectors for email text", ["Numeric vectors for email text", "Final spam decisions", "New email labels"], "TF-IDF represents text; a later classifier makes the decision."),
        "review": "TF-IDF creates aligned numeric features while learning vocabulary only from training text.",
    },
    "model_training": {
        "title": "Fit the classifier",
        "intro": "LogisticRegression learns parameters that connect training feature patterns to known sentiment labels.",
        "target": "a fitted LogisticRegression model",
        "relationship": "fit changes model parameters using paired examples",
        "analogy": "Calling fit is like a Java method updating an object's internal fields from input examples.",
        "example": "The model receives X_train_tfidf and y_train, so it can associate numeric word patterns with positive or negative labels.",
        "result": "LogisticRegression creates a model object, and fit stores learned parameters inside it; the original reviews are unchanged.",
        "why": "Training is the point where the classifier learns a decision boundary from labeled examples.",
        "operation": ("Which line actually trains the classifier?", "model.fit(X_train_tfidf, y_train)", ["model.fit(X_train_tfidf, y_train)", "LogisticRegression()", "model.predict(X_test_tfidf)"], "fit uses training features and labels to learn model parameters."),
        "variable": ("What does y_train provide during fitting?", "Known sentiment labels", ["Known sentiment labels", "Unseen review vectors", "Accuracy scores"], "The labels tell supervised learning which outcome belongs to each training review."),
        "boundary": ("Which distinction is correct?", "Constructing a model is not the same as fitting it", ["Constructing a model is not the same as fitting it", "predict trains the model", "fit should use test labels"], "The constructor creates the model; fit learns its parameters."),
        "ordering": ("Which order follows vectorization?", "vectorize train → fit model → predict test", ["vectorize train → fit model → predict test", "predict test → fit model → split", "evaluate → fit → load"]),
        "transfer": ("What would fit learn in a spam classifier?", "Parameters connecting email features to spam labels", ["Parameters connecting email features to spam labels", "A new CSV file", "The test-set answers"], "Fitting learns the relationship between input features and labels."),
        "review": "Fitting is the learning step: training features and labels update the classifier's parameters.",
    },
    "prediction": {
        "title": "Predict unseen reviews",
        "intro": "The fitted classifier applies its learned parameters to feature vectors from held-out reviews.",
        "target": "predicted sentiment labels",
        "relationship": "stored parameters determine a new output",
        "analogy": "After learning a rule from worked examples, you apply it to a new case without looking at its answer.",
        "example": "model.predict receives X_test_tfidf and returns one predicted label for each held-out review vector.",
        "result": "y_pred stores predictions, and the loop displays a small sample of review-and-prediction pairs.",
        "why": "Prediction applies the learned pipeline without changing its parameters or using the held-out labels as input.",
        "operation": ("Which call produces labels for held-out reviews?", "model.predict(X_test_tfidf)", ["model.predict(X_test_tfidf)", "model.fit(X_test_tfidf, y_test)", "vectorizer.fit(X_test)"], "predict applies the fitted classifier to test vectors."),
        "variable": ("What does y_pred contain?", "Predicted sentiment labels", ["Predicted sentiment labels", "Original training reviews", "TF-IDF vocabulary"], "Each element is the model's predicted class for one test review."),
        "boundary": ("Which statement describes prediction?", "Prediction applies learned parameters without updating them", ["Prediction applies learned parameters without updating them", "Prediction requires y_test as input", "Prediction retrains TF-IDF"], "Prediction uses the fitted pipeline; it does not retrain it."),
        "ordering": ("Which order produces held-out predictions?", "fit vectorizer → fit model → predict", ["fit vectorizer → fit model → predict", "predict → fit model → vectorize", "evaluate → predict → train"]),
        "transfer": ("For a new movie review, what should the pipeline return?", "A predicted sentiment label", ["A predicted sentiment label", "A known training label", "A new model vocabulary"], "A new review is transformed with the fitted vectorizer and classified by the fitted model."),
        "review": "Prediction uses the fitted feature pipeline and model to assign labels without learning from the answers.",
    },
    "evaluation": {
        "title": "Measure performance honestly",
        "intro": "Evaluation compares held-out predictions with held-out labels to describe what the classifier gets right and wrong.",
        "target": "classification metrics on y_test and y_pred",
        "relationship": "actual and predicted values are compared",
        "analogy": "A test score summarizes results, while an error breakdown shows which kinds of answers were missed.",
        "example": "accuracy_score compares y_test with y_pred. classification_report adds per-class precision, recall, and F1 details.",
        "result": "The code prints an accuracy value and a report describing performance for each sentiment class.",
        "why": "A single score is useful, but class-level metrics can reveal failures hidden by overall accuracy.",
        "operation": ("Which call computes the fraction of correct predictions?", "accuracy_score(y_test, y_pred)", ["accuracy_score(y_test, y_pred)", "model.fit(y_test, y_pred)", "vectorizer.transform(y_pred)"], "Accuracy compares true and predicted labels and returns the correct fraction."),
        "variable": ("What is y_test during evaluation?", "The true held-out labels", ["The true held-out labels", "The model predictions", "The fitted vocabulary"], "y_test provides the answers used after predictions are made."),
        "boundary": ("Which evaluation rule is correct?", "Evaluation measures performance; it should not retrain the model", ["Evaluation measures performance; it should not retrain the model", "Accuracy should use training labels only", "A report creates new predictions"], "Evaluation compares outputs with held-out truth; it does not update the model."),
        "ordering": ("Which order completes the pipeline?", "predict test → compare with y_test → report metrics", ["predict test → compare with y_test → report metrics", "report metrics → train → split", "compare labels → load → predict"]),
        "transfer": ("Why inspect precision and recall as well as accuracy?", "Different error types can matter differently", ["Different error types can matter differently", "They retrain the classifier", "They replace test data"], "Per-class metrics show errors that overall accuracy can hide."),
        "review": "Honest evaluation compares unseen predictions with withheld truth and examines more than one metric.",
    },
}


def _stage_content(
    title: str,
    intro: str,
    target: str,
    relationship: str,
    analogy: str,
    example: str,
    result: str,
    why: str,
    operation: tuple[str, str, list[str], str],
    variable: tuple[str, str, list[str], str],
    boundary: tuple[str, str, list[str], str],
    ordering: tuple[str, str, list[str], str],
    transfer: tuple[str, str, list[str], str],
    review: str,
) -> dict[str, object]:
    return {
        "title": title, "intro": intro, "target": target, "relationship": relationship,
        "analogy": analogy, "example": example, "result": result, "why": why,
        "operation": operation, "variable": variable, "boundary": boundary,
        "ordering": ordering, "transfer": transfer, "review": review,
    }


CNN_STAGES: dict[str, dict[str, object]] = {
    "load_images": _stage_content(
        "Load digit images", "Each optical-digit row stores 64 pixel intensities and one digit label; the first step reshapes those values into image tensors.",
        "a labeled PyTorch image dataset", "64 pixel values become one single-channel 8 × 8 image tensor",
        "A Java array of 64 measurements becomes a small grid object with an associated digit label.",
        "The tensor shape is (examples, channels, height, width), so a row becomes (1, 8, 8) before batching.",
        "TensorDataset pairs each image tensor with its numeric digit label.", "The network cannot use flat table rows until their spatial image structure is represented.",
        ("Which operation turns the 64 pixel columns into image tensors?", "reshape(-1, 1, 8, 8)", ["reshape(-1, 1, 8, 8)", "argmax(dim=1)", "optimizer.step()"], "Reshaping gives each record channel, height, and width dimensions; it does not train the network."),
        ("What does the label tensor contain?", "The digit class for each image", ["The digit class for each image", "The learned convolution filters", "The test accuracy"], "Labels identify which digit each image represents."),
        ("What must remain paired?", "Each image tensor and its digit label", ["Each image tensor and its digit label", "Each image and a random label", "Pixels and the optimizer state"], "Supervised learning needs the correct target beside each input."),
        ("Which order begins the image pipeline?", "load rows → reshape images → create labeled dataset", ["load rows → reshape images → create labeled dataset", "predict → reshape → load", "evaluate → train → reshape"], "The data must be represented as labeled tensors before loaders and training."),
        ("For audio classification, what is the analogous operation?", "Convert each recording into a structured input tensor with its label", ["Convert each recording into a structured input tensor with its label", "Remove labels before inference", "Use the final accuracy as an input"], "Other modalities also need a structured input representation paired with a target."),
        "Loading is correct when every digit label stays attached to the corresponding image tensor.",
    ),
    "normalize_split": _stage_content(
        "Split and normalize images", "A fair CNN experiment keeps test images out of weight updates and scales pixel intensities into a stable numeric range.",
        "training and test image loaders", "one labeled dataset becomes train/test partitions while input values are normalized for the model",
        "A practice stack is used for learning; a sealed stack is opened only to check transfer.",
        "A reproducible split reserves 20% of the images for testing, while dividing pixel values by 16 maps their original range to approximately 0–1.",
        "DataLoaders provide shuffled training batches and separate test batches.", "The split estimates performance on images that did not update the network.",
        ("Which subset should update CNN weights?", "The training images", ["The training images", "The held-out test images", "Both sets after every batch"], "Only training batches should be used for optimizer updates."),
        ("What does normalization change?", "The numeric scale of pixel inputs", ["The numeric scale of pixel inputs", "The digit labels", "The number of output classes"], "Normalization changes representation scale without changing which digit an image shows."),
        ("Which rule prevents evaluation leakage?", "Keep test images out of training updates", ["Keep test images out of training updates", "Tune weights using test accuracy every batch", "Copy test labels into the training loader"], "Held-out data must remain unseen during learning."),
        ("Which order is valid?", "create labeled tensors → split → build loaders", ["create labeled tensors → split → build loaders", "evaluate → split → normalize labels", "train → load images → split"], "The loaders are built after the dataset has been partitioned."),
        ("Why use a held-out set for a spam classifier?", "To estimate performance on messages not used for fitting", ["To estimate performance on messages not used for fitting", "To create more labels", "To replace the training examples"], "A held-out set tests transfer to unseen inputs."),
        "A fair image experiment separates the test loader before any optimizer update uses the data.",
    ),
    "build_cnn": _stage_content(
        "Build convolutional feature extractors", "A CNN combines local filters, nonlinear activation, downsampling, and a final layer that scores the ten digit classes.",
        "an untrained ten-class CNN", "local image patterns are transformed into a vector of ten class scores",
        "A convolution layer is like a reusable pattern detector that scans each image instead of checking every pixel combination separately.",
        "Conv2d finds local patterns, ReLU adds a nonlinear response, MaxPool2d reduces spatial size, and Linear produces ten outputs.",
        "The Sequential model has the architecture, but its weights are not learned yet.", "Separating architecture from training makes it clear which step defines capacity and which step estimates parameters.",
        ("Which layer learns local visual filters?", "nn.Conv2d", ["nn.Conv2d", "nn.Flatten", "DataLoader"], "Conv2d learns filters that respond to local neighborhoods."),
        ("What do the ten final outputs represent?", "Scores for the ten digit classes", ["Scores for the ten digit classes", "Ten training batches", "Ten pixel rows"], "The final linear layer produces one score per possible digit."),
        ("Which statement is correct?", "Defining layers does not fit their weights", ["Defining layers does not fit their weights", "Flattening trains the filters", "DataLoader chooses the architecture"], "The model must be trained before its parameters encode useful patterns."),
        ("Which order describes the architecture?", "convolution → activation/pooling → flatten → class scores", ["convolution → activation/pooling → flatten → class scores", "class scores → convolution → load", "evaluate → flatten → define"], "Spatial features are progressively transformed into class scores."),
        ("What is a parallel idea in a tabular model?", "Define a model structure before fitting its parameters", ["Define a model structure before fitting its parameters", "Use test targets as input features", "Evaluate before creating the model"], "Model construction and parameter learning are separate operations across ML methods."),
        "The CNN definition describes the computation graph; training is still required to learn useful weights.",
    ),
    "train_network": _stage_content(
        "Train the CNN", "Training repeatedly compares predictions with known digit labels and updates filters to reduce classification loss.",
        "a CNN with learned weights", "a loss signal becomes gradients and optimizer updates to model parameters",
        "Training is like adjusting a set of knobs after comparing a program's output with the expected answer.",
        "The loop clears old gradients, computes loss, calls backward, and applies an Adam update.",
        "After updates, the model parameters contain information learned from training images.", "This is the stage where the architecture becomes a task-specific classifier.",
        ("Which call calculates parameter gradients?", "loss.backward()", ["loss.backward()", "optimizer.zero_grad()", "model.eval()"], "backward propagates the loss through the network to compute gradients."),
        ("What does y_batch provide during training?", "Known digit labels", ["Known digit labels", "Test predictions", "The image dimensions only"], "Labels provide the target used to calculate the loss."),
        ("Which data should the optimizer use?", "Training images and their labels", ["Training images and their labels", "Held-out test labels for every update", "Only the final accuracy"], "Optimizer updates should learn from the training partition."),
        ("Which order completes one update?", "forward pass → loss → backward → optimizer.step", ["forward pass → loss → backward → optimizer.step", "predict test → step → load", "evaluate → backward → split"], "The loss must be computed before gradients and the parameter update."),
        ("What would training learn for a flower classifier?", "Weights connecting image patterns to flower labels", ["Weights connecting image patterns to flower labels", "A new test set", "The final accuracy as a feature"], "Training learns a relationship between input patterns and targets."),
        "Training changes model weights using labeled training batches; it should not use held-out answers to update them.",
    ),
    "classify_images": _stage_content(
        "Classify unseen digits", "After training, the CNN applies its learned filters to held-out images and selects the class with the largest score.",
        "predicted digit classes", "a trained network maps each held-out image tensor to one predicted class",
        "Once a rule has been learned from examples, it can be applied to a new case without changing the rule.",
        "model.eval() switches behavior to evaluation mode, torch.no_grad() avoids gradient tracking, and argmax selects the largest class score.",
        "y_pred contains one predicted digit for each evaluated image.", "Inference applies the learned model without accidentally changing it during measurement.",
        ("Which operation chooses the predicted digit?", "argmax(dim=1)", ["argmax(dim=1)", "loss.backward()", "random_split()"], "argmax selects the class with the largest output score."),
        ("What does y_pred contain?", "Predicted digit labels", ["Predicted digit labels", "Training gradients", "Pixel means"], "Each prediction is the class selected for one input image."),
        ("Why use torch.no_grad() during inference?", "Inference does not need gradient history", ["Inference does not need gradient history", "It creates new labels", "It trains the convolution filters"], "Disabling gradient tracking reduces inference overhead and prevents accidental training behavior."),
        ("Which order is correct?", "load trained weights → evaluate mode → predict held-out images", ["load trained weights → evaluate mode → predict held-out images", "predict → train → split", "compare labels → define model → load"], "Inference begins with the trained model and then produces predictions."),
        ("For house prices, what is the analogous output?", "A numeric prediction for each held-out house", ["A numeric prediction for each held-out house", "A new convolution filter", "The training labels copied unchanged"], "Different tasks produce different output types, but inference applies learned parameters to unseen inputs."),
        "Prediction uses learned weights to produce outputs; it does not update those weights or require test labels as inputs.",
    ),
    "evaluate_cnn": _stage_content(
        "Measure held-out accuracy", "Evaluation compares predicted digits with held-out labels to summarize how often the CNN is correct on unseen images.",
        "test accuracy", "predicted classes are compared with true held-out classes to produce a performance metric",
        "A scorecard compares answers with an answer key after the practice period is over.",
        "Accuracy is the fraction of test predictions equal to their corresponding labels.",
        "The result is one accuracy value, while the individual predictions remain available for error analysis.", "A held-out metric estimates how well the learned visual patterns transfer beyond the training images.",
        ("What does test accuracy measure?", "The fraction of held-out digits classified correctly", ["The fraction of held-out digits classified correctly", "Optimizer updates", "Average pixel intensity"], "Accuracy counts correct predictions among the held-out examples."),
        ("What is y_test during evaluation?", "The true held-out digit labels", ["The true held-out digit labels", "The model's gradients", "The training images"], "The held-out labels are used as the reference after predictions are made."),
        ("Which evaluation rule is correct?", "Evaluation does not retrain the CNN", ["Evaluation does not retrain the CNN", "Test accuracy updates weights", "Accuracy replaces the test images"], "Evaluation measures the current model rather than changing it."),
        ("Which order completes the pipeline?", "predict test images → compare with labels → calculate accuracy", ["predict test images → compare with labels → calculate accuracy", "calculate accuracy → train → load", "split labels → evaluate → define"], "Predictions must exist before they can be compared with truth."),
        ("Why inspect errors beyond accuracy?", "Different digit classes may have different failure patterns", ["Different digit classes may have different failure patterns", "Errors retrain the model automatically", "Accuracy removes the need for labels"], "Aggregate accuracy can hide which classes or examples are difficult."),
        "Held-out accuracy is meaningful only when the test images were kept separate from training updates.",
    ),
}


REGRESSION_STAGES: dict[str, dict[str, object]] = {
    "prepare_housing_data": _stage_content(
        "Prepare housing records", "A regression pipeline begins with clean rows, numeric property features, and a continuous target price.",
        "clean feature rows and prices", "each house remains paired with its observed sale price",
        "A Java record can keep several property fields together with the value the program needs to estimate.",
        "The code loads houses.csv, removes incomplete rows, selects feature columns, and separates X from y.",
        "X contains bedrooms, bathrooms, square feet, and age; y contains the observed price.", "A model cannot learn a reliable price relationship from missing or mismatched inputs and targets.",
        ("Which column is the regression target?", "price", ["price", "bedrooms", "zipcode"], "price is the continuous value the model is asked to estimate."),
        ("What does X contain?", "Property features used as inputs", ["Property features used as inputs", "The model's predictions", "The final MAE only"], "X contains explanatory variables such as bedrooms and square feet."),
        ("What must remain paired?", "Each house's features and its observed price", ["Each house's features and its observed price", "A house and a random price", "Features and test accuracy"], "Supervised regression needs the correct target for each feature row."),
        ("Which order begins the regression pipeline?", "load and clean rows → select X and y → split data", ["load and clean rows → select X and y → split data", "predict → clean → fit", "evaluate → load → remove targets"], "The data contract must be established before fitting or prediction."),
        ("For energy forecasting, what is analogous to price?", "The continuous quantity paired with each feature row", ["The continuous quantity paired with each feature row", "A random class name", "The model's coefficients as inputs"], "Regression targets can be any continuous outcome paired with inputs."),
        "Preparation is complete when usable feature rows remain correctly paired with continuous prices.",
    ),
    "split_housing_data": _stage_content(
        "Reserve unseen houses", "A train/test split gives the model houses for learning and separate houses for an honest evaluation.",
        "training and held-out housing partitions", "one collection of houses becomes a learning set and an evaluation set",
        "Practice homes help estimate a rule; a separate set of homes checks whether the rule generalizes.",
        "With test_size=0.2, 20% of rows are held out while the remaining 80% are available for fitting.",
        "X_train, X_test, y_train, and y_test preserve features and prices for their respective partitions.", "Testing on houses used during fitting would make the error look more optimistic than real-world performance.",
        ("With 500 houses and test_size=0.2, how many are held out?", "100", ["100", "250", "400"], "Twenty percent of 500 is 100 houses."),
        ("What does y_test contain?", "Held-out observed prices", ["Held-out observed prices", "Training features", "Predicted prices before the model exists"], "y_test contains the reference prices reserved for evaluation."),
        ("What must remain true during a fair split?", "Test houses remain unseen during fitting", ["Test houses remain unseen during fitting", "Test houses are copied into training", "Splitting learns coefficients"], "The held-out partition is for measuring transfer, not learning parameters."),
        ("Which order protects the evaluation set?", "load → split → fit preprocessing on training data", ["load → split → fit preprocessing on training data", "fit preprocessing → split → evaluate", "predict → split → load"], "The split must happen before fitting transformations or the model."),
        ("Why split a rent dataset?", "To test price estimates on properties not used for learning", ["To test price estimates on properties not used for learning", "To remove every target", "To duplicate each property"], "A held-out set estimates performance on new properties."),
        "A fair split keeps held-out houses and prices separate until the pipeline is ready to evaluate them.",
    ),
    "scale_features": _stage_content(
        "Scale numeric features", "Standardization puts features such as square feet and age on comparable scales without using test-set statistics.",
        "scaled training and test feature matrices", "training statistics define a reusable transformation applied to both partitions",
        "A measuring tool can convert different units to a common reference without changing which house is being described.",
        "StandardScaler learns means and standard deviations from X_train, then fit_transform handles training data and transform handles X_test.",
        "X_train_scaled and X_test_scaled have comparable feature scales, while the original price target remains unchanged.", "Fitting the scaler on test data would leak information about the evaluation distribution into the pipeline.",
        ("Which data should fit the scaler?", "X_train", ["X_train", "X_test", "All houses before splitting"], "Training features provide the statistics that define the transformation."),
        ("What does X_test_scaled represent?", "Held-out features transformed with training statistics", ["Held-out features transformed with training statistics", "Predicted prices", "The fitted model coefficients"], "The test features use the already learned training transformation."),
        ("Which preprocessing boundary is correct?", "Fit on X_train; only transform X_test", ["Fit on X_train; only transform X_test", "Fit a separate scaler on X_test", "Use y_test to scale features"], "The test partition must not influence preprocessing parameters."),
        ("Which order avoids leakage?", "split → fit_transform train → transform test", ["split → fit_transform train → transform test", "transform test → split → fit", "predict → scale → split"], "The scaler learns from training features and reuses those statistics for test features."),
        ("For a sensor dataset, why scale features?", "To make numeric inputs comparable while preserving each row's identity", ["To make numeric inputs comparable while preserving each row's identity", "To turn measurements into labels", "To evaluate before fitting"], "Scaling changes units and range, not the supervised target relationship itself."),
        "Scaling is safe when its fitted statistics come only from training features and are reused for held-out features.",
    ),
    "train_regression": _stage_content(
        "Fit a price model", "LinearRegression learns coefficients that connect scaled property features to continuous house prices.",
        "a fitted linear regression model", "fit estimates coefficients from training features and known training prices",
        "Calling fit is like a Java method updating an object's fields after receiving examples and expected outputs.",
        "LinearRegression is constructed first, then fit receives X_train_scaled and y_train to estimate coefficients.",
        "The model stores a coefficient for each feature and an intercept that together produce price estimates.", "This is the point where the model learns a relationship rather than merely defining its structure.",
        ("Which method learns regression coefficients?", "model.fit", ["model.fit", "model.predict", "mean_absolute_error"], "fit estimates parameters from training inputs and target prices."),
        ("What does y_train provide?", "Known training prices", ["Known training prices", "Test feature names", "The final error metric"], "The target values tell supervised regression what each training row should predict."),
        ("Which distinction is correct?", "Constructing a model is not the same as fitting it", ["Constructing a model is not the same as fitting it", "predict trains the model", "fit should use test prices"], "The constructor creates the object; fit learns its parameters."),
        ("Which order follows scaling?", "scale training features → fit model → predict test", ["scale training features → fit model → predict test", "predict → fit → split", "evaluate → fit → load"], "The model is fitted after preprocessing and before prediction."),
        ("What would fit learn for energy usage?", "Coefficients connecting sensor features to continuous usage", ["Coefficients connecting sensor features to continuous usage", "A new sensor dataset", "The test-set answers"], "Fitting learns how inputs relate to a numeric target."),
        "Fitting is the learning step: training features and prices update the regression model's parameters.",
    ),
    "predict_prices": _stage_content(
        "Predict unseen prices", "The fitted regression model applies its learned coefficients to scaled features from held-out houses.",
        "continuous price predictions", "stored coefficients map each unseen feature row to a numeric estimate",
        "After learning a rule from worked examples, the rule can estimate a new case without seeing its answer first.",
        "model.predict(X_test_scaled) returns one numeric estimate for each held-out house.",
        "y_pred contains estimated prices that can later be compared with y_test.", "Prediction applies the model without changing its coefficients or using the held-out prices as inputs.",
        ("What does y_pred contain?", "Predicted prices", ["Predicted prices", "Training rows", "Feature names"], "Each element is the model's numeric estimate for one held-out house."),
        ("What is an input to model.predict here?", "Scaled test features", ["Scaled test features", "The true test prices", "The MAE before prediction"], "Prediction uses the feature matrix; true prices are reserved for evaluation."),
        ("Which prediction rule is correct?", "Prediction applies learned coefficients without updating them", ["Prediction applies learned coefficients without updating them", "Prediction retrains the scaler", "Prediction requires y_test as an input"], "Inference uses the fitted pipeline but does not learn from the answers."),
        ("Which order produces price estimates?", "fit scaler and model on training data → transform test features → predict", ["fit scaler and model on training data → transform test features → predict", "predict → fit model → load prices", "evaluate → split → predict"], "Test rows must receive the same preprocessing before prediction."),
        ("For a new apartment, what should the pipeline return?", "A numeric estimated price", ["A numeric estimated price", "A new feature scaler", "The known sale price as an input"], "A regression model returns a continuous estimate for a new input."),
        "Prediction produces estimates from learned parameters; it does not use held-out target values to make those estimates.",
    ),
    "evaluate_regression": _stage_content(
        "Measure prediction error", "Evaluation compares predicted prices with held-out prices using mean absolute error, an interpretable dollar-scale metric.",
        "mean absolute error on held-out houses", "absolute differences between predictions and true prices are averaged",
        "A measurement of how far estimates miss the answer key summarizes the quality of the predictions.",
        "mean_absolute_error(y_test, y_pred) averages the absolute difference between each observed and predicted price.",
        "MAE is expressed in the same price units as the target; lower values mean predictions are closer on average.", "A held-out error provides an honest estimate of how far the model may miss on new houses.",
        ("What does a lower MAE indicate?", "Predictions are closer to true prices", ["Predictions are closer to true prices", "More classes were created", "The test set is larger"], "Lower mean absolute error means smaller average absolute prediction mistakes."),
        ("What does y_test provide?", "The true held-out prices", ["The true held-out prices", "The model's coefficients", "The scaled training features"], "The held-out targets are the reference for calculating error."),
        ("Which evaluation rule is correct?", "Evaluation measures error without retraining", ["Evaluation measures error without retraining", "MAE updates the model automatically", "Prediction should use y_test as a feature"], "The metric describes the current predictions and does not change the model."),
        ("Which order completes the regression pipeline?", "predict test prices → compare with y_test → calculate MAE", ["predict test prices → compare with y_test → calculate MAE", "calculate MAE → fit → split", "compare labels → load → predict"], "Predictions and true held-out prices must exist before error can be calculated."),
        ("Why inspect individual absolute errors as well as MAE?", "Average error can hide unusually large or small misses", ["Average error can hide unusually large or small misses", "Individual errors retrain the model", "MAE makes targets unnecessary"], "The average is useful, but individual misses reveal the error distribution."),
        "MAE is meaningful when predictions are compared with prices from houses that did not train the model.",
    ),
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
    analogy_body = (
        f"Directly, {data['relationship']}. This relationship matters because it connects the data representation to the next pipeline step."
        if analogy_type == "concept" else str(data["analogy"])
    )
    sections = [
        GeneratedLessonSection(type="meaning", title="What this stage means", body=str(data["intro"]), items=[], code=None, language=None),
        GeneratedLessonSection(type=analogy_type, title="Connect the idea", body=analogy_body, items=[], code=None, language=None),
        GeneratedLessonSection(type="example", title="A small example", body=str(data["example"]), items=[], code=None, language=None),
        GeneratedLessonSection(type="result", title="What the code produces", body=str(data["result"]), items=[], code=None, language=None),
        GeneratedLessonSection(type="code", title="Try the code", body="Run the code and compare what it creates with the Result section above.", items=[], code=code.code, language=code.language),
        GeneratedLessonSection(type="why_it_matters", title="Why it matters", body=str(data["why"]), items=[], code=None, language=None),
    ]
    experiments = fixed_code_experiments(request.task, request.stage)
    return GeneratedLessonContent(
        title=str(data["title"]), introduction=str(data["intro"]), sections=sections,
        code_explanation=[f"{request.stage.replace('_', ' ')} — the code performs this pipeline stage."],
        try_this=[{
            "title": experiment.title, "find": experiment.find, "replace": experiment.replace,
            "expected_change": experiment.expected_change,
        } for experiment in experiments[:1]],
        key_takeaway=str(data["review"]),
    )


def _question(request: TutorGenerationRequest, data: dict[str, object]) -> TutorContent:
    action = request.action_type.value.rsplit(".", 1)[-1]
    operation_prompt, operation_correct, operation_options, operation_explanation = data["operation"]  # type: ignore[misc]
    variable_prompt, variable_correct, variable_options, variable_explanation = data["variable"]  # type: ignore[misc]
    boundary_parts = data["boundary"]  # type: ignore[assignment]
    boundary_prompt, boundary_correct, boundary_options = boundary_parts[:3]
    boundary_explanation = str(boundary_parts[3]) if len(boundary_parts) > 3 else str(boundary_correct)
    ordering_parts = data["ordering"]  # type: ignore[assignment]
    ordering_prompt, ordering_correct, ordering_options = ordering_parts[:3]
    ordering_explanation = str(ordering_parts[3]) if len(ordering_parts) > 3 else str(ordering_correct)
    transfer_parts = data["transfer"]  # type: ignore[assignment]
    transfer_prompt, transfer_correct, transfer_options = transfer_parts[:3]
    transfer_explanation = str(transfer_parts[3]) if len(transfer_parts) > 3 else str(transfer_correct)
    if action in {"concept_matching", "misconception_diagnosis", "concept_summary"}:
        prompt, correct, options, explanation = boundary_prompt, boundary_correct, boundary_options, boundary_explanation
    elif action in {"comparison_selection", "error_identification"}:
        prompt, correct, options, explanation = variable_prompt, variable_correct, variable_options, variable_explanation
    elif action in {"analogy_mapping", "novel_transfer"}:
        prompt, correct, options, explanation = transfer_prompt, transfer_correct, transfer_options, transfer_explanation
    elif action in {"pipeline_ordering"}:
        prompt, correct, options, explanation = ordering_prompt, ordering_correct, ordering_options, ordering_explanation
    else:
        prompt, correct, options, explanation = operation_prompt, operation_correct, operation_options, operation_explanation
    ordered_options = _stable_shuffle(list(options), f"{request.task}.{request.stage}.{request.step}.{action}")
    return TutorContent(
        question=str(prompt), options=ordered_options, expected_answer=str(correct),
        hint=f"Focus on the role of {data['target']} in this stage.", explanation=str(explanation),
        concepts_tested=list(request.learning_objectives) or [str(data["target"])],
    )


def authored_tutor_content(request: TutorGenerationRequest, instance_id: str | None = None) -> TutorGenerationResponse:
    data = _stage(request.task, request.stage)
    effective_request = request.model_copy(update={"task": "sentiment_classification" if request.task == "sentiment" else request.task})
    lesson = _lesson(effective_request, data)
    content = _question(request, data)
    return TutorGenerationResponse(
        content_instance_id=instance_id or f"authored-{uuid4()}", model="authored", prompt_version=AUTHORED_CONTENT_VERSION,
        code_version=fixed_lesson_code(effective_request.task, request.stage).version,
        dataset=dataset_for_task(effective_request.task).public(), lesson=lesson, content=content,
    )
