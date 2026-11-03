"use client";

import CnnLayersAnimation from "@/features/learning/components/lesson-animations/cnn-layers-animation";
import RecallAnimation from "@/features/learning/components/lesson-animations/recall-animation";
import RegressionLineAnimation from "@/features/learning/components/lesson-animations/regression-line-animation";
import ReshapeAnimation from "@/features/learning/components/lesson-animations/reshape-animation";
import ScalingAnimation from "@/features/learning/components/lesson-animations/scaling-animation";
import StratifyAnimation from "@/features/learning/components/lesson-animations/stratify-animation";
import TfidfAnimation from "@/features/learning/components/lesson-animations/tfidf-animation";
import TrainingLoopAnimation from "@/features/learning/components/lesson-animations/training-loop-animation";
import WordWeightsAnimation from "@/features/learning/components/lesson-animations/word-weights-animation";

// Stage animations shown in the Idea step, keyed by "task.stage". They are the same for
// every analogy preference so they don't differ between study conditions.
export default function StageAnimation({ task, stage }: { task: string; stage: string }) {
  switch (`${task}.${stage}`) {
    case "cnn.load_images": return <ReshapeAnimation />;
    case "cnn.build_cnn": return <CnnLayersAnimation />;
    case "cnn.train_network": return <TrainingLoopAnimation />;
    case "regression.scale_features": return <ScalingAnimation />;
    case "regression.train_regression": return <RegressionLineAnimation mode="fit" />;
    case "regression.evaluate_regression": return <RegressionLineAnimation mode="errors" />;
    case "sentiment_classification.train_test_split": return <StratifyAnimation />;
    case "sentiment_classification.tfidf_vectorization": return <TfidfAnimation />;
    case "sentiment_classification.prediction": return <WordWeightsAnimation />;
    case "sentiment_classification.evaluation": return <RecallAnimation />;
    default: return null;
  }
}
