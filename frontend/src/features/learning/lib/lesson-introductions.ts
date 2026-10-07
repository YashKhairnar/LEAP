import { additionalTasks } from "@/features/learning/lib/additional-task-bank";
import { sentimentStages } from "@/features/learning/lib/question-bank";

export type TaskSlug = "sentiment" | "cnn" | "regression";
export type StageIntroduction = {
  id: string;
  label: string;
  title: string;
  summary: string;
  objectives: string[];
  input: string;
  output: string;
};
export type TaskIntroduction = {
  slug: TaskSlug;
  taskId: string;
  number: string;
  title: string;
  headline: string;
  description: string;
  purpose: string;
  datasetSummary: string;
  success: string;
  level: string;
  duration: string;
  question: string;
  objectives: string[];
  prerequisites: string[];
  tools: string[];
  pipeline: [string, string, string];
  stages: StageIntroduction[];
};

// Learner-facing outcomes are separate from the objective IDs used by the tutor.
const sentimentBriefs = [
  { objectives: ["Represent labeled reviews as rows in a pandas DataFrame.", "Check that each review stays paired with its sentiment label."], input: "Labeled review file", output: "A table of reviews and labels" },
  { objectives: ["Separate reviews and labels into matching training and test sets.", "Explain why held-out reviews are needed to check generalization."], input: "Reviews and sentiment labels", output: "Separate training and test sets" },
  { objectives: ["Explain how TF-IDF represents text as weighted numeric features.", "Fit the vocabulary on training reviews and reuse it for test reviews."], input: "Training and test text", output: "Aligned numeric feature matrices" },
  { objectives: ["Distinguish creating a classifier from fitting its parameters.", "Explain how training features and labels teach a sentiment boundary."], input: "Training features and labels", output: "A fitted sentiment classifier" },
  { objectives: ["Apply the fitted pipeline to reviews the model has not seen.", "Explain why predicting labels does not retrain the model."], input: "Held-out review features", output: "Predicted sentiment labels" },
  { objectives: ["Compare predicted sentiment with held-out labels.", "Interpret classification metrics and examine the model’s mistakes."], input: "Predictions and true labels", output: "An assessment of model performance" },
];

const cnnBriefs = [
  { objectives: ["Connect a row of 64 pixel values to a single 8 × 8 digit image.", "Explain the channel, height, and width dimensions of an image tensor."], input: "Labeled digit pixel records", output: "An image tensor dataset" },
  { objectives: ["Explain the purpose of separate training and test loaders.", "Describe how dividing 0–16 intensities by 16 rescales the input."], input: "Image tensors and digit labels", output: "Training and test loaders" },
  { objectives: ["Identify the roles of convolution, activation, pooling, and flattening.", "Connect ten output scores to the ten possible digit classes."], input: "Single-channel 8 × 8 images", output: "An untrained CNN architecture" },
  { objectives: ["Trace a training update from loss to gradients to new weights.", "Explain why only training batches should update the model."], input: "CNN and labeled training batches", output: "Learned network weights" },
  { objectives: ["Distinguish evaluation mode and gradient-free inference from training.", "Explain how the largest output score selects a predicted digit."], input: "Trained CNN and unseen images", output: "Predicted digit classes" },
  { objectives: ["Calculate accuracy from matching predictions and held-out labels.", "Interpret test accuracy as the fraction of unseen digits classified correctly."], input: "Predicted and true digits", output: "Held-out classification accuracy" },
];

const regressionBriefs = [
  { objectives: ["Identify property features and the price target in tabular data.", "Explain why rows without a target price cannot supply labeled training examples."], input: "Housing records", output: "Rows with usable target prices" },
  { objectives: ["Keep feature rows and prices aligned during a train/test split.", "Explain how reserving unseen houses supports a fair evaluation."], input: "Property features and prices", output: "Training and held-out houses" },
  { objectives: ["Explain why numeric features are placed on comparable scales.", "Fit scaling statistics on training data and reuse them on test data."], input: "Numeric feature partitions", output: "Consistently scaled features" },
  { objectives: ["Connect property features to a continuous price prediction.", "Distinguish constructing a regression model from learning its coefficients."], input: "Scaled training features and prices", output: "A fitted linear regression model" },
  { objectives: ["Apply a fitted model to scaled features for unseen houses.", "Explain why actual test prices are not inputs to prediction."], input: "Scaled held-out property features", output: "Estimated house prices" },
  { objectives: ["Explain mean absolute error in the same units as the target price.", "Interpret a lower MAE as smaller average prediction errors."], input: "Estimated and actual prices", output: "Mean absolute error" },
];

function additionalStages(slug: "cnn" | "regression", briefs: typeof cnnBriefs): StageIntroduction[] {
  return additionalTasks[slug].stages.map((stage, index) => ({
    id: stage.id, label: stage.label, title: stage.title, summary: stage.intro, ...briefs[index],
  }));
}

export const taskIntroductions: Record<TaskSlug, TaskIntroduction> = {
  sentiment: {
    slug: "sentiment", taskId: "sentiment_classification", number: "01",
    title: "Review Sentiment Classification", headline: "From written reviews to meaningful predictions.",
    description: "Build a complete text-classification pipeline that predicts whether a written review expresses positive or negative sentiment.",
    purpose: "Sentiment classification is a supervised-learning problem: the model studies reviews with known answers, learns patterns associated with each sentiment, and applies those patterns to new writing. The same prepare, train, predict, and evaluate workflow transfers to spam detection, support-ticket routing, and many other text tasks.",
    datasetSummary: "You will work with 3,000 labeled sentences from Amazon, IMDb, and Yelp. Each row contains review text, its source, and a known positive or negative label.",
    success: "You can trace an unseen review from raw text to numeric features, a predicted label, and an evidence-based evaluation of the classifier.",
    level: "Foundation", duration: "2–3 hours",
    question: "How can a model learn whether a review is positive or negative?",
    objectives: ["Prepare labeled reviews and turn text into numeric features.", "Train a classifier and use it to predict sentiment.", "Evaluate predictions on reviews kept separate from training."],
    prerequisites: ["Familiarity with variables, collections, and function or method calls", "Comfort reading short code examples and simple program output"],
    tools: ["Python", "pandas", "scikit-learn"], pipeline: ["Written reviews", "TF-IDF + classifier", "Positive or negative"],
    stages: sentimentStages.map((stage, index) => ({ id: stage.id, label: stage.shortLabel, title: stage.heading, summary: stage.intro, ...sentimentBriefs[index] })),
  },
  cnn: {
    slug: "cnn", taskId: "cnn", number: "02",
    title: additionalTasks.cnn.title, headline: "Give pixels a meaning. Teach a network to recognize digits.",
    description: "Build and train a convolutional neural network that recognizes handwritten digits from grids of pixel values.",
    purpose: "Image classification asks a model to choose a category from visual input. A CNN learns small local patterns such as edges and curves, combines them into stronger features, and uses those features to recognize a digit it has not seen before.",
    datasetSummary: "You will use 5,620 labeled handwritten digits from UCI Optical Digits. Every example is an 8 × 8 image stored as 64 intensity values with a label from 0 to 9.",
    success: "You can explain how an image moves through convolution, training, and inference, then judge the trained network using accuracy on held-out digits.",
    level: "Intermediate", duration: "3–4 hours",
    question: "How does a grid of pixel values become a recognizable digit?",
    objectives: ["Prepare image tensors and understand convolutional layers.", "Explain how training updates a network’s weights.", "Predict unseen digits and measure classification accuracy."],
    prerequisites: ["Basic arrays, method calls, and program flow", "An understanding of training data, test data, and labels"],
    tools: ["Python", "PyTorch", "UCI Optical Digits"], pipeline: ["8 × 8 digit images", "Convolutional network", "A digit from 0 to 9"],
    stages: additionalStages("cnn", cnnBriefs),
  },
  regression: {
    slug: "regression", taskId: "regression", number: "03",
    title: additionalTasks.regression.title, headline: "Turn property features into a price prediction.",
    description: "Build a regression pipeline that uses property features to estimate house prices and measures how close those estimates are.",
    purpose: "Regression predicts a continuous number instead of a category. The model learns how inputs such as size, age, bedrooms, and bathrooms relate to sale price, then estimates a value for a house that was kept out of training.",
    datasetSummary: "You will work with 2,930 property sales from Ames, Iowa, reduced to four explanatory features and the recorded sale price used as the target.",
    success: "You can produce prices for held-out houses without data leakage and interpret mean absolute error as the model’s typical prediction distance in price units.",
    level: "Foundation", duration: "2–3 hours",
    question: "How can we estimate a house price—and measure how far off we are?",
    objectives: ["Split and scale housing data without using test information.", "Train a regression model to predict numeric prices.", "Measure prediction error with mean absolute error."],
    prerequisites: ["Familiarity with variables, collections, and function or method calls", "Comfort reading a table of numeric values"],
    tools: ["Python", "pandas", "scikit-learn"], pipeline: ["Property features", "Linear regression", "An estimated price"],
    stages: additionalStages("regression", regressionBriefs),
  },
};
