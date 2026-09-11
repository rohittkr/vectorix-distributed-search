interface EmptyStateProps {
  title: string;
  description?: string;
}

export function EmptyState({ title, description }: EmptyStateProps) {
  return (
    <div className="empty-state">
      <h3>{title}</h3>
      {description && <p>{description}</p>}
    </div>
  );
}

interface ErrorStateProps {
  title: string;
  description?: string;
  onRetry?: () => void;
}

export function ErrorState({ title, description, onRetry }: ErrorStateProps) {
  return (
    <div className="error-state">
      <h3>{title}</h3>
      {description && <p>{description}</p>}
      {onRetry && (
        <button className="retry-button" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  );
}

export function ResultSkeleton() {
  return (
    <div className="result-item">
      <div className="skeleton" style={{ height: 20, width: "60%", marginBottom: 8 }} />
      <div className="skeleton" style={{ height: 14, width: "30%", marginBottom: 8 }} />
      <div className="skeleton" style={{ height: 14, width: "90%", marginBottom: 4 }} />
      <div className="skeleton" style={{ height: 14, width: "80%" }} />
    </div>
  );
}
