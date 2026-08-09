import type { InstructionalActionType, InstructionalStep } from "./instructional-actions";

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

export const questionBank: Record<StepId, QuestionItem[]> = {
  activate: [
    { id: "a-concept", step: "activate", actionType: "activate.java_concept_identification", typeLabel: "Java concept", prompt: "What does one Review object represent?", options: ["One labeled review", "The complete dataset", "Only a sentiment label"], correctAnswer: "One labeled review", explanation: "One object keeps one review text paired with its sentiment.", misconception: "object_collection_scope" },
    { id: "a-output", step: "activate", actionType: "activate.java_output_prediction", typeLabel: "Output prediction", prompt: "After adding three Review objects, what does reviews.size() return?", options: ["1", "2", "3"], correctAnswer: "3", explanation: "ArrayList.size() counts the objects stored in the collection.", misconception: "collection_size" },
    { id: "a-explain", step: "activate", actionType: "activate.java_code_explanation", typeLabel: "Code explanation", prompt: "Why are text and sentiment stored in the same Review object?", options: ["To keep each review paired with its label", "To make every sentiment positive", "To train a model in Java"], correctAnswer: "To keep each review paired with its label", explanation: "The fields belong together because they describe one labeled example.", misconception: "label_pairing" },
  ],
  connect: [
    { id: "c-match", step: "connect", actionType: "connect.concept_matching", typeLabel: "Concept matching", prompt: "A Java Review object maps to what in the dataset?", options: ["One row", "The complete DataFrame", "The pandas library"], correctAnswer: "One row", explanation: "Both structures represent one labeled example.", misconception: "object_row_mapping" },
    { id: "c-compare", step: "connect", actionType: "connect.comparison_selection", typeLabel: "Comparison", prompt: "Which Java structure is closest to the complete DataFrame?", options: ["ArrayList<Review>", "One Review field", "One String"], correctAnswer: "ArrayList<Review>", explanation: "The ArrayList and DataFrame both hold the complete collection.", misconception: "collection_dataframe_mapping" },
    { id: "c-analogy", step: "connect", actionType: "connect.analogy_mapping", typeLabel: "Analogy mapping", prompt: "In the patient-file analogy, what corresponds to one dataset row?", options: ["One patient file", "The entire hospital", "A filing cabinet label"], correctAnswer: "One patient file", explanation: "One patient file and one dataset row each describe a single labeled case.", misconception: "analogy_case_mapping" },
  ],
  implement: [
    { id: "i-complete", step: "implement", actionType: "implement.code_completion", typeLabel: "Code completion", prompt: "Complete: df = pd.____(\"reviews.csv\")", options: ["read_csv", "fit", "predict"], correctAnswer: "read_csv", explanation: "read_csv loads the file into a DataFrame.", misconception: "loading_api" },
    { id: "i-output", step: "implement", actionType: "implement.code_output_prediction", typeLabel: "Output prediction", prompt: "What does len(df) return for the displayed dataset?", options: ["2", "3", "6"], correctAnswer: "3", explanation: "len(df) returns the number of rows, and the dataset has three reviews.", misconception: "dataframe_length" },
    { id: "i-variable", step: "implement", actionType: "implement.variable_purpose", typeLabel: "Variable purpose", prompt: "What does df represent?", options: ["The complete review dataset", "One sentiment label", "A trained model"], correctAnswer: "The complete review dataset", explanation: "df refers to the DataFrame containing all loaded rows and columns.", misconception: "dataframe_identity" },
  ],
  learn: [
    { id: "l-classify", step: "learn", actionType: "learn.transfer_or_new", typeLabel: "Transfer or new", prompt: "Which behavior is genuinely new in pandas?", options: ["Loading the complete table in one call", "Keeping text paired with sentiment", "Counting stored examples"], correctAnswer: "Loading the complete table in one call", explanation: "Java knowledge explains the contents; pandas changes how the full collection is built and handled.", misconception: "transfer_boundary" },
    { id: "l-difference", step: "learn", actionType: "learn.difference_explanation", typeLabel: "Difference", prompt: "What is the main shift from Java construction to pandas loading?", options: ["From one record at a time to the whole table", "From labels to unlabeled data", "From Python back to Java"], correctAnswer: "From one record at a time to the whole table", explanation: "pandas replaces repeated construction and add calls with a table-level operation.", misconception: "record_table_shift" },
    { id: "l-boundary", step: "learn", actionType: "learn.concept_boundary", typeLabel: "Concept boundary", prompt: "Which statement correctly describes this stage?", options: ["The data is loaded, but no model is trained", "The model is trained by df.head()", "The predictions are already evaluated"], correctAnswer: "The data is loaded, but no model is trained", explanation: "Stage 1 prepares and inspects data. Training begins later with fit().", misconception: "loading_equals_training" },
  ],
  practice: [
    { id: "p-diagnose", step: "practice", actionType: "practice.misconception_diagnosis", typeLabel: "Misconception check", prompt: "Does read_csv() train the sentiment model?", options: ["Yes, it learns from reviews", "No, it only loads the data", "Yes, but only three rows"], correctAnswer: "No, it only loads the data", explanation: "Training begins when a model calls fit(), not when the dataset is loaded.", misconception: "loading_equals_training" },
    { id: "p-error", step: "practice", actionType: "practice.error_identification", typeLabel: "Find the issue", prompt: "What is missing if reviews.csv contains text but no sentiment column?", options: ["The labels needed for supervised learning", "The pandas library name", "The Java constructor"], correctAnswer: "The labels needed for supervised learning", explanation: "Supervised classification needs each training example paired with a known target label.", misconception: "missing_labels" },
    { id: "p-order", step: "practice", actionType: "practice.pipeline_ordering", typeLabel: "Pipeline ordering", prompt: "Which order is correct?", options: ["read_csv → split → fit", "fit → read_csv → split", "predict → fit → read_csv"], correctAnswer: "read_csv → split → fit", explanation: "Data must be loaded and divided before the model can be trained.", misconception: "pipeline_order" },
  ],
  review: [
    { id: "r-summary", step: "review", actionType: "review.concept_summary", typeLabel: "Concept summary", prompt: "What is genuinely new when moving from Java objects to pandas?", options: ["The whole table can be loaded in one call", "Reviews no longer need labels", "Every row becomes a Java class"], correctAnswer: "The whole table can be loaded in one call", explanation: "The information stays the same, but pandas handles the complete table at once.", misconception: "transfer_summary" },
    { id: "r-transfer", step: "review", actionType: "review.novel_transfer", typeLabel: "New scenario", prompt: "In a support-ticket dataset, what would one row represent?", options: ["One labeled support ticket", "Every ticket in the company", "The trained classifier"], correctAnswer: "One labeled support ticket", explanation: "The row-as-one-example relationship transfers to other labeled datasets.", misconception: "generalization" },
    { id: "r-check", step: "review", actionType: "review.confidence_checkpoint", typeLabel: "Final checkpoint", prompt: "Which operation would show that model training has started?", options: ["model.fit(X_train, y_train)", "pd.read_csv(file)", "df.head()"], correctAnswer: "model.fit(X_train, y_train)", explanation: "fit() is the operation that learns patterns from training data.", misconception: "training_boundary" },
  ],
};
