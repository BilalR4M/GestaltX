import type { ResearchAnswer } from "@/lib/api";

export function AnswerPanel({ result }: { result: ResearchAnswer | null }) {
  if (!result) {
    return (
      <section className="panel answer-panel" aria-live="polite">
        <p className="eyebrow">Evidence-backed result</p>
        <h2>Answer</h2>
        <p className="empty">The final answer, confidence, and citations will appear here.</p>
      </section>
    );
  }
  const confidence = Math.max(0, Math.min(100, Math.round(result.confidence * 100)));
  return (
    <section className="panel answer-panel" aria-live="polite">
      <div className="panel-heading">
        <div><p className="eyebrow">Evidence-backed result</p><h2>Answer</h2></div>
        <span className="confidence">{confidence}% confidence</span>
      </div>
      <p className="answer-copy">{result.answer}</p>
      <div className="confidence-track"><span style={{ width: `${confidence}%` }} /></div>
      <h3>Citations</h3>
      {result.citations.length ? (
        <ol className="citations">
          {result.citations.map((citation, index) => (
            <li key={`${citation.path}-${index}`}>
              <a href={`file://${citation.path}`} title={citation.path}>
                {citation.title ?? citation.path}
              </a>
              {citation.section && <span> · {citation.section}</span>}
              {citation.quote && <blockquote>{citation.quote}</blockquote>}
            </li>
          ))}
        </ol>
      ) : <p className="empty">No citations were returned.</p>}
    </section>
  );
}
