import type { Metadata } from "next";
import TaskIntroductionPage from "@/features/learning/components/task-introduction";
import { taskIntroductions } from "@/features/learning/lib/lesson-introductions";

export const metadata: Metadata = {
  title: "Sentiment Classification · Learning overview | LEAP",
  description: taskIntroductions.sentiment.description,
};

export default async function SentimentOverview({ searchParams }: { searchParams: Promise<{ view?: string }> }) {
  const { view } = await searchParams;
  return <TaskIntroductionPage task={taskIntroductions.sentiment} initialView={view === "assessment" ? "assessment" : view === "dataset" ? "dataset" : "introduction"} />;
}
