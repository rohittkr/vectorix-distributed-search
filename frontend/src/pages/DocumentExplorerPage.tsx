import { useState } from "react";

import ConfirmDialog from "../components/ConfirmDialog";
import { EmptyState, ErrorState } from "../components/States";
import { ApiRequestError, api } from "../services/api";
import type { DocumentRead } from "../types/api";

export default function DocumentExplorerPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<DocumentRead[] | null>(null);
  const [selected, setSelected] = useState<DocumentRead | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pendingDelete, setPendingDelete] = useState<DocumentRead | null>(null);
  const [creating, setCreating] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newContent, setNewContent] = useState("");

  async function handleLookup(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const doc = await api.getDocument(query.trim());
      setResults([doc]);
    } catch (err) {
      setResults([]);
      setError(err instanceof ApiRequestError ? err.message : "Lookup failed.");
    }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    try {
      const doc = await api.createDocument({ title: newTitle, content: newContent });
      setResults((prev) => [doc, ...(prev ?? [])]);
      setNewTitle("");
      setNewContent("");
      setCreating(false);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : "Failed to create document.");
    }
  }

  async function handleDelete() {
    if (!pendingDelete) return;
    try {
      await api.deleteDocument(pendingDelete.id);
      setResults((prev) => prev?.filter((d) => d.id !== pendingDelete.id) ?? null);
      setSelected(null);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : "Failed to delete document.");
    } finally {
      setPendingDelete(null);
    }
  }

  return (
    <div>
      <div className="page-header">
        <h1>Documents</h1>
        <p>Look up a document by ID, or create a new one directly.</p>
      </div>

      <form onSubmit={handleLookup}>
        <div className="search-bar">
          <input
            type="text"
            placeholder="Paste a document ID…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
      </form>

      <div className="filter-row">
        <button className="btn" onClick={() => setCreating(true)}>
          New document
        </button>
      </div>

      {creating && (
        <form onSubmit={handleCreate} style={{ marginBottom: 24, display: "grid", gap: 8, maxWidth: 480 }}>
          <input
            className="search-bar"
            placeholder="Title"
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
            required
          />
          <textarea
            placeholder="Content"
            value={newContent}
            onChange={(e) => setNewContent(e.target.value)}
            required
            rows={4}
            style={{ padding: 12, border: "1px solid var(--color-border)", borderRadius: 8, fontFamily: "inherit" }}
          />
          <div style={{ display: "flex", gap: 8 }}>
            <button type="submit" className="btn btn-primary">
              Create
            </button>
            <button type="button" className="btn" onClick={() => setCreating(false)}>
              Cancel
            </button>
          </div>
        </form>
      )}

      {error && <ErrorState title="Something went wrong" description={error} />}

      {results !== null && results.length === 0 && !error && (
        <EmptyState title="No document found" description="Check the ID and try again." />
      )}

      {results && results.length > 0 && (
        <table className="data-table">
          <thead>
            <tr>
              <th>Title</th>
              <th>Category</th>
              <th>Indexed</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {results.map((doc) => (
              <tr key={doc.id}>
                <td>
                  <a href="#" onClick={(e) => { e.preventDefault(); setSelected(doc); }}>
                    {doc.title}
                  </a>
                </td>
                <td>{doc.category ?? "—"}</td>
                <td>{doc.indexed_at ? "Yes" : "Pending"}</td>
                <td>
                  <button className="btn" onClick={() => setPendingDelete(doc)}>
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {selected && (
        <div style={{ marginTop: 24, padding: 16, border: "1px solid var(--color-border)", borderRadius: 8 }}>
          <h3>{selected.title}</h3>
          <p style={{ color: "var(--color-muted)" }}>{selected.content}</p>
        </div>
      )}

      {pendingDelete && (
        <ConfirmDialog
          title="Delete this document?"
          description={`"${pendingDelete.title}" will be permanently removed. This cannot be undone.`}
          confirmLabel="Delete"
          onConfirm={handleDelete}
          onCancel={() => setPendingDelete(null)}
        />
      )}
    </div>
  );
}
