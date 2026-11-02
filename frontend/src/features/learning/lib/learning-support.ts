type JavaExample = { code: string; explanation: string };

// Small Java snippets illustrate the idea; each declares the values it uses.
export const JAVA_ANALOGY_EXAMPLES: Record<string, JavaExample> = {
  "sentiment_classification.data_loading_and_preparation": {
    code: 'record Review(String text, String sentiment) {}\n\nList<Review> reviews = List.of(\n    new Review("The mic is great.", "positive"),\n    new Review("Doesn\'t hold charge.", "negative"));',
    explanation: "Each Review keeps its text and its label together. In pandas, one DataFrame row plays the role of one Review object.",
  },
  "sentiment_classification.train_test_split": {
    code: "List<String> reviews = List.of(\"Great mic\", \"Too slow\", \"Loved it\", \"Broke fast\", \"Works well\");\nList<String> labels = List.of(\"positive\", \"negative\", \"positive\", \"negative\", \"positive\");\nint cut = 4; // the same cut for both lists\nList<String> testReviews = reviews.subList(cut, 5);\nList<String> testLabels = labels.subList(cut, 5);",
    explanation: "Cutting both lists at the same position keeps every review with its label. train_test_split does the same, but picks the test rows at random.",
  },
  "sentiment_classification.tfidf_vectorization": {
    code: "Map<String, Double> row = new HashMap<>(); // \"The mic is great.\"\nrow.put(\"mic\", 0.85);   // rare word: high weight\nrow.put(\"great\", 0.41);\nrow.put(\"is\", 0.28);\nrow.put(\"the\", 0.20);   // common word: low weight",
    explanation: "One review as word weights, using the real values from the lesson. Every vocabulary word not in the map counts as 0.",
  },
  "sentiment_classification.model_training": {
    code: "double[] weights = new double[4558]; // one per vocabulary word\ndouble bias = 0;\n// Before fit: all zeros, so the model knows nothing.\n// fit(...) fills the array from the 2,400 labeled reviews,\n// e.g. the entry for \"great\" becomes about +4.92.",
    explanation: "LogisticRegression() creates the empty fields; fit is the method that fills them. Positive entries push a review towards positive.",
  },
  "sentiment_classification.prediction": {
    code: "double score = bias;\nfor (Map.Entry<String, Double> word : row.entrySet()) {\n    score += weightOf(word.getKey()) * word.getValue();\n}\nString label = score > 0 ? \"positive\" : \"negative\";",
    explanation: "Prediction only reads the stored weights; it never changes them. A total score above 0 means positive.",
  },
  "sentiment_classification.evaluation": {
    code: "String[] predicted = {\"positive\", \"negative\", \"positive\", \"positive\"};\nString[] actual = {\"positive\", \"negative\", \"negative\", \"positive\"};\nint correct = 0;\nfor (int i = 0; i < actual.length; i++) {\n    if (predicted[i].equals(actual[i])) correct++;\n}\ndouble accuracy = (double) correct / actual.length; // 0.75",
    explanation: "Three of four match, so accuracy is 0.75. accuracy_score does the same comparison over all 600 test reviews.",
  },
  "cnn.load_images": {
    code: "int[] row = new int[64];        // one line of images.csv\nint[][] image = new int[8][8];\nfor (int i = 0; i < 64; i++) {\n    image[i / 8][i % 8] = row[i]; // 8 values per row\n}",
    explanation: "This folds 64 numbers into an 8 × 8 grid. reshape(-1, 1, 8, 8) does the same for every image at once, adding the single grayscale channel.",
  },
  "cnn.normalize_split": {
    code: "int total = 4496, batchSize = 128;\nint fullBatches = total / batchSize; // 35\nint lastBatch = total % batchSize;   // 16 images left over\ndouble scaled = 4 / 16.0;            // a pixel of 4 becomes 0.25",
    explanation: "Integer division and the remainder give the batch counts from the lesson. Dividing by 16.0 maps brightness onto 0–1.",
  },
  "cnn.build_cnn": {
    code: "double[] patch = {0, 16, 8};\ndouble[] filter = {0.1, 0.5, 0.2};\ndouble score = patch[0] * filter[0] + patch[1] * filter[1] + patch[2] * filter[2];",
    explanation: "This combines nearby values using weights. A convolution repeats that idea across the image with 3 × 3 patches, using weights learned in training.",
  },
  "cnn.train_network": {
    code: "double weight = 0.5;\ndouble gradient = 0.2;     // from loss.backward()\ndouble learningRate = 0.1;\nweight = weight - learningRate * gradient; // optimizer.step()",
    explanation: "The gradient says which way to move; the step moves the weight a little the other way. The optimizer does this for every weight, once per batch.",
  },
  "cnn.classify_images": {
    code: "double[] scores = {0.1, 0.8, 0.3};\nint best = 0;\nfor (int i = 1; i < scores.length; i++) {\n    if (scores[i] > scores[best]) best = i;\n}",
    explanation: "best ends up as 1, the position of the largest score. argmax does the same search; the digit model has ten scores instead of three.",
  },
  "cnn.evaluate_cnn": {
    code: "int[] predicted = {3, 7, 1, 8, 1};\nint[] actual = {3, 7, 7, 8, 1};\nint correct = 0;\nfor (int i = 0; i < actual.length; i++) {\n    if (predicted[i] == actual[i]) correct++;\n}\ndouble accuracy = (double) correct / actual.length; // 0.8",
    explanation: "Four of five digits match, so accuracy is 0.8. (y_pred == y_test).float().mean() does this for all 1,124 test images.",
  },
  "regression.prepare_housing_data": {
    code: "record Sale(int bedrooms, double bathrooms, int squareFeet, int ageYears, int price) {}\n\nSale first = new Sale(3, 2.0, 1656, 50, 215000);\ndouble[] x = {first.bedrooms(), first.bathrooms(), first.squareFeet(), first.ageYears()};\ndouble y = first.price(); // the target, never a feature",
    explanation: "The first house in the file, split the way the lesson splits X and y.",
  },
  "regression.split_housing_data": {
    code: "List<Integer> positions = new ArrayList<>(List.of(0, 1, 2, 3, 4));\nCollections.shuffle(positions, new Random(42));\n// Use the same positions to pick from BOTH features and prices.\nList<Integer> trainRows = positions.subList(0, 4);\nList<Integer> testRows = positions.subList(4, 5);",
    explanation: "One shuffled list of positions is used for features and prices alike, so every house keeps its own price.",
  },
  "regression.scale_features": {
    code: "double mean = 1500, spread = 505; // set once by fit, from training houses\ndouble scaled = (1656 - mean) / spread; // about +0.31, via transform",
    explanation: "fit sets the mean and spread once; transform reuses them for any house, training or test.",
  },
  "regression.train_regression": {
    code: "double intercept = 180000; // the price of an average house\ndouble[] coef = {5000, 9000, 40000, -12000}; // example values\ndouble[] x = {0, 0, 0, 1}; // average, except one spread older\ndouble price = intercept;\nfor (int i = 0; i < coef.length; i++) price += coef[i] * x[i]; // 168,000",
    explanation: "These are example numbers, not the real model's. fit is what chooses the intercept and coefficients from the training houses.",
  },
  "regression.predict_prices": {
    code: "double[] predicted = new double[586];\nfor (int i = 0; i < 586; i++) {\n    predicted[i] = priceOf(xTestScaled[i]); // reads coef, never changes it\n}",
    explanation: "One estimate per test house. The real prices in y_test are never passed in.",
  },
  "regression.evaluate_regression": {
    code: "double[] actual = {150000, 240000, 98000};\ndouble[] predicted = {162000, 225000, 101000};\ndouble total = 0;\nfor (int i = 0; i < actual.length; i++) total += Math.abs(actual[i] - predicted[i]);\ndouble mae = total / actual.length; // 10,000",
    explanation: "The same three houses as the worked example: errors of $12,000, $15,000 and $3,000 average to $10,000.",
  },
};

const BASIC_TERMS = "Features are input values. Labels or targets are the known answers.";
export function stageTerms(task: string, stage: string): string {
  if (stage === "load_images") return "A tensor is an array of numbers. A grayscale image uses one channel of brightness values. The label names the digit.";
  if (stage.includes("split") || stage === "normalize_split") return "Training data teaches the model. Test data is kept aside to check it. Held-out means kept aside.";
  if (stage === "tfidf_vectorization") return "A vector is a list of numbers. TF-IDF turns words into weighted numbers. Fit means learn from data.";
  if (stage === "scale_features") return "Scaling changes the number range of inputs. Fit learns the scaling rule; transform applies it.";
  if (stage === "train_network") return "Loss measures mistakes. A gradient guides changes to weights. The optimizer makes those changes.";
  if (stage === "build_cnn") return "A filter detects small patterns. Pooling makes a smaller grid. Flattening turns a grid into a list.";
  if (stage.includes("train") || stage === "model_training") return "Fit means train. Parameters, weights, and coefficients are numbers the model learns.";
  if (stage === "classify_images") return "Inference means prediction. argmax selects the largest score. Gradients guide training updates.";
  if (stage.includes("predict")) return "Prediction uses the learned model. Test inputs are new examples; their answers are kept aside.";
  if (stage.includes("evaluat")) return task === "regression" ? "Absolute error is the size of a mistake, ignoring its sign. MAE averages those sizes." : "Accuracy is the fraction of correct predictions. Held-out examples were kept aside during training.";
  return BASIC_TERMS;
}
