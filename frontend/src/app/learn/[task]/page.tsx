import { notFound } from "next/navigation";
import { additionalTasks } from "@/lib/additional-task-bank";
import TaskLessonClient from "./task-lesson-client";

export default async function TaskPage({ params }: { params: Promise<{ task: string }> }) {
  const { task: taskId } = await params;
  if (taskId !== "cnn" && taskId !== "regression") notFound();
  return <TaskLessonClient task={additionalTasks[taskId]} />;
}
