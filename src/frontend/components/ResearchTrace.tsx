"use client";

import { useEffect, useRef, useState } from "react";
import { ToolActivityCard } from "@/components/ToolActivityCard";
import type { FeedItem, ReasoningStep, TraceIteration } from "@/lib/api";

const PHASE_LABEL: Record<string, string> = {
  thought: "Thought",
  search: "Search",
  finding: "Finding",
  judgment: "Judgment"
};

function rich(text: string) {
  return text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g).filter(Boolean).map((part, index) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={index}>{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith("`") && part.endsWith("`")) {
      return <code key={index}>{part.slice(1, -1)}</code>;
    }
    return <span key={index}>{part}</span>;
  });
}

function ReasoningRow({
  item,
  index,
  expanded,
  active,
  onToggle
}: {
  item: ReasoningStep;
  index: number;
  expanded: boolean;
  active: boolean;
  onToggle: () => void;
}) {
  return (
    <li className={`trace-item thought-step${active ? " active" : ""}${expanded ? "" : " collapsed"}`}>
      <span className="iteration">{String(index + 1).padStart(2, "0")}</span>
      <div>
        <button type="button" className="step-toggle" onClick={onToggle} aria-expanded={expanded}>
          <span className={`phase-chip phase-${item.phase}`}>
            {PHASE_LABEL[item.phase] ?? item.phase}
          </span>
          <span className="trace-title">{item.title}</span>
          <span className="chevron" aria-hidden="true">{expanded ? "▾" : "▸"}</span>
        </button>
        {expanded && (
          <div className="step-body">
            <p className="trace-narrative">{rich(item.narrative)}</p>
            {item.query && (
              <p className="trace-query"><code>{item.query}</code></p>
            )}
            {item.highlights && item.highlights.length > 0 && (
              <div className="highlight-list">
                {item.highlights.map((line, hi) => (
                  <span key={`hi-${index}-${hi}`}>{line}</span>
                ))}
              </div>
            )}
            {item.sources && item.sources.length > 0 && (
              <div className="source-list">
                {item.sources.map((source, sourceIndex) => (
                  <span key={`src-${index}-${sourceIndex}`}>{source}</span>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </li>
  );
}

function LegacyTrace({ iterations }: { iterations: TraceIteration[] }) {
  return (
    <ol className="trace-list">
      {iterations.map((item, index) => (
        <li key={`legacy-${index}`} className="trace-item">
          <span className="iteration">{String(index + 1).padStart(2, "0")}</span>
          <div>
            <p className="trace-title">{item.gap}</p>
            {item.query && <p className="trace-query"><code>{item.query}</code></p>}
            <div className="source-list">
              {item.sources.map((source, sourceIndex) => (
                <span key={`src-${index}-${sourceIndex}`}>{source}</span>
              ))}
            </div>
          </div>
        </li>
      ))}
    </ol>
  );
}

export function ResearchTrace({
  feed,
  iterations,
  busy
}: {
  feed: FeedItem[];
  iterations?: TraceIteration[];
  busy?: boolean;
}) {
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [feed.length, busy]);

  useEffect(() => {
    // Auto-expand the latest item; collapse older reasoning when busy.
    if (!feed.length) return;
    setExpanded((current) => {
      const next = { ...current };
      feed.forEach((item, index) => {
        const isLast = index === feed.length - 1;
        if (item.type === "tool") {
          next[item.id] = item.data.status === "running" || isLast;
        } else if (item.type === "reasoning") {
          next[item.id] = isLast || (!busy && item.data.phase === "judgment");
        } else {
          next[item.id] = isLast;
        }
      });
      return next;
    });
  }, [feed, busy]);

  const count = feed.length || iterations?.length || 0;
  const usingFeed = feed.length > 0;
  let reasoningIndex = 0;

  return (
    <section className="panel activity-panel" aria-labelledby="trace-heading">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Live process</p>
          <h2 id="trace-heading">Research steps</h2>
        </div>
        <span className="count">{count} steps</span>
      </div>
      {count === 0 ? (
        <p className="empty">
          {busy
            ? "Beginning the investigation…"
            : "Watch each step of the research as it happens."}
        </p>
      ) : usingFeed ? (
        <ol className="trace-list thought-stream activity-feed">
          {feed.map((item) => {
            if (item.type === "tool") {
              return (
                <li key={item.id} className="trace-item tool-row">
                  <span className="iteration">··</span>
                  <ToolActivityCard tool={item.data} />
                </li>
              );
            }
            if (item.type === "status") {
              return (
                <li key={item.id} className="trace-item status-row">
                  <span className="iteration">··</span>
                  <p className="status-pill">{item.data.message}</p>
                </li>
              );
            }
            const index = reasoningIndex++;
            const isActive = Boolean(busy && feed[feed.length - 1]?.id === item.id);
            return (
              <ReasoningRow
                key={item.id}
                item={item.data}
                index={index}
                expanded={expanded[item.id] ?? isActive}
                active={isActive}
                onToggle={() =>
                  setExpanded((current) => ({
                    ...current,
                    [item.id]: !(current[item.id] ?? false)
                  }))
                }
              />
            );
          })}
          <div ref={bottomRef} />
        </ol>
      ) : (
        <LegacyTrace iterations={iterations ?? []} />
      )}
    </section>
  );
}
