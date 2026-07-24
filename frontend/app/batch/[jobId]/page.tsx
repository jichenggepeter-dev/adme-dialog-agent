import { BatchJobWorkspace } from "@/components/batch-job-workspace";

export default async function BatchJobPage({ params }: { params: Promise<{ jobId: string }> }) {
  const { jobId } = await params;
  return <main id="main-content" className="route-main secondary-route"><header className="page-heading"><h1>Batch Screening</h1><p>Review validation, prediction progress, compound results, and exports.</p></header><BatchJobWorkspace jobId={jobId} /></main>;
}
