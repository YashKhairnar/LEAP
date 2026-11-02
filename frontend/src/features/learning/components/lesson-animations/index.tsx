"use client";

import CnnLayersAnimation from "@/features/learning/components/lesson-animations/cnn-layers-animation";
import RecallAnimation from "@/features/learning/components/lesson-animations/recall-animation";
import RegressionLineAnimation from "@/features/learning/components/lesson-animations/regression-line-animation";
import TfidfAnimation from "@/features/learning/components/lesson-animations/tfidf-animation";
import WordWeightsAnimation from "@/features/learning/components/lesson-animations/word-weights-animation";

// Stage animations shown in the Idea step, keyed by "task.stage". They are the same for
// every analogy preference so they don't differ between study conditions.
export default function StageAnimation({ task, stage }: { task: string; stage: string }) {
  switch (`${task}.${stage}`) {
    case "cnn.build_cnn": return <CnnLayersAnimation />;
    case "regression.train_regression": return <RegressionLineAnimation mode="fit" />;
    case "regression.evaluate_regression": return <RegressionLineAnimation mode="errors" />;
    case "sentiment_classification.tfidf_vectorization": return <TfidfAnimation />;
    case "sentiment_classification.prediction": return <WordWeightsAnimation />;
    case "sentiment_classification.evaluation": return <RecallAnimation />;
    default: return null;
  }
}
