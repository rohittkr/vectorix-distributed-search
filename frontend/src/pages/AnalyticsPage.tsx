import { useEffect, useState } from "react";

import StatusIndicator from "../components/StatusIndicator";
import { ErrorState } from "../components/States";
import { ApiRequestError, api } from "../services/api";
import type { StatsResponse } from "../types/api";

export default function AnalyticsPage() {
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      setStats(await api.stats());
      setError(null);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : "Could not load stats.");
    }
  }

  useEffect(() => {
    load();
    const interval = setInterval(load, 10_000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div>
      <div className="page-header">
        <h1>Analytics</h1>
        <p>Live index and search performance, refreshed every 10 seconds.</p>
      </div>

      {error && <ErrorState title="Could not load analytics" description={error} onRetry={load} />}

      {stats && (
        <div className="stat-grid">
          <div className="stat-card">
            <div className="stat-value">{stats.total_documents.toLocaleString()}</div>
            <div className="stat-label">Total documents</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{stats.indexed_documents.toLocaleString()}</div>
            <div className="stat-label">Indexed</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{stats.pending_documents.toLocaleString()}</div>
            <div className="stat-label">Pending indexing</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{stats.active_jobs}</div>
            <div className="stat-label">Active jobs</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{(stats.cache_hit_rate * 100).toFixed(1)}%</div>
            <div className="stat-label">Cache hit rate</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">
              <StatusIndicator status={stats.elasticsearch_status} />
            </div>
            <div className="stat-label">Elasticsearch</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">
              <StatusIndicator status={stats.redis_status} />
            </div>
            <div className="stat-label">Redis</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">
              <StatusIndicator status={stats.postgres_status} />
            </div>
            <div className="stat-label">PostgreSQL</div>
          </div>
        </div>
      )}
    </div>
  );
}
