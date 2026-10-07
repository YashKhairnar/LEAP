import type { QuestionItem } from "@/features/learning/lib/question-bank";

/**
 * Content IDs are global and versioned because the backend rejects reuse of an
 * ID when authored question content changes. Additional-task question IDs
 * already include their task prefix; sentiment question IDs do not.
 */
export function questionContentId(task: string, item: QuestionItem): string {
  if (item.collectionContent) return item.collectionContent.content_id;
  const globalId = item.id.startsWith(`${task}.`) ? item.id : `${task}.${item.id}`;
  return `${globalId}.v2`;
}
