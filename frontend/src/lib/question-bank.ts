import { INSTRUCTIONAL_ACTIONS, type InstructionalActionType, type InstructionalStep } from "./instructional-actions";

export type StepId = InstructionalStep;

export type QuestionItem = {
  id: string;
  step: StepId;
  actionType: InstructionalActionType;
  typeLabel: string;
  prompt: string;
  options: string[];
  correctAnswer: string;
  explanation: string;
  misconception: string;
  learningObjectives?: string[];
};

export type StageDefinition = {
  id: string;
  shortLabel: string;
  heading: string;
  intro: string;
  familiar: string;
  target: string;
  relationship: string;
  pythonCode: string;
  operation: { prompt: string; correct: string; options: string[]; explanation: string };
  outcome: { prompt: string; correct: string; options: string[]; explanation: string };
  variable: { prompt: string; correct: string; options: string[]; explanation: string };
  boundary: { correct: string; options: string[] };
  ordering: { correct: string; options: string[] };
  transfer: { prompt: string; correct: string; options: string[] };
  analogy: string;
  reviewStatement: string;
  misconception: string;
  objectives: string[];
};

export const sentimentStages: StageDefinition[] = [
  {
    id: "data_loading_and_preparation", shortLabel: "Prepare data", heading: "From Java objects to a dataset",
    intro: "Load labeled reviews and confirm that every text remains paired with its sentiment.", familiar: "An ArrayList of Review objects", target: "A pandas DataFrame of labeled rows", relationship: "one object maps to one row",
    pythonCode: 'import pandas as pd\n\ndf = pd.read_csv("reviews.csv")\nprint(df.head())\nprint("Rows:", len(df))',
    operation: { prompt: 'Complete: df = pd.____("reviews.csv")', correct: "read_csv", options: ["read_csv", "fit", "predict"], explanation: "read_csv loads the file into a DataFrame." },
    outcome: { prompt: "A displayed DataFrame has three rows. What does len(df) return?", correct: "3", options: ["1", "2", "3"], explanation: "len(df) returns the number of rows." },
    variable: { prompt: "What does df represent?", correct: "The complete review dataset", options: ["The complete review dataset", "One sentiment label", "A trained model"], explanation: "df contains all loaded examples and labels." },
    boundary: { correct: "The data is loaded, but no model is trained", options: ["The data is loaded, but no model is trained", "The classifier is already trained", "The predictions are evaluated"] },
    ordering: { correct: "read_csv → split → fit", options: ["read_csv → split → fit", "fit → read_csv → split", "predict → fit → read_csv"] },
    transfer: { prompt: "In a support-ticket dataset, what would one row represent?", correct: "One labeled support ticket", options: ["One labeled support ticket", "Every company ticket", "The trained classifier"] },
    analogy: "A patient file keeps one patient paired with a diagnosis; a dataset row keeps one review paired with its label.", reviewStatement: "The information stays paired while pandas changes how the complete collection is represented.", misconception: "loading_equals_training", objectives: ["pandas_data_loading", "labeled_example_representation"]
  },
  {
    id: "train_test_split", shortLabel: "Split data", heading: "Separate learning from testing",
    intro: "Reserve unseen reviews so evaluation measures generalization rather than memorization.", familiar: "Dividing examples into two Java lists", target: "Training and test partitions", relationship: "one collection becomes two purpose-specific subsets",
    pythonCode: "from sklearn.model_selection import train_test_split\n\nX_train, X_test, y_train, y_test = train_test_split(\n    df['text'], df['sentiment'], test_size=0.2, random_state=42\n)",
    operation: { prompt: "Which function creates training and test partitions?", correct: "train_test_split", options: ["train_test_split", "read_csv", "predict"], explanation: "train_test_split separates features and labels into training and held-out sets." },
    outcome: { prompt: "With 100 reviews and test_size=0.2, approximately how many are test reviews?", correct: "20", options: ["20", "50", "80"], explanation: "Twenty percent of 100 is 20." },
    variable: { prompt: "What does X_test contain?", correct: "Held-out review text", options: ["Held-out review text", "Training labels", "Model predictions"], explanation: "X_test contains input text reserved for later evaluation." },
    boundary: { correct: "Test reviews must remain unseen during training", options: ["Test reviews must remain unseen during training", "Test reviews should be copied into training", "Splitting trains the model"] },
    ordering: { correct: "load → split → vectorize", options: ["load → split → vectorize", "vectorize → evaluate → load", "predict → split → load"] },
    transfer: { prompt: "Why split a house-price dataset?", correct: "To test on homes not used for learning", options: ["To test on homes not used for learning", "To remove all prices", "To duplicate every home"] },
    analogy: "A practice exam is used to learn; a separate final exam checks whether that learning transfers.", reviewStatement: "Training data teaches the model; held-out test data measures generalization.", misconception: "test_data_leakage", objectives: ["train_test_separation", "generalization"]
  },
  {
    id: "tfidf_vectorization", shortLabel: "TF-IDF", heading: "Turn language into numeric features",
    intro: "Convert review text into vectors whose values reflect informative terms.", familiar: "A Java Map<String, Double> of term weights", target: "A TF-IDF feature matrix", relationship: "each review becomes a numeric vector",
    pythonCode: "from sklearn.feature_extraction.text import TfidfVectorizer\n\nvectorizer = TfidfVectorizer()\nX_train_tfidf = vectorizer.fit_transform(X_train)\nX_test_tfidf = vectorizer.transform(X_test)",
    operation: { prompt: "Which call learns the vocabulary and transforms training text?", correct: "fit_transform(X_train)", options: ["fit_transform(X_train)", "transform(y_train)", "predict(X_train)"], explanation: "fit_transform learns TF-IDF statistics from training text and creates its matrix." },
    outcome: { prompt: "What does one row of X_train_tfidf represent?", correct: "One review as numeric term weights", options: ["One review as numeric term weights", "One sentiment label", "One trained classifier"], explanation: "Each matrix row is the numeric representation of one review." },
    variable: { prompt: "What does vectorizer store after fitting?", correct: "Training vocabulary and term statistics", options: ["Training vocabulary and term statistics", "Predicted sentiments", "Test labels"] , explanation: "The fitted vectorizer stores vocabulary and weighting information." },
    boundary: { correct: "Fit on training text; only transform test text", options: ["Fit on training text; only transform test text", "Fit separately on test text", "TF-IDF directly predicts sentiment"] },
    ordering: { correct: "split → fit_transform train → transform test", options: ["split → fit_transform train → transform test", "transform test → split → load", "predict → fit_transform → split"] },
    transfer: { prompt: "For spam detection, what does TF-IDF produce?", correct: "Numeric vectors for email text", options: ["Numeric vectors for email text", "Final spam decisions", "New email labels"] },
    analogy: "A weighted index emphasizes distinctive words rather than treating every word as equally informative.", reviewStatement: "TF-IDF creates model-ready numbers without using test data to learn the vocabulary.", misconception: "vectorizer_data_leakage", objectives: ["tfidf_representation", "fit_transform_boundary"]
  },
  {
    id: "model_training", shortLabel: "Train model", heading: "Learn the sentiment boundary",
    intro: "Fit logistic regression on training vectors and their known sentiment labels.", familiar: "A Java method updating an object's internal fields", target: "A fitted LogisticRegression model", relationship: "fit changes model parameters using examples",
    pythonCode: "from sklearn.linear_model import LogisticRegression\n\nmodel = LogisticRegression(max_iter=1000)\nmodel.fit(X_train_tfidf, y_train)",
    operation: { prompt: "Which line actually trains the classifier?", correct: "model.fit(X_train_tfidf, y_train)", options: ["model.fit(X_train_tfidf, y_train)", "LogisticRegression()", "model.predict(X_test_tfidf)"], explanation: "fit uses training features and labels to learn model parameters." },
    outcome: { prompt: "What changes when fit() succeeds?", correct: "The model's learned parameters", options: ["The model's learned parameters", "The original review text", "The test labels"] , explanation: "Training estimates parameters that connect features to sentiment." },
    variable: { prompt: "What does y_train provide during fitting?", correct: "Known sentiment labels", options: ["Known sentiment labels", "Unseen review vectors", "Accuracy scores"] , explanation: "The labels tell supervised learning which outcomes correspond to training examples." },
    boundary: { correct: "Constructing a model is not the same as fitting it", options: ["Constructing a model is not the same as fitting it", "predict trains the model", "fit should use test labels"] },
    ordering: { correct: "vectorize train → fit model → predict test", options: ["vectorize train → fit model → predict test", "predict test → fit model → split", "evaluate → fit → load"] },
    transfer: { prompt: "What would fit() learn in a spam classifier?", correct: "Parameters connecting email features to spam labels", options: ["Parameters connecting email features to spam labels", "A new CSV file", "The test-set answers"] },
    analogy: "Training adjusts the model like practice with answer feedback adjusts a student's strategy.", reviewStatement: "The classifier learns only when fit receives training features paired with training labels.", misconception: "construction_equals_training", objectives: ["supervised_model_fit", "training_parameter_update"]
  },
  {
    id: "prediction", shortLabel: "Predict", heading: "Apply learning to unseen reviews",
    intro: "Use the fitted classifier to produce sentiment labels for held-out feature vectors.", familiar: "Calling a Java object's method after its fields are initialized", target: "Calling predict on a fitted model", relationship: "stored parameters determine a new output",
    pythonCode: "y_pred = model.predict(X_test_tfidf)\n\nfor text, label in zip(X_test, y_pred):\n    print(label, text)",
    operation: { prompt: "Which call produces labels for held-out reviews?", correct: "model.predict(X_test_tfidf)", options: ["model.predict(X_test_tfidf)", "model.fit(X_test_tfidf, y_test)", "vectorizer.fit(X_test)"] , explanation: "predict applies the fitted classifier to test vectors." },
    outcome: { prompt: "What does y_pred contain?", correct: "Predicted sentiment labels", options: ["Predicted sentiment labels", "Original training reviews", "TF-IDF vocabulary"] , explanation: "Each element is the model's predicted class for one test review." },
    variable: { prompt: "Why must X_test_tfidf use the training vectorizer?", correct: "Its feature columns must match training", options: ["Its feature columns must match training", "It needs new labels", "It retrains the model"] , explanation: "The model expects the same feature meaning and ordering used during fitting." },
    boundary: { correct: "Prediction applies learned parameters without updating them", options: ["Prediction applies learned parameters without updating them", "Prediction requires y_test as input", "Prediction retrains TF-IDF"] },
    ordering: { correct: "fit vectorizer → fit model → predict", options: ["fit vectorizer → fit model → predict", "predict → fit model → vectorize", "evaluate → predict → train"] },
    transfer: { prompt: "For a new movie review, what should the pipeline return?", correct: "A predicted sentiment label", options: ["A predicted sentiment label", "A known training label", "A new model vocabulary"] },
    analogy: "After learning a rule from worked examples, you apply it to a new case without looking at its answer.", reviewStatement: "Prediction uses the frozen training pipeline to assign labels to unseen examples.", misconception: "prediction_retrains_model", objectives: ["held_out_prediction", "feature_alignment"]
  },
  {
    id: "evaluation", shortLabel: "Evaluate", heading: "Measure performance honestly",
    intro: "Compare predictions with held-out labels to quantify what the classifier gets right and wrong.", familiar: "Comparing Java method output with expected values in a test", target: "Classification metrics on y_test and y_pred", relationship: "actual and predicted values are compared",
    pythonCode: "from sklearn.metrics import accuracy_score, classification_report\n\naccuracy = accuracy_score(y_test, y_pred)\nprint(accuracy)\nprint(classification_report(y_test, y_pred))",
    operation: { prompt: "Which call computes the fraction of correct predictions?", correct: "accuracy_score(y_test, y_pred)", options: ["accuracy_score(y_test, y_pred)", "model.fit(y_test, y_pred)", "vectorizer.transform(y_pred)"] , explanation: "Accuracy compares true and predicted labels and returns the correct fraction." },
    outcome: { prompt: "What does accuracy = 0.80 mean?", correct: "80% of evaluated labels were correct", options: ["80% of evaluated labels were correct", "The model trained for 80 epochs", "There were 80 reviews"] , explanation: "Accuracy is the proportion of evaluated examples classified correctly." },
    variable: { prompt: "What is y_test during evaluation?", correct: "The true held-out labels", options: ["The true held-out labels", "The model predictions", "The fitted vocabulary"] , explanation: "y_test provides the answers used only after predictions are made." },
    boundary: { correct: "Evaluation measures performance; it should not retrain the model", options: ["Evaluation measures performance; it should not retrain the model", "Accuracy should be computed on training labels only", "A report creates new predictions"] },
    ordering: { correct: "predict test → compare with y_test → report metrics", options: ["predict test → compare with y_test → report metrics", "report metrics → train → split", "compare labels → load → predict"] },
    transfer: { prompt: "Why inspect precision and recall as well as accuracy?", correct: "Different error types can matter differently", options: ["Different error types can matter differently", "They retrain the classifier", "They replace test data"] },
    analogy: "A test score summarizes results, while an error breakdown reveals which kinds of questions caused difficulty.", reviewStatement: "Honest evaluation compares unseen predictions with withheld truth and examines more than one metric.", misconception: "evaluation_equals_training", objectives: ["held_out_evaluation", "classification_metrics"]
  },
];

function buildQuestionBank(stage: StageDefinition): Record<StepId, QuestionItem[]> {
  const q = (id: string, step: StepId, index: number, typeLabel: string, prompt: string, options: string[], correctAnswer: string, explanation: string, misconception = stage.misconception): QuestionItem => ({ id: `${stage.id}.${id}`, step, actionType: INSTRUCTIONAL_ACTIONS[step][index], typeLabel, prompt, options, correctAnswer, explanation, misconception, learningObjectives: stage.objectives });
  return {
    activate: [
      q("a-concept", "activate", 0, "Java concept", `Which familiar programming idea best prepares you for ${stage.target}?`, [stage.familiar, "A random number generator", "A UI color"], stage.familiar, `${stage.familiar} provides the reusable structure for this stage.`),
      q("a-output", "activate", 1, "Output prediction", stage.outcome.prompt, stage.outcome.options, stage.outcome.correct, stage.outcome.explanation),
      q("a-explain", "activate", 2, "Code explanation", `Why is ${stage.familiar} relevant here?`, [stage.relationship, "It removes every label", "It evaluates the final model"], stage.relationship, `The key connection is that ${stage.relationship}.`),
    ],
    connect: [
      q("c-match", "connect", 0, "Concept matching", `${stage.familiar} maps most directly to what?`, [stage.target, "An unrelated chart", "A password"], stage.target, `${stage.familiar} transfers to ${stage.target}.`),
      q("c-compare", "connect", 1, "Comparison", `Which statement best connects the familiar and new representations?`, [stage.relationship, "They have no shared structure", "Both automatically evaluate accuracy"], stage.relationship, `They connect because ${stage.relationship}.`),
      q("c-analogy", "connect", 2, "Analogy mapping", `What is the main point of this analogy: ${stage.analogy}`, [stage.relationship, "Training and testing are identical", "Labels are unnecessary"], stage.relationship, `The analogy highlights that ${stage.relationship}.`),
    ],
    implement: [
      q("i-complete", "implement", 0, "Code completion", stage.operation.prompt, stage.operation.options, stage.operation.correct, stage.operation.explanation),
      q("i-output", "implement", 1, "Output prediction", stage.outcome.prompt, stage.outcome.options, stage.outcome.correct, stage.outcome.explanation),
      q("i-variable", "implement", 2, "Variable purpose", stage.variable.prompt, stage.variable.options, stage.variable.correct, stage.variable.explanation),
    ],
    learn: [
      q("l-transfer", "learn", 0, "Transfer or new", `What transfers into this stage?`, [stage.relationship, "The final accuracy value", "The student's password"], stage.relationship, `The transferable relationship is that ${stage.relationship}.`),
      q("l-difference", "learn", 1, "Difference", `What is the new ML-specific idea?`, [stage.target, stage.familiar, "A page layout"], stage.target, `${stage.target} is the new representation or operation.`),
      q("l-boundary", "learn", 2, "Concept boundary", "Which boundary is correct?", stage.boundary.options, stage.boundary.correct, stage.boundary.correct),
    ],
    practice: [
      q("p-diagnose", "practice", 0, "Misconception check", `A learner confuses this stage with another operation. Which correction is accurate?`, stage.boundary.options, stage.boundary.correct, stage.boundary.correct),
      q("p-error", "practice", 1, "Find the issue", stage.variable.prompt, stage.variable.options, stage.variable.correct, stage.variable.explanation),
      q("p-order", "practice", 2, "Pipeline ordering", "Which order is correct?", stage.ordering.options, stage.ordering.correct, `The correct pipeline order is ${stage.ordering.correct}.`),
    ],
    review: [
      q("r-summary", "review", 0, "Concept summary", "Which statement best summarizes this stage?", [stage.reviewStatement, "Labels are no longer needed", "The test set should train the model"], stage.reviewStatement, stage.reviewStatement),
      q("r-transfer", "review", 1, "New scenario", stage.transfer.prompt, stage.transfer.options, stage.transfer.correct, `The same principle transfers: ${stage.transfer.correct}.`),
      q("r-check", "review", 2, "Final checkpoint", stage.operation.prompt, stage.operation.options, stage.operation.correct, stage.operation.explanation),
    ],
  };
}

export const questionBanks = Object.fromEntries(sentimentStages.map((stage) => [stage.id, buildQuestionBank(stage)])) as Record<string, Record<StepId, QuestionItem[]>>;
export const questionBank = questionBanks.data_loading_and_preparation;
