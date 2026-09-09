"use client";

import type { ToolCardState } from "@/lib/api";

const TOOL_LABEL: Record<string, string> = {
  search_corpus: "Searching the archive",
  injected_evidence: "Reading the evidence"
};

export function ToolActivityCard({ tool }: { tool: ToolCardState }) {
  const running = tool.status === "running";
  const label = TOOL_LABEL[tool.tool] ?? tool.tool;

  return (
    <div className={`tool-card${running ? " running" : " done"}`}>
      <div className="tool-card-head">
        {running ? <span className="spinner" aria-hidden="true" /> : <span className="tool-check" aria-hidden="true">✓</span>}
        <div>
          <p className="tool-name">
            <code>{label}</code>
            {running ? <span className="tool-state">Searching…</span> : (
              <span className="tool-state">
                {tool.hitCount != null ? `${tool.hitCount} matches` : "Complete"}
              </span>
            )}
          </p>
          {tool.query && <p className="tool-query"><code>{tool.query}</code></p>}
        </div>
      </div>
      {!running && tool.sources && tool.sources.length > 0 && (
        <div className="source-list">
          {tool.sources.map((source) => (
            <span key={source}>{source}</span>
          ))}
        </div>
      )}
    </div>
  );
}
