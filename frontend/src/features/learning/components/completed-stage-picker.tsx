"use client";

import { useId } from "react";

export default function CompletedStagePicker({ stages, selectedStage = "", onSelect }: {
  stages: { id: string; label: string }[];
  selectedStage?: string;
  onSelect: (stageId: string) => void;
}) {
  const id = useId();
  if (!stages.length) return null;

  return <div className="completed-stage-picker">
    <label htmlFor={id}>Review completed stages</label>
    <select id={id} value={selectedStage} onChange={(event) => onSelect(event.target.value)}>
      <option value="">{selectedStage ? "Return to current position" : "Choose a stage…"}</option>
      {stages.map((stage, index) => <option key={stage.id} value={stage.id}>Stage {index + 1}: {stage.label}</option>)}
    </select>
  </div>;
}
