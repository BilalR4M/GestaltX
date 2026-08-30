export type Citation = {
  path: string;
  title?: string;
  section?: string;
  quote?: string;
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
  trace?: TraceIteration[];
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export async function askQuestion(question: string, signal?: AbortSignal): Promise<ResearchAnswer> {
  const response = await fetch(`${API_URL}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
    signal
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Research request failed (${response.status})`);
  }
  return response.json() as Promise<ResearchAnswer>;
}

export function researchStreamUrl(question: string): string {
  return `${API_URL}/ask/stream?question=${encodeURIComponent(question)}`;
}
