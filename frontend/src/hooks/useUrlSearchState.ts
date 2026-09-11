import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router-dom";

interface UrlSearchState {
  q: string;
  category: string;
  page: number;
  sortBy: string;
}

export function useUrlSearchState(): [UrlSearchState, (patch: Partial<UrlSearchState>) => void] {
  const [params, setParams] = useSearchParams();

  const state = useMemo<UrlSearchState>(
    () => ({
      q: params.get("q") ?? "",
      category: params.get("category") ?? "",
      page: Number(params.get("page") ?? "1"),
      sortBy: params.get("sort") ?? "relevance",
    }),
    [params]
  );

  const update = useCallback(
    (patch: Partial<UrlSearchState>) => {
      const next = { ...state, ...patch };
      const nextParams = new URLSearchParams();
      if (next.q) nextParams.set("q", next.q);
      if (next.category) nextParams.set("category", next.category);
      if (next.page && next.page !== 1) nextParams.set("page", String(next.page));
      if (next.sortBy && next.sortBy !== "relevance") nextParams.set("sort", next.sortBy);
      setParams(nextParams, { replace: true });
    },
    [state, setParams]
  );

  return [state, update];
}
