type JavaExample = { code: string; explanation: string };

// Small Java snippets illustrate the idea; each declares the values it uses.
export const JAVA_ANALOGY_EXAMPLES: Record<string, JavaExample> = {
  "sentiment_classification.data_loading_and_preparation": {
    code: 'record Review(String text, String sentiment) {}\n\nList<Review> reviews = List.of(\n    new Review("The mic is great.", "positive"),\n    new Review("Doesn\'t hold charge.", "negative"));',
    explanation: "Each Review keeps its text and its label together. In pandas, one DataFrame row plays the role of one Review object.",
  },
  "sentiment_classification.train_test_split": {
    code: 'List<String> reviews = List.of("Great", "Slow", "Tasty", "Cold", "Good");\nList<String> training = reviews.subList(0, 4);\nList<String> test = reviews.subList(4, 5);',
    explanation: "Four examples are for learning and one is kept for testing. In the ML lesson, the split is random and keeps labels paired too.",
  },
  "sentiment_classification.tfidf_vectorization": {
    code: 'Map<String, Double> weights = new HashMap<>();\nweights.put("great", 0.8);\nweights.put("slow", 0.2);',
    explanation: "A Map pairs a key with a value. Here, word keys have numeric weights. TF-IDF learns word weights from training text.",
  },
  "sentiment_classification.model_training": {
    code: 'double weight = 0.5;\nweight = weight + 0.1;',
    explanation: "This changes a stored value. Training also changes stored weights, but computes those changes from examples and labels.",
  },
  "sentiment_classification.prediction": {
    code: 'double score = 0.8;\nString label = score > 0.5 ? "positive" : "negative";',
    explanation: "The stored rule produces a label without changing its values. A fitted classifier similarly applies what it learned.",
  },
  "sentiment_classification.evaluation": {
    code: 'int correct = 8;\nint total = 10;\ndouble accuracy = (double) correct / total;',
    explanation: "Eight correct answers out of ten give accuracy 0.8, or 80%.",
  },
  "cnn.load_images": {
    code: 'int[][] pixels = {{0, 16}, {8, 0}};\nint digitLabel = 7;',
    explanation: "A grid stores brightness values, and a label names the digit. This tiny 2 × 2 example illustrates the lesson's 8 × 8 images.",
  },
  "cnn.normalize_split": {
    code: 'int pixel = 12;\ndouble scaledPixel = pixel / 16.0;',
    explanation: "The brightness 12 becomes 0.75. Scaling changes the number range while keeping the image's meaning.",
  },
  "cnn.build_cnn": {
    code: 'double[] patch = {0, 16, 8};\ndouble[] filter = {0.1, 0.5, 0.2};\ndouble score = patch[0] * filter[0] + patch[1] * filter[1] + patch[2] * filter[2];',
    explanation: "This combines nearby values using weights. A convolution repeats that idea over image regions, with weights learned during training.",
  },
  "cnn.train_network": {
    code: 'double weight = 0.5;\ndouble gradient = 0.2;\ndouble learningRate = 0.1;\nweight = weight - learningRate * gradient;',
    explanation: "The gradient tells an update which direction to move. The optimizer applies updates like this across the network's weights.",
  },
  "cnn.classify_images": {
    code: 'double[] scores = {0.1, 0.8, 0.3};\nint best = 0;\nfor (int i = 1; i < scores.length; i++) {\n    if (scores[i] > scores[best]) best = i;\n}',
    explanation: "The largest score is at index 1. argmax does the same search; the digit model has ten scores instead of three.",
  },
  "cnn.evaluate_cnn": {
    code: 'int correct = 18;\nint total = 20;\ndouble accuracy = (double) correct / total;',
    explanation: "Eighteen matching digit labels out of twenty give 90% accuracy.",
  },
  "regression.prepare_housing_data": {
    code: 'double[][] houses = {{3, 1800, 325000}, {2, 1200, 240000}};',
    explanation: "Each example keeps bedrooms, size, and a price together. The lesson separates the input details from the price to predict.",
  },
  "regression.split_housing_data": {
    code: 'List<Integer> houseIds = List.of(1, 2, 3, 4, 5);\nList<Integer> training = houseIds.subList(0, 4);\nList<Integer> test = houseIds.subList(4, 5);',
    explanation: "The groups serve different purposes. The ML split chooses houses randomly and keeps their details and prices paired.",
  },
  "regression.scale_features": {
    code: 'double size = 1200;\ndouble trainingMean = 1500;\ndouble trainingStd = 300;\ndouble scaled = (size - trainingMean) / trainingStd;',
    explanation: "This produces −1: the size is one training standard deviation below the training average.",
  },
  "regression.train_regression": {
    code: 'double coefficient = 2.0;\ncoefficient = 2.2;',
    explanation: "Changing a coefficient changes a numeric rule. Regression learns such coefficients from training houses and their prices.",
  },
  "regression.predict_prices": {
    code: 'double size = 1500;\ndouble pricePerSquareFoot = 200;\ndouble estimatedPrice = size * pricePerSquareFoot;',
    explanation: "A stored rule estimates $300,000 without knowing the sale price. The lesson learns a rule using several features.",
  },
  "regression.evaluate_regression": {
    code: 'double[] errors = {Math.abs(200000 - 210000), Math.abs(300000 - 270000)};\ndouble mae = (errors[0] + errors[1]) / 2;',
    explanation: "The absolute errors are $10,000 and $30,000. MAE is their average: $20,000.",
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
