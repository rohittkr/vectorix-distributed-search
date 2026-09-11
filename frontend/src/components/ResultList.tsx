import type { SearchResultItem } from "../types/api";

function Highlighted({ item }: { item: SearchResultItem }) {
  const snippet = item.highlight?.content?.[0] ?? item.description ?? "";
  return <p className="result-snippet" dangerouslySetInnerHTML={{ __html: snippet }} />;
}

export default function ResultList({ results }: { results: SearchResultItem[] }) {
  return (
    <div className="result-list">
      {results.map((item) => (
        <article className="result-item" key={item.id}>
          <h3 className="result-title">
            <a href={item.url ?? "#"} target="_blank" rel="noreferrer">
              {item.title}
            </a>
          </h3>
          {item.url && <div className="result-url">{item.url}</div>}
          <Highlighted item={item} />
          {item.tags.length > 0 && (
            <div className="result-tags">
              {item.tags.map((tag) => (
                <span className="result-tag" key={tag}>
                  {tag}
                </span>
              ))}
            </div>
          )}
        </article>
      ))}
    </div>
  );
}
