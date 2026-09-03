import type { TraceIteration } from "@/lib/api";

export function ResearchTrace({ iterations }: { iterations: TraceIteration[] }) {
  return (
    <section className="panel" aria-labelledby="trace-heading">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Live process</p>
          <h2 id="trace-heading">Research trace</h2>
        </div>
        <span className="count">{iterations.length} iterations</span>
      </div>
      {iterations.length === 0 ? (
        <p className="empty">Research gaps, reformulated queries, and consulted sources appear here.</p>
      ) : (
        <ol className="trace-list">
          {iterations.map((item) => (
            <li key={`${item.iteration}-${item.query}`} className="trace-item">
              <span className="iteration">{String(item.iteration).padStart(2, "0")}</span>
              <div>
                <p><strong>Gap</strong> {item.gap}</p>
                <p><strong>Query</strong> <code>{item.query}</code></p>
                <div className="source-list">
                  {item.sources.map((source) => <span key={source}>{source}</span>)}
                </div>
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
