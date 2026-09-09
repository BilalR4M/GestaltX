import type { ActivityEvent, AnswerChunk, ResearchAnswer, ReasoningStep, TraceIteration } from "./api";
import { normalizeActivity, normalizeAnswer, normalizeAnswerChunk, normalizeReasoningStep } from "./api";

export type ResearchEvent =
  | { type: "reasoning"; data: ReasoningStep }
  | { type: "activity"; data: ActivityEvent }
  | { type: "answer_chunk"; data: AnswerChunk }
  | { type: "iteration"; data: TraceIteration }
  | { type: "answer"; data: ResearchAnswer }
  | { type: "error"; data: { message: string } };

type BackendEnvelope = {
  event?: string;
  data?: Record<string, unknown>;
};

export function streamResearch(
  url: string,
  onEvent: (event: ResearchEvent) => void,
  onError?: (error: Error) => void
): () => void {
  const source = new EventSource(url);
  let closedByAnswer = false;
  let lastQuery = "";
  let lastSources: string[] = [];
  let sawPayload = false;
  let sawReasoning = false;

  const emitIteration = (partial: Partial<TraceIteration> & { iteration: number }) => {
    if (sawReasoning) return;
    onEvent({
      type: "iteration",
      data: {
        iteration: partial.iteration,
        gap: partial.gap ?? "Gathering evidence",
        query: partial.query ?? lastQuery,
        sources: partial.sources ?? lastSources
      }
    });
  };

  const handleNamed = (eventName: string) => (raw: MessageEvent<string>) => {
    try {
      sawPayload = true;
      const payload = JSON.parse(raw.data) as Record<string, unknown>;
      if (eventName === "reasoning") {
        sawReasoning = true;
        onEvent({ type: "reasoning", data: normalizeReasoningStep(payload) });
        return;
      }
      if (eventName === "activity") {
        onEvent({ type: "activity", data: normalizeActivity(payload) });
        return;
      }
      if (eventName === "answer_chunk") {
        onEvent({ type: "answer_chunk", data: normalizeAnswerChunk(payload) });
        return;
      }
      if (eventName === "plan") {
        const queries = Array.isArray(payload.queries) ? payload.queries.map(String) : [];
        lastQuery = queries[0] ?? "";
        emitIteration({
          iteration: 0,
          gap: "Plan research steps",
          query: lastQuery || "planning",
          sources: Array.isArray(payload.entities) ? payload.entities.map(String) : []
        });
        return;
      }
      if (eventName === "tool_call") {
        lastQuery = String(payload.query ?? lastQuery);
        emitIteration({
          iteration: Number(payload.iteration ?? 1),
          gap: "Searching the archive",
          query: lastQuery,
          sources: []
        });
        return;
      }
      if (eventName === "tool_result") {
        const results = Array.isArray(payload.results) ? payload.results : [];
        lastSources = Array.from(
          new Set(
            results
              .map((row) => {
                const item = row as Record<string, unknown>;
                return String(item.path ?? item.source ?? item.doc_id ?? "");
              })
              .filter(Boolean)
          )
        ).slice(0, 6);
        emitIteration({
          iteration: Number(payload.iteration ?? 1),
          gap: "Reading the matches",
          query: lastQuery,
          sources: lastSources
        });
        return;
      }
      if (eventName === "critique") {
        const reasons = Array.isArray(payload.reasons) ? payload.reasons.map(String) : [];
        const next = (payload.next_action as Record<string, unknown> | null) ?? null;
        emitIteration({
          iteration: Number(payload.iteration ?? 1),
          gap: reasons.join("; ") || (payload.sufficient ? "Have enough evidence" : "Need more searching"),
          query: String(next?.query ?? lastQuery),
          sources: lastSources
        });
        return;
      }
      if (eventName === "answer" || eventName === "iteration") {
        if (eventName === "iteration") {
          onEvent({ type: "iteration", data: payload as unknown as TraceIteration });
          return;
        }
        closedByAnswer = true;
        onEvent({ type: "answer", data: normalizeAnswer(payload) });
        source.close();
      }
    } catch {
      onError?.(new Error("The archive returned an unexpected response."));
      source.close();
    }
  };

  for (const name of [
    "reasoning",
    "activity",
    "answer_chunk",
    "plan",
    "tool_call",
    "tool_result",
    "critique",
    "answer",
    "iteration",
    "error"
  ]) {
    source.addEventListener(name, handleNamed(name));
  }

  source.onmessage = (raw) => {
    try {
      sawPayload = true;
      const envelope = JSON.parse(raw.data) as BackendEnvelope;
      if (envelope.event && envelope.data) {
        handleNamed(envelope.event)({ data: JSON.stringify(envelope.data) } as MessageEvent<string>);
      }
    } catch {
      // ignore unnamed frames
    }
  };

  source.onerror = () => {
    if (closedByAnswer) return;
    if (!sawPayload) {
      onError?.(
        new Error(
          "Connection lost. Is the backend running at http://127.0.0.1:8000?"
        )
      );
    } else {
      onError?.(new Error("Connection lost before the answer was complete."));
    }
    source.close();
  };

  return () => source.close();
}
