"""Authored end-of-task assessments. Bump VERSION when changing scored items."""

from dataclasses import dataclass

VERSION = "task_assessment_v1"


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


QUESTION_BANK: dict[str, tuple[AssessmentQuestion, ...]] = {
    "sentiment_classification": (
        AssessmentQuestion("sentiment-01", "data_loading_and_preparation", "Features and labels",
            "In our review dataset, which pairing supplies one labeled training example?",
            ("A review and its source website", "A review and its positive/negative sentiment", "Two reviews with similar lengths", "A row number and the total number of reviews"), 1,
            "The review is the input and its sentiment is the target. The website is metadata, not the sentiment label our classifier learns to predict."),
        AssessmentQuestion("sentiment-02", "train_test_split", "Generalization",
            "Why do we set aside test reviews before training the classifier?",
            ("To give the classifier extra labels while it learns", "To ensure every test prediction is correct", "To remove all unfamiliar words from the dataset", "To estimate performance on reviews not used to learn the model"), 3,
            "Held-out reviews help estimate generalization. Testing on the training reviews can give an overly optimistic view because the model already learned from them."),
        AssessmentQuestion("sentiment-03", "train_test_split", "Stratified splitting",
            "What is the purpose of stratify=df[\"sentiment\"] in our train/test split?",
            ("Keep approximately the same class proportions in both sets", "Sort reviews from most positive to most negative", "Put all positive reviews into training and all negative reviews into testing", "Make both sets contain exactly the same reviews"), 0,
            "Stratification preserves the approximate positive/negative proportions. It does not duplicate reviews or split the classes into separate sets."),
        AssessmentQuestion("sentiment-04", "tfidf_vectorization", "Text representation",
            "Why do we apply TF-IDF before fitting LogisticRegression?",
            ("It supplies the correct sentiment for each test review", "It translates each review into a Java object", "It turns text into numeric word features the classifier can use", "It makes every review contain the same words"), 2,
            "The classifier works on numeric features. TF-IDF creates weighted word features; it neither supplies sentiment labels nor rewrites every review to use identical words."),
        AssessmentQuestion("sentiment-05", "tfidf_vectorization", "Data leakage",
            "A student fits the vectorizer on all reviews, then splits the resulting matrix. What should change?",
            ("Keep it: preprocessing cannot use test information", "Split the text first, fit on training text, and only transform test text", "Fit another independent vocabulary on the test text", "Use test labels to choose which words to keep"), 1,
            "Vocabulary and IDF weights must be learned only from training text. Using all reviews lets held-out information influence preprocessing; fitting an independent test vocabulary also breaks feature alignment."),
        AssessmentQuestion("sentiment-06", "model_training", "Fitting a classifier",
            "Which statement correctly distinguishes the two lines below?",
            ("The first constructs the classifier; the second learns its parameters from training features and labels", "Both lines make predictions on the test set", "The first learns the parameters; the second only displays them", "The second creates the sentiment labels without using y_train"), 0,
            "Constructing a model sets up its configuration. fit() uses the training feature matrix and its paired labels to learn the classification boundary.",
            "model = LogisticRegression(max_iter=1000, random_state=42)\nmodel.fit(X_train_tfidf, y_train)"),
        AssessmentQuestion("sentiment-07", "prediction", "Predicting new reviews",
            "How should we classify one new review after the pipeline has been trained?",
            ("Fit a new vectorizer on that review, then pass its features to the existing model", "Pass the known sentiment to model.predict()", "Train the classifier again using the review as its own label", "Transform the review with the fitted vectorizer, then call the fitted model's predict()"), 3,
            "The fitted vectorizer preserves the training feature meanings and order. predict() applies the learned model without needing a label or retraining."),
        AssessmentQuestion("sentiment-08", "prediction", "Prediction versus display",
            "If [:10] is changed to [:3], what changes?",
            ("Only three test reviews are passed to model.predict()", "The classifier is retrained on three reviews", "Only three predictions are printed; y_pred still contains predictions for all test reviews", "The test set is permanently shortened to three reviews"), 2,
            "predict() runs before the loop and receives the full test matrix. The slice only limits which review/prediction pairs the loop displays.",
            'y_pred = model.predict(X_test_tfidf)\nfor review, prediction in list(zip(X_test, y_pred))[:10]:\n    print(f"{prediction}: {review}")'),
        AssessmentQuestion("sentiment-09", "evaluation", "Interpreting accuracy",
            "The classifier predicts 48 of 60 held-out review labels correctly. What does its accuracy mean?",
            ("80% of these test reviews were classified correctly", "Every future prediction has a guaranteed 80% chance of being correct", "80% of the reviews contain positive words", "The model has learned 80% of all possible words"), 0,
            "Accuracy is correct predictions divided by total predictions: 48/60 = 0.80. It describes this test set, not a guarantee for each future review."),
        AssessmentQuestion("sentiment-10", "evaluation", "Looking beyond accuracy",
            "On a new test sample, 90 reviews are positive and 10 are negative. A classifier always predicts positive and gets 90% accuracy. What is the best conclusion?",
            ("It identifies both classes well because accuracy is high", "We should remove the negative reviews before scoring", "Its negative-class recall must also be 90%", "Accuracy alone hides its failure to identify negative reviews; inspect per-class recall and F1"), 3,
            "All ten negative reviews are missed, so negative-class recall is zero. The classification report reveals this failure even though the majority class makes overall accuracy look high."),
    ),
    "regression": (
        AssessmentQuestion("regression-01", "prepare_housing_data", "Features and target",
            "Which setup matches our house-price prediction task?",
            ("Use price as an input to predict the row number", "Use the train/test label as the price target", "Use bedrooms, bathrooms, square feet, and age as inputs; price is the target", "Use only the price column as both input and target"), 2,
            "Property characteristics are features available when estimating a price. The recorded price is the target; using it as an input would reveal the answer."),
        AssessmentQuestion("regression-02", "prepare_housing_data", "Missing data",
            "In this preparation code, what happens to a row whose bathroom value is missing?",
            ("Its missing value is automatically replaced by zero", "The row is removed before X and y are created", "Only its price is removed, leaving X and y with different lengths", "The model fills in its bathroom value during read_csv()"), 1,
            "dropna() without a subset removes rows with any missing value. Creating X and y from the same remaining DataFrame keeps features and prices aligned.",
            'df = pd.read_csv("houses.csv").dropna()\nX = df[["bedrooms", "bathrooms", "square_feet", "age_years"]]\ny = df["price"]'),
        AssessmentQuestion("regression-03", "split_housing_data", "Paired splitting",
            "Why do we pass X and y together to train_test_split()?",
            ("To make each house's features stay paired with its actual price in both partitions", "To sort all houses by price", "To make the training prices equal to the predicted prices", "To put feature columns in training and the price column in testing"), 0,
            "The split applies matching row selections to X and y. Separately shuffling features and targets can teach the model incorrect house/price relationships."),
        AssessmentQuestion("regression-04", "scale_features", "Preprocessing without leakage",
            "Which scaling procedure gives a fair test of the housing model?",
            ("Fit the scaler on all houses to obtain the most complete statistics", "Fit separate scalers on training houses and test houses", "Fit the scaler on test prices", "Fit the scaler on training features and reuse it to transform test features"), 3,
            "Training means and standard deviations define the transformation. Reusing them keeps feature meanings consistent without letting the held-out houses influence preprocessing."),
        AssessmentQuestion("regression-05", "scale_features", "Interpreting standardized values",
            "After StandardScaler, a house has a negative square_feet feature. What does that mean?",
            ("The house has a physically negative floor area", "Its floor area is below the training-set average", "Its predicted price must be negative", "The scaler could not read its floor area"), 1,
            "StandardScaler subtracts the training mean and divides by the training standard deviation. A below-average original value becomes negative; its physical area is still positive."),
        AssessmentQuestion("regression-06", "train_regression", "Learning coefficients",
            "What does model.fit(X_train_scaled, y_train) learn in our regression task?",
            ("The exact prices of every possible future house", "A positive/negative class label for every feature", "Coefficients and an intercept that relate the training features to numeric prices", "The test-set mean and standard deviation"), 2,
            "Linear regression learns coefficients and an intercept from training examples. These parameters produce continuous price estimates; it does not memorize all future prices or learn the test scaler."),
        AssessmentQuestion("regression-07", "predict_prices", "Inference inputs",
            "A new house has the four required feature values but no known sale price. What is the correct next step?",
            ("Keep the training feature order, transform with the fitted scaler, and predict with the fitted model", "Append a guessed price to the input before predicting", "Fit a new scaler on this one house and use its output", "Wait for its actual sale price because prediction requires y_test"), 0,
            "Inference needs feature values, not the target. Keeping their order and using the training scaler makes the new input compatible with the fitted model."),
        AssessmentQuestion("regression-08", "evaluate_regression", "Calculating MAE",
            "For two houses, actual prices are $200,000 and $300,000; predicted prices are $210,000 and $270,000. What is the mean absolute error?",
            ("−$10,000", "$40,000", "$10,000", "$20,000"), 3,
            "The absolute errors are $10,000 and $30,000. Their average is ($10,000 + $30,000)/2 = $20,000. Taking absolute values prevents over- and underestimates from cancelling."),
        AssessmentQuestion("regression-09", "evaluate_regression", "Interpreting MAE",
            "A model has a held-out MAE of $18,000. Which interpretation is correct?",
            ("Its price accuracy is 18%", "Every house prediction is exactly $18,000 too high", "Its average absolute price error on that test set is $18,000; individual errors can be larger or smaller", "No prediction can be more than $18,000 away from the actual price"), 2,
            "MAE is an average magnitude of error in the target's units. It is neither a percentage, a signed bias, nor a maximum error bound."),
        AssessmentQuestion("regression-10", "evaluate_regression", "Comparing models fairly",
            "Two models use the same features, the same held-out houses, and no test data during training. Model A has MAE $15,000; model B has MAE $22,000. What does this support?",
            ("B has smaller errors because its MAE is larger", "A has the smaller average absolute error on this held-out set", "A is guaranteed to be better on every future house", "The models cannot be compared because regression has no accuracy score"), 1,
            "Lower MAE means smaller average absolute error on the same evaluation set. This supports A on that set, but does not guarantee it is better for every individual or future house."),
    ),
    "cnn": (
        AssessmentQuestion("cnn-01", "load_images", "Image tensor shape",
            "Our image array has shape (N, 1, 8, 8). What do these dimensions represent?",
            ("Number of images, number of classes, height, width", "Number of labels, height, width, number of training passes", "Number of pixels, number of images, number of classes, number of channels", "Number of images, one grayscale channel, height, width"), 3,
            "PyTorch convolution expects batch, channels, height, width. Each record contains one grayscale 8×8 image; the 1 is a channel count, not a class count."),
        AssessmentQuestion("cnn-02", "normalize_split", "Input normalization",
            "Our pixels range from 0 to 16. Why do we divide image batches by 16.0 during both training and prediction?",
            ("To consistently rescale pixel intensities to 0–1", "To reduce each image from 8×8 pixels to 4×4 pixels", "To change digit labels from 0–9 into probabilities", "To make every image have the same intensity"), 0,
            "Division rescales intensity values without changing image shape or digit labels. Prediction must use the same input scaling that the network saw during training."),
        AssessmentQuestion("cnn-03", "normalize_split", "Mini-batches",
            "What does batch_size=128 in the training DataLoader control?",
            ("The total number of images retained in the dataset", "The number of digit classes the CNN can predict", "The number of images processed together in a full training batch", "The number of times every image is used in one pass"), 2,
            "The loader groups training examples into batches of up to 128. It does not discard the rest of the dataset; the final batch may be smaller."),
        AssessmentQuestion("cnn-04", "build_cnn", "Convolution",
            "What is the role of the 3×3 filters in nn.Conv2d(1, 16, kernel_size=3, padding=1)?",
            ("Assign the correct digit label before training starts", "Learn local image patterns with filters reused across spatial positions", "Shuffle the training and test images", "Calculate the final classification accuracy"), 1,
            "Convolution learns filters that respond to local pixel patterns, such as parts of strokes. The filters are reused across the image; their weights are learned during training."),
        AssessmentQuestion("cnn-05", "build_cnn", "Pooling and flattening",
            "A batch has shape (B, 16, 8, 8) just before MaxPool2d(2). How many values per image enter the linear layer after pooling and flattening?",
            ("256, because pooling gives 16×4×4 and flattening puts those values in one vector", "10, because there are ten digit classes", "64, because the original image contains 64 pixels", "1,024, because pooling leaves the height and width unchanged"), 0,
            "The 2×2 pooling operation halves both spatial dimensions to 4×4 while keeping 16 channels. Flattening produces 16×4×4 = 256 values per image."),
        AssessmentQuestion("cnn-06", "build_cnn", "Output scores",
            "Why does the final layer use nn.Linear(16 * 4 * 4, 10)?",
            ("To train on exactly ten images", "To produce a ten-pixel image", "To guarantee that ten predictions are correct", "To produce one score for each possible digit, 0 through 9"), 3,
            "Each of the ten outputs corresponds to a digit class. These are scores, not a guarantee of correctness or ten new image pixels."),
        AssessmentQuestion("cnn-07", "train_network", "Gradients and weight updates",
            "Which statement correctly explains the training steps below?",
            ("backward() makes predictions; step() creates the labels", "zero_grad() clears old gradients, backward() computes new gradients, and step() updates weights", "zero_grad() sets every network weight permanently to zero", "The three calls only calculate test accuracy and never change weights"), 1,
            "Gradients accumulate unless cleared. backward() calculates how the loss changes with the weights; the optimizer uses those gradients in step() to update the weights.",
            "optimizer.zero_grad()\nloss = loss_fn(model(images_batch / 16.0), labels_batch)\nloss.backward()\noptimizer.step()"),
        AssessmentQuestion("cnn-08", "classify_images", "Inference versus training",
            "Which statement about model.eval() and torch.no_grad() is correct?",
            ("They retrain the network using test labels", "They erase the learned weights before making predictions", "eval() selects evaluation behavior; no_grad() disables gradient tracking for inference", "They guarantee that every test image is classified correctly"), 2,
            "These calls prepare inference without learning from test batches. They serve different roles and neither updates the weights nor guarantees correct predictions. In this CNN, the listed layers have no train/eval-specific behavior, but no_grad() still avoids tracking gradients."),
        AssessmentQuestion("cnn-09", "classify_images", "Selecting a class",
            "For one image, the ten output scores are [0.1, −0.2, 0.3, 2.4, 0.0, 0.5, −0.1, 0.2, 0.4, 0.6]. What does argmax select?",
            ("Digit 2, because it is closest to the largest score", "Digit 9, because it is the last output", "Digit 4, because 2.4 is the fourth value and digit numbering starts at 1", "Digit 3, because the largest score is at index 3"), 3,
            "argmax returns the index of the largest score, not the score itself. The outputs correspond to digits 0–9, so the fourth value is at index 3 and predicts digit 3."),
        AssessmentQuestion("cnn-10", "evaluate_cnn", "Held-out accuracy",
            "A trained CNN correctly labels 85 of 100 held-out digit images. What can we conclude?",
            ("The network is 85% confident in each individual prediction", "Its test accuracy is 85%; this estimates performance on similar unseen images, not a guarantee for all handwriting", "The remaining 15 images must have incorrect labels", "Training for another pass will definitely give 100% accuracy"), 1,
            "Accuracy is the fraction of matching predicted and true labels: 85/100. It describes this held-out sample; different handwriting or image conditions can lead to different performance."),
    ),
}


def assessment_task(task: str) -> str:
    task = "sentiment_classification" if task == "sentiment" else task
    if task not in QUESTION_BANK:
        raise ValueError("Unknown assessment task")
    return task
