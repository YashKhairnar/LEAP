import type { Metadata } from "next";
import { notFound } from "next/navigation";
import TaskIntroductionPage from "@/features/learning/components/task-introduction";
import { taskIntroductions } from "@/features/learning/lib/lesson-introductions";

async function getTask(params: Promise<{ task: string }>) {
  const { task } = await params;
  if (task !== "cnn" && task !== "regression") notFound();
  return taskIntroductions[task];
}

export async function generateMetadata({ params }: { params: Promise<{ task: string }> }): Promise<Metadata> {
  const task = await getTask(params);
  return { title: `${task.title} · Learning overview | LEAP`, description: task.description };
}

export default async function TaskPage({ params, searchParams }: { params: Promise<{ task: string }>; searchParams: Promise<{ view?: string }> }) {
  const task = await getTask(params);
  const { view } = await searchParams;
  return <TaskIntroductionPage key={`${task.slug}.${view ?? "introduction"}`} task={task} initialView={view === "assessment" ? "assessment" : view === "dataset" ? "dataset" : "introduction"} />;
}
