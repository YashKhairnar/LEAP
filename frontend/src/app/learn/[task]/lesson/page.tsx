import { notFound } from "next/navigation";
import { additionalTasks } from "@/features/learning/lib/additional-task-bank";
import TaskLessonClient from "@/features/learning/components/task-lesson-client";

export default async function TaskLessonPage({ params, searchParams }: {
  params: Promise<{ task: string }>;
  searchParams: Promise<{ review?: string }>;
}) {
  const { task } = await params;
  if (task !== "cnn" && task !== "regression") notFound();
  const { review } = await searchParams;
  return <TaskLessonClient key={task} task={additionalTasks[task]} initialReviewStage={review} />;
}
