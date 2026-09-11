import { useEffect, useState } from "react";

import ConfirmDialog from "../components/ConfirmDialog";
import { EmptyState, ErrorState } from "../components/States";
import { ApiRequestError, api } from "../services/api";
import type { IndexingJob } from "../types/api";

function statusColor(status: IndexingJob["status"]): string {
  switch (status) {
    case "succeeded":
      return "var(--color-success)";
    case "failed":
      return "var(--color-danger)";
    case "partially_failed":
      return "var(--color-warning)";
    default:
      return "var(--color-muted)";
  }
}

export default function IndexingPage() {
  const [jobs, setJobs] = useState<IndexingJob[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [confirmAction, setConfirmAction] = useState<"rebuild" | "reindex" | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function load() {
    try {
      setJobs(await api.listJobs());
      setError(null);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : "Could not load indexing jobs.");
    }
  }

  useEffect(() => {
    load();
    const interval = setInterval(load, 5_000);
    return () => clearInterval(interval);
  }, []);

  async function handleConfirm() {
    if (!confirmAction) return;
    setSubmitting(true);
    try {
      if (confirmAction === "rebuild") {
        await api.rebuildIndex();
      } else {
        await api.reindex();
      }
      await load();
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : "Failed to start job.");
    } finally {
      setSubmitting(false);
      setConfirmAction(null);
    }
  }

  return (
    <div>
      <div className="page-header">
        <h1>Indexing</h1>
        <p>Monitor and control the async indexing pipeline.</p>
      </div>

      <div className="filter-row">
        <button className="btn" onClick={() => setConfirmAction("reindex")}>
          Index pending documents
        </button>
        <button className="btn" onClick={() => setConfirmAction("rebuild")}>
          Rebuild full index
        </button>
      </div>

      {error && <ErrorState title="Could not load jobs" description={error} onRetry={load} />}

      {!error && jobs.length === 0 && (
        <EmptyState title="No indexing jobs yet" description="Start one above, or bulk-create documents via the API." />
      )}

      {!error && jobs.length > 0 && (
        <table className="data-table">
          <thead>
            <tr>
              <th>Type</th>
              <th>Status</th>
              <th>Progress</th>
              <th>Processed</th>
              <th>Failed</th>
              <th>Retries</th>
              <th>Started</th>
            </tr>
          </thead>
          <tbody>
            {jobs.map((job) => (
              <tr key={job.id}>
                <td>{job.job_type}</td>
                <td style={{ color: statusColor(job.status) }}>{job.status}</td>
                <td>{job.progress_pct.toFixed(0)}%</td>
                <td>{job.processed_documents.toLocaleString()}</td>
                <td>{job.failed_documents.toLocaleString()}</td>
                <td>{job.retry_count}</td>
                <td>{job.started_at ? new Date(job.started_at).toLocaleString() : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {confirmAction && (
        <ConfirmDialog
          title={confirmAction === "rebuild" ? "Rebuild full index?" : "Index pending documents?"}
          description={
            confirmAction === "rebuild"
              ? "This re-sends every document to Elasticsearch, regardless of current index state. It can take a while on large datasets."
              : "This queues indexing for documents that aren't yet in Elasticsearch."
          }
          confirmLabel={submitting ? "Starting…" : "Start job"}
          onConfirm={handleConfirm}
          onCancel={() => setConfirmAction(null)}
        />
      )}
    </div>
  );
}
