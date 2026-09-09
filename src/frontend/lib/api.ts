export type Citation = {
  path: string;
  title?: string;
  section?: string;
  quote?: string;
  authority?: string;
  role?: string;
};

export type ReasoningStep = {
  step: number;
  phase: "thought" | "search" | "finding" | "judgment" | string;
  title: string;
  narrative: string;
  query?: string | null;
  sources?: string[];
  highlights?: string[];
};

export type ActivityEvent = {
  kind: "tool_start" | "tool_end" | "status" | string;
  tool?: string;
  query?: string;
  iteration?: number;
  id?: string;
  hit_count?: number;
  sources?: string[];
  message?: string;
};

export type AnswerChunk = {
  section: "answer" | "documents" | "why" | "how" | "sources" | string;
  markdown: string;
};

export type TraceIteration = {
  iteration: number;
  gap: string;
  query: string;
  sources: string[];
};

export type ResearchAnswer = {
  answer: string;
  citations: Citation[];
  confidence: number;
  confidence_label?: string;
  confidence_note?: string;
  trace?: TraceIteration[];
  reasoning?: ReasoningStep[];
  mode?: "llm" | "heuristic" | string;
  structured?: boolean;
  sections?: Partial<
    Record<"answer" | "documents" | "why" | "how" | "sources" | "verdict" | "reasoning" | "evidence", string>
  >;
};

export type FeedItem =
  | { type: "reasoning"; id: string; data: ReasoningStep }
  | { type: "tool"; id: string; data: ToolCardState }
  | { type: "status"; id: string; data: { message: string } };

export type ToolCardState = {
  id: string;
  tool: string;
  query: string;
  status: "running" | "done";
  hitCount?: number;
  sources?: string[];
  iteration?: number;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export type CorpusRecentItem = {
  path?: string;
  title: string;
  kind: string;
  tier?: number;
};

export type CorpusStatus = {
  version: number;
  documents: number;
  chunks: number;
  watching: boolean;
  last_refresh?: string | null;
  recent: CorpusRecentItem[];
  updated_at?: string | null;
};

export async function corpusStatus(signal?: AbortSignal): Promise<CorpusStatus> {
  const response = await fetch(`${API_URL}/api/corpus`, { signal });
  if (!response.ok) {
    throw new Error(`Corpus status failed (${response.status})`);
  }
  const raw = (await response.json()) as Record<string, unknown>;
  const recentRaw = Array.isArray(raw.recent) ? raw.recent : [];
  return {
    version: Number(raw.version ?? 0),
    documents: Number(raw.documents ?? 0),
    chunks: Number(raw.chunks ?? 0),
    watching: Boolean(raw.watching),
    last_refresh: raw.last_refresh ? String(raw.last_refresh) : null,
    updated_at: raw.updated_at ? String(raw.updated_at) : null,
    recent: recentRaw.map((item) => {
      const row = item as Record<string, unknown>;
      return {
        path: row.path ? String(row.path) : undefined,
        title: String(row.title ?? row.path ?? "document"),
        kind: String(row.kind ?? "document"),
        tier: row.tier != null ? Number(row.tier) : undefined
      };
    })
  };
}

export async function askQuestion(question: string, signal?: AbortSignal): Promise<ResearchAnswer> {
  const response = await fetch(`${API_URL}/api/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
    signal
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Research request failed (${response.status})`);
  }
  return normalizeAnswer(await response.json());
}

export function researchStreamUrl(question: string): string {
  return `${API_URL}/api/ask/stream?question=${encodeURIComponent(question)}`;
}

export function normalizeReasoningStep(raw: Record<string, unknown>): ReasoningStep {
  return {
    step: Number(raw.step ?? 0),
    phase: String(raw.phase ?? "thought"),
    title: String(raw.title ?? "Thinking"),
    narrative: String(raw.narrative ?? ""),
    query: raw.query ? String(raw.query) : null,
    sources: Array.isArray(raw.sources) ? raw.sources.map(String) : [],
    highlights: Array.isArray(raw.highlights) ? raw.highlights.map(String) : []
  };
}

export function normalizeActivity(raw: Record<string, unknown>): ActivityEvent {
  return {
    kind: String(raw.kind ?? "status"),
    tool: raw.tool ? String(raw.tool) : undefined,
    query: raw.query ? String(raw.query) : undefined,
    iteration: raw.iteration != null ? Number(raw.iteration) : undefined,
    id: raw.id ? String(raw.id) : undefined,
    hit_count: raw.hit_count != null ? Number(raw.hit_count) : undefined,
    sources: Array.isArray(raw.sources) ? raw.sources.map(String) : undefined,
    message: raw.message ? String(raw.message) : undefined
  };
}

export function normalizeAnswerChunk(raw: Record<string, unknown>): AnswerChunk {
  return {
    section: String(raw.section ?? "answer"),
    markdown: String(raw.markdown ?? "")
  };
}

export function normalizeAnswer(raw: Record<string, unknown>): ResearchAnswer {
  const citationsRaw = Array.isArray(raw.citations) ? raw.citations : [];
  const citations: Citation[] = citationsRaw.map((item) => {
    if (typeof item === "string") return { path: item, title: item };
    const row = item as Record<string, unknown>;
    const path = String(row.path ?? row.source ?? row.id ?? "source");
    return {
      path,
      title: String(row.title ?? path),
      section: row.section ? String(row.section) : undefined,
      quote: row.quote ? String(row.quote) : undefined,
      authority: row.authority ? String(row.authority) : undefined,
      role: row.role ? String(row.role) : undefined
    };
  });
  const confidence = Number(raw.confidence ?? 0);
  const reasoningRaw = Array.isArray(raw.reasoning) ? raw.reasoning : [];
  const sectionsRaw = (raw.sections as Record<string, unknown> | undefined) ?? {};
  return {
    answer: String(raw.answer ?? ""),
    citations,
    confidence: confidence > 1 ? confidence / 100 : confidence,
    confidence_label: raw.confidence_label ? String(raw.confidence_label) : undefined,
    confidence_note: raw.confidence_note ? String(raw.confidence_note) : undefined,
    trace: Array.isArray(raw.trace) ? (raw.trace as TraceIteration[]) : undefined,
    reasoning: reasoningRaw.map((item) => normalizeReasoningStep(item as Record<string, unknown>)),
    mode: raw.mode ? String(raw.mode) : undefined,
    structured: Boolean(raw.structured),
    sections: {
      answer: sectionsRaw.answer ? String(sectionsRaw.answer) : sectionsRaw.verdict ? String(sectionsRaw.verdict) : undefined,
      documents: sectionsRaw.documents ? String(sectionsRaw.documents) : undefined,
      why: sectionsRaw.why ? String(sectionsRaw.why) : sectionsRaw.reasoning ? String(sectionsRaw.reasoning) : undefined,
      how: sectionsRaw.how ? String(sectionsRaw.how) : undefined,
      sources: sectionsRaw.sources ? String(sectionsRaw.sources) : sectionsRaw.evidence ? String(sectionsRaw.evidence) : undefined
    }
  };
}
