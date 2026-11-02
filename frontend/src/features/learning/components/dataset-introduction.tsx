"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
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

const explanations: Record<TaskIntroduction["slug"], { row: string; inputs: string; target: string; previewNote?: string }> = {
  sentiment: {
    row: "Each row is one review together with its known sentiment.",
    inputs: "The model reads the review text. The source only tells us where the review came from.",
    target: "Sentiment is the known answer: positive or negative. The model uses these answers while learning.",
  },
  cnn: {
    row: "Each row is one handwritten digit image together with the correct digit.",
    inputs: "The model receives 64 brightness values arranged as an 8 × 8 image. A larger value means a brighter pixel.",
    target: "Label is the known answer: the digit from 0 to 9 shown in the image.",
    previewNote: "For readability, this table shows the first eight of the 64 pixel values in each image.",
  },
  regression: {
    row: "Each row is one sold house together with its sale price.",
    inputs: "The model receives four house details: bedrooms, bathrooms, square feet, and age.",
    target: "Price is the known answer. The model learns from past prices so it can estimate a price for another house.",
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
  const firstExample = dataset.preview[0];

  return <section className="dataset-introduction" aria-labelledby="dataset-title">
    <header className="dataset-introduction-header">
      <p className="intro-kicker">Before the lesson · Dataset preview</p>
      <h1 id="dataset-title">Explore the dataset</h1>
      <p>You do not need to memorize the table. Just notice what the model receives and what answer it will learn to predict.</p>
    </header>

    <section className="dataset-one-example pt-5" id="one-example" aria-labelledby="one-example-title">
      <div className="dataset-section-heading">
        <p className="dataset-section-number">1</p>
        <div><h2 id="one-example-title">Start with one example</h2><p>{explanation.row}</p></div>
      </div>
      {firstExample && <DatasetExample task={task.slug} row={firstExample} />}
      <div className="dataset-reading-guide">
        <div><span className="dataset-guide-marker is-input" aria-hidden="true" /><div><strong>Input</strong><p>{explanation.inputs}</p></div></div>
        <div><span className="dataset-guide-marker is-answer" aria-hidden="true" /><div><strong>Known answer</strong><p>{explanation.target}</p></div></div>
      </div>
    </section>

    <section className="dataset-sample" id="more-examples" aria-labelledby="sample-rows-title">
      <div className="dataset-section-heading">
        <p className="dataset-section-number">2</p>
        <div><h2 id="sample-rows-title">Compare a few more examples</h2><p>{explanation.previewNote ?? "Every row follows the same input-and-answer structure."}</p></div>
      </div>
      <div className="lesson-dataset-preview">
        <div className="lesson-dataset-meta"><span>{dataset.runtime_filename}</span><span>{dataset.row_count.toLocaleString()} examples · Answer column: {dataset.target}</span></div>
        <div className="cell-table-wrap">
          <table>
            <thead><tr>{previewColumns.map((column) => <th key={column}>{column}</th>)}</tr></thead>
            <tbody>{dataset.preview.map((row, rowIndex) => <tr key={rowIndex}>{previewColumns.map((column) => <td key={column}>{row[column]}</td>)}</tr>)}</tbody>
          </table>
        </div>
      </div>
    </section>

    <section className="dataset-ready" id="dataset-continue" aria-labelledby="dataset-ready-title">
      <p className="dataset-section-number">3</p>
      <div><h2 id="dataset-ready-title">That’s all you need for now</h2><p>The lesson will show you how Python loads these examples and how the model learns from them.</p></div>
      <Link className="primary-button" href={`/learn/${task.slug}/lesson`}>Start the lesson <span aria-hidden="true">→</span></Link>
    </section>
    <Link className="text-button dataset-back-link" href={`/learn/${task.slug}`}>← Back to task overview</Link>
  </section>;
}

function DatasetExample({ task, row }: { task: TaskIntroduction["slug"]; row: Record<string, string> }) {
  if (task === "sentiment") return <div className="dataset-example-flow">
    <div className="dataset-example-input"><span>Model receives</span><blockquote>“{row.review}”</blockquote><small>Source: {row.source}</small></div>
    <span className="dataset-example-arrow" aria-hidden="true">→</span>
    <div className="dataset-example-answer"><span>Known answer</span><strong>{row.sentiment}</strong></div>
  </div>;

  if (task === "regression") return <div className="dataset-example-flow">
    <div className="dataset-example-input"><span>Model receives</span><dl className="dataset-house-features">
      <div><dt>Bedrooms</dt><dd>{row.bedrooms}</dd></div>
      <div><dt>Bathrooms</dt><dd>{row.bathrooms}</dd></div>
      <div><dt>Square feet</dt><dd>{Number(row.square_feet).toLocaleString()}</dd></div>
      <div><dt>Age</dt><dd>{row.age_years} years</dd></div>
    </dl></div>
    <span className="dataset-example-arrow" aria-hidden="true">→</span>
    <div className="dataset-example-answer"><span>Known sale price</span><strong>{formatPrice(row.price)}</strong></div>
  </div>;

  const pixels = Array.from({ length: 64 }, (_, index) => Number(row[`pixel_${index}`]));
  return <div className="dataset-example-flow">
    <div className="dataset-example-input cnn-dataset-example"><span>Model receives</span><div className="dataset-digit-image" role="img" aria-label={`An eight by eight pixel image of the handwritten digit ${row.label}`}>
      {pixels.map((value, index) => { const brightness = Math.round(value / 16 * 255); return <i key={index} style={{ backgroundColor: `rgb(${brightness}, ${brightness}, ${brightness})` }} />; })}
    </div><small>64 brightness values · Image {row.image_id}</small></div>
    <span className="dataset-example-arrow" aria-hidden="true">→</span>
    <div className="dataset-example-answer"><span>Known digit</span><strong>{row.label}</strong></div>
  </div>;
}

function formatPrice(value: string) {
  const price = Number(value);
  return Number.isFinite(price) ? price.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }) : value;
}
