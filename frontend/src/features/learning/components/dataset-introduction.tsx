"use client";

import { useEffect, useState } from "react";
import { API_URL } from "@/lib/auth";
import type { TaskIntroduction } from "@/features/learning/lib/lesson-introductions";

type DatasetInfo = {
  dataset_id: string;
  version: string;
  runtime_filename: string;
  target: string;
  features: string[];
  description: string;
  columns: string[];
  row_count: number;
  preview: Record<string, string>[];
};

const explanations: Record<TaskIntroduction["slug"], {
  row: string;
  inputs: string;
  target: string;
  previewNote?: string;
}> = {
  sentiment: {
    row: "One row is one sentence from an Amazon, IMDb, or Yelp review, kept together with its source and known sentiment.",
    inputs: "The review column contains the text the classifier will learn from. The source column records where the sentence came from; it is context, not the text feature used by TF-IDF.",
    target: "The sentiment column is the answer to learn: positive or negative. It stays paired with the review during splitting, training, and evaluation.",
  },
  cnn: {
    row: "One row is one handwritten digit image. Its 64 pixel values form an 8 × 8 intensity grid, and image_id identifies the example.",
    inputs: "pixel_0 through pixel_63 are brightness values from 0 to 16. The lesson reshapes those 64 numbers into one image channel with eight rows and eight columns.",
    target: "The label column is the digit shown in the image, from 0 through 9. The CNN learns to connect pixel patterns to this class.",
    previewNote: "The table shows the first eight pixel values from each 64-value image row to keep the preview readable.",
  },
  regression: {
    row: "One row is one recorded home sale in Ames, Iowa, with property measurements and its observed sale price.",
    inputs: "Bedrooms, bathrooms, square feet, and age in years are the explanatory features the regression model receives.",
    target: "The price column is the numeric value the model learns to estimate. It is withheld from the inputs used to make a prediction.",
  },
};

export default function DatasetIntroduction({ task }: { task: TaskIntroduction }) {
  const [dataset, setDataset] = useState<DatasetInfo | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let active = true;
    void fetch(`${API_URL}/api/datasets/${encodeURIComponent(task.taskId)}`, { credentials: "include" })
      .then(async (response) => {
        if (!response.ok) throw new Error(`Dataset API returned ${response.status}`);
        return response.json() as Promise<DatasetInfo>;
      })
      .then((value) => { if (active) setDataset(value); })
      .catch(() => { if (active) setFailed(true); });
    return () => { active = false; };
  }, [task.taskId]);

  const explanation = explanations[task.slug];
  if (failed) return <section className="dataset-introduction" aria-labelledby="dataset-title"><p className="dataset-preview-status" role="status">The dataset preview is temporarily unavailable.</p></section>;
  if (!dataset) return <section className="dataset-introduction" aria-labelledby="dataset-title"><div className="dataset-preview-skeleton" aria-label="Loading dataset preview" /></section>;

  const previewColumns = task.slug === "cnn"
    ? ["image_id", ...Array.from({ length: 8 }, (_, index) => `pixel_${index}`), "label"]
    : dataset.columns;

  return <section className="dataset-introduction" aria-labelledby="dataset-title">
    <header className="dataset-introduction-header">
      <p className="intro-kicker">Dataset preview</p>
      <h1 id="dataset-title">Meet <code>{dataset.runtime_filename}</code></h1>
      <p>{dataset.description}</p>
    </header>

    <dl className="dataset-facts">
      <div><dt>Examples</dt><dd>{dataset.row_count.toLocaleString()}</dd></div>
      <div><dt>Input features</dt><dd>{task.slug === "cnn" ? "64 pixels" : dataset.features.join(", ")}</dd></div>
      <div><dt>Prediction target</dt><dd>{dataset.target}</dd></div>
    </dl>

    <div className="dataset-explanation-grid">
      <article><span>01</span><h2>What one row means</h2><p>{explanation.row}</p></article>
      <article><span>02</span><h2>What goes into the model</h2><p>{explanation.inputs}</p></article>
      <article><span>03</span><h2>What the model learns</h2><p>{explanation.target}</p></article>
    </div>

    <section className="dataset-sample" aria-labelledby="sample-rows-title">
      <div><h2 id="sample-rows-title">Sample rows</h2><p>{explanation.previewNote ?? "These are the first five records from the dataset used by the executable lesson code."}</p></div>
      <div className="lesson-dataset-preview">
        <div className="lesson-dataset-meta"><span>{dataset.runtime_filename}</span><span>Version {dataset.version} · Target: {dataset.target}</span></div>
        <div className="cell-table-wrap">
          <table>
            <thead><tr>{previewColumns.map((column) => <th key={column}>{column}</th>)}</tr></thead>
            <tbody>{dataset.preview.map((row, rowIndex) => <tr key={rowIndex}>{previewColumns.map((column) => <td key={column}>{row[column]}</td>)}</tr>)}</tbody>
          </table>
        </div>
      </div>
    </section>

    <p className="dataset-pipeline-note"><strong>How it fits the task:</strong> {task.pipeline.join(" → ")}. The stages transform these raw rows into model-ready inputs while keeping each target aligned with its example.</p>
  </section>;
}
