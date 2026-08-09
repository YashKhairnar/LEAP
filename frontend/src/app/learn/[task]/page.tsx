import Link from "next/link";
import { notFound } from "next/navigation";

const paths = {
  cnn: {
    eyebrow: "Intermediate · Image classification",
    title: "Image Classification with CNNs",
    description: "Learn how pixels become features and how a convolutional neural network learns visual patterns.",
    stages: ["Load images", "Split & augment", "Build CNN", "Train network", "Classify", "Evaluate"],
  },
  regression: {
    eyebrow: "Foundation · Regression",
    title: "House Price Regression",
    description: "Learn to predict a continuous value from property features and measure how close the predictions are.",
    stages: ["Prepare data", "Split data", "Select features", "Train model", "Predict price", "Measure error"],
  },
};

export default async function TaskOverview({ params }: { params: Promise<{ task: string }> }) {
  const { task } = await params;
  const path = paths[task as keyof typeof paths];
  if (!path) notFound();

  return <main className="overview-shell">
    <header className="topbar"><Link className="brand" href="/"><span>LEAP</span></Link><div className="header-context"><Link className="back-link" href="/">← All learning paths</Link></div><Link className="avatar" href="/login">YS</Link></header>
    <section className="overview-hero"><p className="eyebrow">{path.eyebrow}</p><h1>{path.title}</h1><p>{path.description}</p></section>
    <section className="overview-path">
      <div className="overview-heading"><div><p className="eyebrow blue">Predefined path</p><h2>Six stages from data to evaluation</h2></div><span>Not started</span></div>
      <ol>{path.stages.map((stage, index) => <li key={stage}><span className="overview-number">0{index + 1}</span><div><small>Stage {index + 1}</small><strong>{stage}</strong></div><span className="overview-status">{index === 0 ? "Start here" : "Follows stage " + index}</span></li>)}</ol>
      <p className="overview-note">This learning path structure is ready. Detailed lesson content will follow the same Activate → Connect → Implement → Learn → Practice → Review sequence used in the sentiment path.</p>
      <Link className="overview-cta" href="/">Back to dashboard</Link>
    </section>
  </main>;
}
