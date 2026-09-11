import { useEffect, useState } from "react";

import StatusIndicator from "../components/StatusIndicator";
import { ErrorState } from "../components/States";
import { ApiRequestError, api } from "../services/api";

export default function SystemHealthPage() {
  const [checks, setChecks] = useState<Record<string, string> | null>(null);
  const [overall, setOverall] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      const health = await api.health();
      setChecks(health.checks);
      setOverall(health.status);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : "Could not reach the backend.");
    }
  }

  useEffect(() => {
    load();
    const interval = setInterval(load, 5_000);
    return () => clearInterval(interval);
  }, []);

  const labels: Record<string, string> = {
    elasticsearch: "Elasticsearch",
    redis: "Redis",
    postgres: "PostgreSQL",
  };

  return (
    <div>
      <div className="page-header">
        <h1>System health</h1>
        <p>
          Overall status: <StatusIndicator status={overall || "unknown"} />
        </p>
      </div>

      {error && <ErrorState title="Could not load health checks" description={error} onRetry={load} />}

      {checks && (
        <table className="data-table">
          <thead>
            <tr>
              <th>Service</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(checks).map(([key, value]) => (
              <tr key={key}>
                <td>{labels[key] ?? key}</td>
                <td>
                  <StatusIndicator status={value} />
                </td>
              </tr>
            ))}
            <tr>
              <td>FastAPI backend</td>
              <td>
                <StatusIndicator status={error ? "down" : "ok"} />
              </td>
            </tr>
          </tbody>
        </table>
      )}
    </div>
  );
}
