import { useCallback, useEffect, useRef, useState } from "react";

import Pagination from "../components/Pagination";
import ResultList from "../components/ResultList";
import { EmptyState, ErrorState, ResultSkeleton } from "../components/States";
import { useDebouncedValue } from "../hooks/useDebouncedValue";
import { ApiRequestError, api } from "../services/api";
import type { SearchResponse } from "../types/api";

const CATEGORIES = ["technology", "science", "business", "health", "sports"];

const RECENT_SEARCHES_KEY = "recent-searches";

const PAGE_SIZE = 10;

const MIN_SUGGESTION_LENGTH = 2;

function loadRecentSearches(): string[] {
  try {
    const raw = window.sessionStorage?.getItem(RECENT_SEARCHES_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [response, setResponse] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [suggestionsLoading, setSuggestionsLoading] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);

  const [recentSearches, setRecentSearches] = useState<string[]>(() =>
    loadRecentSearches()
  );

  const debouncedQuery = useDebouncedValue(query, 300);

  const inputRef = useRef<HTMLInputElement>(null);
  const searchContainerRef = useRef<HTMLDivElement>(null);

  const abortRef = useRef<AbortController | null>(null);
  const suggestionsAbortRef = useRef<AbortController | null>(null);

  // Keyboard shortcut: "/" or Cmd/Ctrl+K focuses the search box.
  useEffect(() => {
    function handler(e: KeyboardEvent) {
      const isTypingElsewhere = ["INPUT", "TEXTAREA"].includes(
        (e.target as HTMLElement)?.tagName
      );

      if (
        (e.key === "/" && !isTypingElsewhere) ||
        ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k")
      ) {
        e.preventDefault();
        inputRef.current?.focus();
      }

      if (e.key === "Escape") {
        setShowSuggestions(false);
      }
    }

    window.addEventListener("keydown", handler);

    return () => window.removeEventListener("keydown", handler);
  }, []);

  // Close the autocomplete dropdown when clicking outside the search area.
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (
        searchContainerRef.current &&
        !searchContainerRef.current.contains(e.target as Node)
      ) {
        setShowSuggestions(false);
      }
    }

    document.addEventListener("mousedown", handleClickOutside);

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  const runSearch = useCallback(
    async (q: string, cat: string | null, p: number) => {
      abortRef.current?.abort();

      const controller = new AbortController();
      abortRef.current = controller;

      setLoading(true);
      setError(null);

      try {
        const result = await api.search(
          {
            query: q,
            filters: cat ? { category: cat } : {},
            page: p,
            page_size: PAGE_SIZE,
          },
          controller.signal
        );

        setResponse(result);
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") {
          return;
        }

        if (err instanceof ApiRequestError) {
          setError(err.message);
        } else {
          setError("Something went wrong while searching. Please try again.");
        }
      } finally {
        setLoading(false);
      }
    },
    []
  );

  // Search as the debounced query changes.
  useEffect(() => {
    runSearch(debouncedQuery, category, page);
  }, [debouncedQuery, category, page, runSearch]);

  // Fetch autocomplete suggestions independently from the search request.
  useEffect(() => {
    const trimmedQuery = debouncedQuery.trim();

    suggestionsAbortRef.current?.abort();

    if (trimmedQuery.length < MIN_SUGGESTION_LENGTH) {
      setSuggestions([]);
      setSuggestionsLoading(false);
      return;
    }

    const controller = new AbortController();
    suggestionsAbortRef.current = controller;

    setSuggestionsLoading(true);

    api
      .suggestions(trimmedQuery, controller.signal)
      .then((result) => {
        if (controller.signal.aborted) {
          return;
        }

        setSuggestions(result.suggestions);
        setShowSuggestions(true);
      })
      .catch((err) => {
        if (err instanceof DOMException && err.name === "AbortError") {
          return;
        }

        // Autocomplete should never break normal search.
        setSuggestions([]);
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setSuggestionsLoading(false);
        }
      });

    return () => {
      controller.abort();
    };
  }, [debouncedQuery]);

  function saveRecentSearch(search: string) {
    const trimmedSearch = search.trim();

    if (!trimmedSearch) {
      return;
    }

    const updated = [
      trimmedSearch,
      ...recentSearches.filter((s) => s !== trimmedSearch),
    ].slice(0, 5);

    setRecentSearches(updated);
    window.sessionStorage?.setItem(
      RECENT_SEARCHES_KEY,
      JSON.stringify(updated)
    );
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    const trimmedQuery = query.trim();

    setShowSuggestions(false);

    if (trimmedQuery) {
      saveRecentSearch(trimmedQuery);
    }

    setPage(1);
    runSearch(trimmedQuery, category, 1);
  }

  function handleSuggestionClick(suggestion: string) {
    setQuery(suggestion);
    setPage(1);
    setShowSuggestions(false);

    saveRecentSearch(suggestion);

    runSearch(suggestion, category, 1);
  }

  function handleQueryChange(value: string) {
    setQuery(value);
    setPage(1);

    if (value.trim().length >= MIN_SUGGESTION_LENGTH) {
      setShowSuggestions(true);
    } else {
      setSuggestions([]);
      setShowSuggestions(false);
    }
  }

  const totalPages = response
    ? Math.max(1, Math.ceil(response.total / PAGE_SIZE))
    : 1;

  const shouldShowSuggestions =
    showSuggestions &&
    query.trim().length >= MIN_SUGGESTION_LENGTH &&
    (suggestionsLoading || suggestions.length > 0);

  return (
    <div>
      <div className="page-header">
        <h1>Search</h1>
        <p>Find anything across the index. Press / to jump to search.</p>
      </div>

      <form onSubmit={handleSubmit}>
        <div className="search-bar" ref={searchContainerRef}>
          <input
            ref={inputRef}
            type="text"
            placeholder="Search documents…"
            value={query}
            onChange={(e) => handleQueryChange(e.target.value)}
            onFocus={() => {
              if (
                query.trim().length >= MIN_SUGGESTION_LENGTH &&
                suggestions.length > 0
              ) {
                setShowSuggestions(true);
              }
            }}
            aria-label="Search query"
            aria-autocomplete="list"
            aria-controls="search-suggestions"
            aria-expanded={shouldShowSuggestions}
          />

          {shouldShowSuggestions && (
            <div
              id="search-suggestions"
              className="search-suggestions"
              role="listbox"
              aria-label="Search suggestions"
            >
              {suggestionsLoading && (
                <div className="search-suggestion-status">
                  Loading suggestions…
                </div>
              )}

              {!suggestionsLoading &&
                suggestions.map((suggestion, index) => (
                  <button
                    key={`${suggestion}-${index}`}
                    type="button"
                    className="search-suggestion"
                    role="option"
                    onMouseDown={(e) => e.preventDefault()}
                    onClick={() => handleSuggestionClick(suggestion)}
                  >
                    <span>{suggestion}</span>
                  </button>
                ))}
            </div>
          )}
        </div>
      </form>

      <div
        className="filter-row"
        role="group"
        aria-label="Filter by category"
      >
        {CATEGORIES.map((cat) => (
          <button
            key={cat}
            type="button"
            className={`filter-chip${category === cat ? " active" : ""}`}
            onClick={() => {
              setCategory(category === cat ? null : cat);
              setPage(1);
            }}
          >
            {cat}
          </button>
        ))}
      </div>

      {!query && recentSearches.length > 0 && (
        <div className="filter-row">
          {recentSearches.map((s) => (
            <button
              key={s}
              type="button"
              className="filter-chip"
              onClick={() => setQuery(s)}
            >
              {s}
            </button>
          ))}
        </div>
      )}

      {response && !loading && !error && (
        <div className="search-meta">
          <span>
            <strong>{response.total.toLocaleString()}</strong> results
          </span>
          <span>{response.took_ms.toFixed(0)} ms</span>
          {response.cache_hit && <span>served from cache</span>}
        </div>
      )}

      {error && (
        <ErrorState
          title="Search failed"
          description={error}
          onRetry={() => runSearch(query, category, page)}
        />
      )}

      {!error && loading && (
        <div className="result-list">
          {[...Array(3)].map((_, i) => (
            <ResultSkeleton key={i} />
          ))}
        </div>
      )}

      {!error &&
        !loading &&
        response &&
        response.results.length === 0 && (
          <EmptyState
            title="No results found"
            description="Try a different search term, or remove a filter."
          />
        )}

      {!error &&
        !loading &&
        response &&
        response.results.length > 0 && (
          <>
            <ResultList results={response.results} />
            <Pagination
              page={page}
              totalPages={totalPages}
              onChange={setPage}
            />
          </>
        )}
    </div>
  );
}
