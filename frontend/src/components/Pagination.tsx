interface Props {
  page: number;
  totalPages: number;
  onChange: (page: number) => void;
}

export default function Pagination({ page, totalPages, onChange }: Props) {
  if (totalPages <= 1) return null;

  const pages = Array.from({ length: totalPages }, (_, i) => i + 1).filter(
    (p) => p === 1 || p === totalPages || Math.abs(p - page) <= 2
  );

  return (
    <nav className="pagination" aria-label="Search results pages">
      <button onClick={() => onChange(page - 1)} disabled={page <= 1} aria-label="Previous page">
        Prev
      </button>
      {pages.map((p, i) => (
        <span key={p} style={{ display: "flex", alignItems: "center", gap: 4 }}>
          {i > 0 && pages[i - 1] !== p - 1 && <span style={{ color: "var(--color-muted)" }}>…</span>}
          <button className={p === page ? "active" : ""} onClick={() => onChange(p)}>
            {p}
          </button>
        </span>
      ))}
      <button onClick={() => onChange(page + 1)} disabled={page >= totalPages} aria-label="Next page">
        Next
      </button>
    </nav>
  );
}
