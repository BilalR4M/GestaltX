"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { AnswerPanel } from "@/components/AnswerPanel";
import { QuestionPicker } from "@/components/QuestionPicker";
import { ResearchTrace } from "@/components/ResearchTrace";
import type { FeedItem, ResearchAnswer, ToolCardState, TraceIteration } from "@/lib/api";
import { corpusStatus, researchStreamUrl } from "@/lib/api";
import { streamResearch } from "@/lib/sse";

const SECTION_ORDER = ["answer", "documents", "why", "how", "sources"] as const;

export default function Home() {
  const [question, setQuestion] = useState("In what year was Gloamreach founded?");
  const [feed, setFeed] = useState<FeedItem[]>([]);
  const [iterations, setIterations] = useState<TraceIteration[]>([]);
  const [result, setResult] = useState<ResearchAnswer | null>(null);
  const [partialSections, setPartialSections] = useState<Partial<Record<(typeof SECTION_ORDER)[number], string>>>({});
  const [status, setStatus] = useState<"idle" | "researching" | "error">("idle");
  const [error, setError] = useState("");
  const [statusLine, setStatusLine] = useState("Ready to research the document archive.");
  const [archiveChip, setArchiveChip] = useState("");
  const stopRef = useRef<(() => void) | null>(null);
  const stepCounter = useRef(0);
  const corpusVersionRef = useRef<number | null>(null);
  const chipTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => () => {
    stopRef.current?.();
    if (chipTimerRef.current) clearTimeout(chipTimerRef.current);
  }, []);

  useEffect(() => {
    if (status === "researching") return;
    let cancelled = false;
    const controller = new AbortController();

    async function poll() {
      try {
        const corpus = await corpusStatus(controller.signal);
        if (cancelled) return;
        const previous = corpusVersionRef.current;
        corpusVersionRef.current = corpus.version;
        if (previous != null && corpus.version > previous) {
          const recent = corpus.recent?.[0];
          const label = recent ? `${recent.title} (${recent.kind})` : "new material";
          const count = Math.max(1, corpus.recent?.length || 1);
          const noun = count === 1 ? "document" : "documents";
          setArchiveChip(
            count === 1
              ? `Document archive updated — 1 new ${noun}: ${label}`
              : `Document archive updated — ${count} ${noun}, including ${label}`
          );
          if (chipTimerRef.current) clearTimeout(chipTimerRef.current);
          chipTimerRef.current = setTimeout(() => setArchiveChip(""), 8000);
        }
      } catch {
        // API may be restarting; ignore transient poll failures.
      }
    }

    poll();
    const id = setInterval(poll, 4000);
    return () => {
      cancelled = true;
      controller.abort();
      clearInterval(id);
    };
  }, [status]);

  const partialMarkdown = SECTION_ORDER
    .map((key) => partialSections[key])
    .filter(Boolean)
    .join("\n\n");

  function upsertTool(updater: (current: ToolCardState | undefined) => ToolCardState) {
    setFeed((current) => {
      const next = [...current];
      const draft = updater(undefined);
      const index = next.findIndex((item) => item.type === "tool" && item.id === draft.id);
      const item: FeedItem = { type: "tool", id: draft.id, data: draft };
      if (index >= 0) {
        const previous = next[index].type === "tool" ? next[index].data : undefined;
        item.data = updater(previous);
        next[index] = item;
      } else {
        next.push(item);
      }
      return next;
    });
  }

  function submit(event?: FormEvent) {
    event?.preventDefault();
    const cleanQuestion = question.trim();
    if (!cleanQuestion || status === "researching") return;
    stopRef.current?.();
    stepCounter.current = 0;
    setFeed([]);
    setIterations([]);
    setResult(null);
    setPartialSections({});
    setError("");
    setStatus("researching");
    setStatusLine("Beginning the investigation…");
    stopRef.current = streamResearch(
      researchStreamUrl(cleanQuestion),
      (message) => {
        if (message.type === "activity") {
          const activity = message.data;
          if (activity.kind === "tool_start") {
            const id = activity.id || `tool-${activity.iteration ?? Date.now()}`;
            upsertTool(() => ({
              id,
              tool: activity.tool || "search_corpus",
              query: activity.query || "",
              status: "running",
              iteration: activity.iteration
            }));
            setStatusLine(`Searching: ${activity.query || "documents"}…`);
          } else if (activity.kind === "tool_end") {
            const id = activity.id || `tool-${activity.iteration ?? Date.now()}`;
            upsertTool((previous) => ({
              id,
              tool: activity.tool || previous?.tool || "search_corpus",
              query: activity.query || previous?.query || "",
              status: "done",
              hitCount: activity.hit_count,
              sources: activity.sources || [],
              iteration: activity.iteration
            }));
            setStatusLine(
              activity.hit_count != null
                ? `Found ${activity.hit_count} document matches`
                : "Search complete"
            );
          } else if (activity.kind === "status" && activity.message) {
            const id = `status-${++stepCounter.current}`;
            setFeed((current) => [
              ...current,
              { type: "status", id, data: { message: activity.message || "" } }
            ]);
            setStatusLine(activity.message);
          }
        }
        if (message.type === "reasoning") {
          const id = `reason-${message.data.step}-${++stepCounter.current}`;
          setFeed((current) => [...current, { type: "reasoning", id, data: message.data }]);
          setStatusLine(message.data.title || message.data.narrative || "Working…");
        }
        if (message.type === "answer_chunk") {
          const section = message.data.section as (typeof SECTION_ORDER)[number];
          if (SECTION_ORDER.includes(section)) {
            setPartialSections((current) => ({
              ...current,
              [section]: message.data.markdown
            }));
            setStatusLine(
              section === "answer"
                ? "Drafting answer…"
                : section === "documents"
                  ? "Listing what the documents say…"
                  : section === "why"
                    ? "Explaining why…"
                    : section === "how"
                      ? "Summarizing the path…"
                      : "Attaching sources…"
            );
          }
        }
        if (message.type === "iteration") {
          setIterations((current) => [...current, message.data]);
          setStatusLine(message.data.gap || "Working…");
        }
        if (message.type === "answer") {
          setResult(message.data);
          if (message.data.answer) {
            setPartialSections({});
          }
          setStatus("idle");
          setStatusLine(
            message.data.mode === "llm"
              ? "Answer drafted with AI assistance."
              : "Answer built directly from the documents."
          );
        }
        if (message.type === "error") {
          setError(message.data.message);
          setStatus("error");
          setStatusLine("Research interrupted.");
        }
      },
      (reason) => {
        setError(reason.message);
        setStatus("error");
        setStatusLine("Connection interrupted. Please try again.");
      }
    );
  }

  return (
    <main>
      <header className="hero">
        <div className="brand"><span>GX</span> DOCUMENT RESEARCH</div>
        <h1 className="product-name">GESTALTX</h1>
        <p className="tagline">
          Search like a researcher, <em>not a keyword box.</em> Watch the research happen live,
          then get a plain-language answer with citations. Point it at any mixed corpus —
          official records, community notes, and loose papers.
        </p>
        {archiveChip ? (
          <p className="archive-chip" role="status">{archiveChip}</p>
        ) : null}
      </header>
      <section className="ask">
        <QuestionPicker disabled={status === "researching"} onPick={setQuestion} />
        <form onSubmit={submit}>
          <label htmlFor="question">Ask the Document Archive</label>
          <div className="input-row">
            <textarea
              id="question"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              rows={2}
              placeholder="Ask about a date, person, place, or disputed claim across your documents…"
            />
            <button disabled={!question.trim() || status === "researching"}>
              {status === "researching" ? "Researching…" : "Begin research"}
            </button>
          </div>
        </form>
        <p className={`status-line ${status}`}>{statusLine}</p>
        {error && <p className="error" role="alert">{error}</p>}
      </section>
      <div className="workspace">
        <ResearchTrace
          feed={feed}
          iterations={iterations}
          busy={status === "researching"}
        />
        <AnswerPanel
          result={result}
          busy={status === "researching"}
          workingLabel={statusLine}
          partialMarkdown={partialMarkdown}
        />
      </div>
      <footer className="site-footer">
        © 2026 GestaltX · Built by <em>“It works on my computer”</em> team
      </footer>
    </main>
  );
}
