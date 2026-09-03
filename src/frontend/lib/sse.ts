import type { ResearchAnswer, TraceIteration } from "./api";

export type ResearchEvent =
  | { type: "iteration"; data: TraceIteration }
  | { type: "answer"; data: ResearchAnswer }
  | { type: "error"; data: { message: string } };

export function streamResearch(
  url: string,
  onEvent: (event: ResearchEvent) => void,
  onError?: (error: Error) => void
): () => void {
  const source = new EventSource(url);
  const consume = (type: ResearchEvent["type"]) => (raw: MessageEvent<string>) => {
    try {
      onEvent({ type, data: JSON.parse(raw.data) } as ResearchEvent);
      if (type === "answer") source.close();
    } catch {
      onError?.(new Error("The research stream returned invalid JSON."));
      source.close();
    }
  };
  source.addEventListener("iteration", consume("iteration"));
  source.addEventListener("answer", consume("answer"));
  source.addEventListener("error", () => {
    onError?.(new Error("Connection to the research stream was lost."));
    source.close();
  });
  return () => source.close();
}
