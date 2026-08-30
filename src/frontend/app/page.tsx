"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { AnswerPanel } from "@/components/AnswerPanel";
import { QuestionPicker } from "@/components/QuestionPicker";
import { ResearchTrace } from "@/components/ResearchTrace";
import type { ResearchAnswer, TraceIteration } from "@/lib/api";
import { researchStreamUrl } from "@/lib/api";
import { streamResearch } from "@/lib/sse";

export default function Home() {
  const [question, setQuestion] = useState("In what year was Gloamreach founded?");
  const [iterations, setIterations] = useState<TraceIteration[]>([]);
  const [result, setResult] = useState<ResearchAnswer | null>(null);
  const [status, setStatus] = useState<"idle" | "researching" | "error">("idle");
  const [error, setError] = useState("");
  const stopRef = useRef<(() => void) | null>(null);
  useEffect(() => () => stopRef.current?.(), []);

  function submit(event?: FormEvent) {
    event?.preventDefault();
    const cleanQuestion = question.trim();
    if (!cleanQuestion || status === "researching") return;
    stopRef.current?.();
    setIterations([]);
    setResult(null);
    setError("");
    setStatus("researching");
    stopRef.current = streamResearch(
      researchStreamUrl(cleanQuestion),
      (message) => {
        if (message.type === "iteration") setIterations((current) => [...current, message.data]);
        if (message.type === "answer") {
          setResult(message.data);
          setStatus("idle");
        }
        if (message.type === "error") {
          setError(message.data.message);
          setStatus("error");
        }
      },
      (reason) => {
        setError(reason.message);
        setStatus("error");
      }
    );
  }

  return (
    <main>
      <header className="hero">
        <div className="brand"><span>GX</span> GESTALTX / ARCHIVE RESEARCH</div>
        <h1>Search like a researcher,<br /><em>not a keyword box.</em></h1>
        <p>GestaltX follows documentary pointers, identifies evidence gaps, and arbitrates conflicting sources before answering.</p>
      </header>
      <section className="ask">
        <QuestionPicker disabled={status === "researching"} onPick={setQuestion} />
        <form onSubmit={submit}>
          <label htmlFor="question">Ask the Ashen Era Archive</label>
          <div className="input-row">
            <textarea id="question" value={question} onChange={(event) => setQuestion(event.target.value)} rows={2} />
            <button disabled={!question.trim() || status === "researching"}>
              {status === "researching" ? "Researching…" : "Begin research"}
            </button>
          </div>
        </form>
        {error && <p className="error" role="alert">{error}</p>}
      </section>
      <div className="workspace">
        <ResearchTrace iterations={iterations} />
        <AnswerPanel result={result} />
      </div>
    </main>
  );
}
