interface Props {
  status: string;
}

function classify(status: string): "ok" | "degraded" | "down" {
  const normalized = status.toLowerCase();
  if (["ok", "green", "ready", "alive"].includes(normalized)) return "ok";
  if (["yellow", "degraded"].includes(normalized)) return "degraded";
  return "down";
}

export default function StatusIndicator({ status }: Props) {
  const level = classify(status);
  return (
    <span>
      <span className={`status-dot ${level}`} />
      {status}
    </span>
  );
}
