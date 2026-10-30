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
  example: {
    input: string;
    output: string;
    explanation: string;
  };
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
    description: "Teach a model to recognize positive and negative reviews, then check how well it handles reviews it has not seen.",
    purpose: "People can often tell whether a review is positive or negative by reading it. Here, you will teach a computer using reviews with known answers. The model is a program that learns patterns from those examples. Choosing a category like positive or negative is called classification.",
    datasetSummary: "Your dataset is a collection of 3,000 short review sentences from Amazon, IMDb, and Yelp. Each sentence comes with a label: the known answer, positive or negative.",
    success: "A small Python program that loads reviews, learns from examples, predicts sentiment for new reviews, and reports how often it is correct.",
    level: "Foundation", duration: "2–3 hours",
    question: "How can a computer recognize a positive review?",
    example: {
      input: 'A new review: “The food was delicious. I would come back.”',
      output: "Predicted category: positive",
      explanation: "This illustrates the task. A model uses what it learned from earlier reviews to choose a category for a new one. Its prediction can still be wrong.",
    },
    objectives: ["Explain what the review text and its label tell the model.", "Follow a review from text to a predicted category.", "Check predictions using reviews kept separate from training."],
    prerequisites: ["Familiarity with variables, collections, and function or method calls", "Comfort reading short code examples and simple program output"],
    tools: ["Python", "pandas", "scikit-learn"], pipeline: ["Review text", "Trained model", "Positive or negative"],
    stages: sentimentStages.map((stage, index) => ({ id: stage.id, label: stage.shortLabel, title: stage.heading, summary: stage.intro, ...sentimentBriefs[index] })),
  },
  cnn: {
    slug: "cnn", taskId: "cnn", number: "02",
    title: additionalTasks.cnn.title, headline: "Give pixels a meaning. Teach a network to recognize digits.",
    description: "Teach a neural network to recognize handwritten digits, then check its predictions on new images.",
    purpose: "Two people can write the same digit in very different ways. Rather than writing rules for every shape, you will train a convolutional neural network, or CNN, on labeled images. It learns useful visual patterns, such as parts of strokes and curves, to help choose a digit from 0 to 9.",
    datasetSummary: "Your dataset is a collection of 5,620 handwritten-digit images from UCI Optical Digits. Each image is a small 8 × 8 grid of brightness values, paired with the digit it shows.",
    success: "A small Python program that prepares image data, trains a CNN, predicts digits in new images, and counts how many predictions are correct.",
    level: "Intermediate", duration: "3–4 hours",
    question: "How can a computer recognize a handwritten digit?",
    example: {
      input: "A small grayscale image of a handwritten 7",
      output: "Predicted digit: 7",
      explanation: "The computer receives a grid of brightness numbers. The CNN uses learned patterns to choose a digit. Different handwriting can make the choice harder.",
    },
    objectives: ["Explain how numbers represent an image.", "Describe how a CNN learns from images with known digit labels.", "Check how often it recognizes new digits correctly."],
    prerequisites: ["Basic arrays, method calls, and program flow", "An understanding of training data, test data, and labels"],
    tools: ["Python", "PyTorch", "UCI Optical Digits"], pipeline: ["8 × 8 digit images", "Convolutional network", "A digit from 0 to 9"],
    stages: additionalStages("cnn", cnnBriefs),
  },
  regression: {
    slug: "regression", taskId: "regression", number: "03",
    title: additionalTasks.regression.title, headline: "Turn property features into a price prediction.",
    description: "Use details about a house to estimate its price, then measure how far the estimate is from the actual sale price.",
    purpose: "A larger house may cost more, but size is only one part of its price. You will train a model using past sales and details such as bedrooms, bathrooms, size, and age. Predicting a number, such as a price, is called regression. The goal is a useful estimate, not an exact price for every house.",
    datasetSummary: "Your dataset is a collection of 2,930 home sales in Ames, Iowa. Each record pairs four house details with its actual sale price.",
    success: "A small Python program that prepares house records, learns from past sales, estimates prices for new houses, and reports the average size of its errors.",
    level: "Foundation", duration: "2–3 hours",
    question: "How can a computer estimate a house price?",
    example: {
      input: "3 bedrooms · 2 bathrooms · 1,800 square feet · 20 years old",
      output: "An estimated sale price in dollars",
      explanation: "The house details are the inputs. The price is the number to predict. Later, you will compare estimated prices with actual sale prices to see how close they are.",
    },
    objectives: ["Identify the house details used to estimate price.", "Explain how a model learns a pricing rule from past sales.", "Describe prediction errors in dollars."],
    prerequisites: ["Familiarity with variables, collections, and function or method calls", "Comfort reading a table of numeric values"],
    tools: ["Python", "pandas", "scikit-learn"], pipeline: ["Property features", "Linear regression", "An estimated price"],
    stages: additionalStages("regression", regressionBriefs),
  },
};
