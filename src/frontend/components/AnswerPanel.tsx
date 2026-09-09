import type { ResearchAnswer } from "@/lib/api";

function renderRichText(text: string) {
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`|\[\d+\])/g).filter(Boolean);
  return parts.map((part, index) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={index}>{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith("`") && part.endsWith("`")) {
      return <code key={index}>{part.slice(1, -1)}</code>;
    }
    if (/^\[\d+\]$/.test(part)) {
      return <span key={index} className="cite-chip">{part}</span>;
    }
    return <span key={index}>{part}</span>;
  });
}

function StructuredAnswer({ markdown }: { markdown: string }) {
  const blocks = markdown
    .split(/\n(?=## )/)
    .map((block) => block.trim())
    .filter(Boolean);

  return (
    <div className="structured-answer">
      {blocks.map((block, index) => {
        const lines = block.split("\n");
        const heading = lines[0].replace(/^##\s*/, "");
        const body = lines.slice(1).join("\n").trim();
        const headingKey = heading.toLowerCase();
        const isAnswer = headingKey === "answer" || headingKey === "verdict";
        const isSources = headingKey === "sources" || headingKey === "evidence";
        const isHow = headingKey.startsWith("how");

        if (isSources) {
          const entries = body.split(/\n(?=\[\d+\])/).map((e) => e.trim()).filter(Boolean);
          return (
            <section key={`${heading}-${index}`} className="answer-section sources-section reveal">
              <h3>{heading}</h3>
              <ol className="source-dossier">
                {entries.map((entry, entryIndex) => {
                  const entryLines = entry.split("\n").map((l) => l.trim()).filter(Boolean);
                  const head = entryLines[0] || "";
                  const quoteLine = entryLines.find((l) => l.startsWith('"') || l.startsWith("'"));
                  const pathLine = entryLines.find((l) => l.startsWith("`") && l.endsWith("`"));
                  return (
                    <li key={entryIndex} className="source-row">
                      <p className="source-title">{renderRichText(head)}</p>
                      {quoteLine && <blockquote>{quoteLine.replace(/^"|"$/g, "")}</blockquote>}
                      {pathLine && <p className="source-path"><code>{pathLine.slice(1, -1)}</code></p>}
                    </li>
                  );
                })}
              </ol>
            </section>
          );
        }

        const bullets = body
          .split("\n")
          .map((line) => line.trim())
          .filter((line) => line.startsWith("- ") || /^\d+\.\s/.test(line))
          .map((line) => line.replace(/^- /, "").replace(/^\d+\.\s*/, ""));
        const prose = body
          .split(/\n\s*\n/)
          .map((para) => para.trim())
          .filter(
            (para) =>
              para &&
              !para.split("\n").every((line) => line.trim().startsWith("- ") || /^\d+\.\s/.test(line.trim()))
          );
        const proseLines = prose.length
          ? prose
          : body
              .split("\n")
              .map((line) => line.trim())
              .filter((line) => line && !line.startsWith("- ") && !/^\d+\.\s/.test(line));

        return (
          <section
            key={`${heading}-${index}`}
            className={`answer-section reveal${isAnswer ? " verdict-section" : ""}`}
          >
            <h3>{heading}</h3>
            {proseLines.map((line, lineIndex) => (
              <p key={lineIndex} className={isAnswer ? "verdict-copy" : "answer-copy"}>
                {renderRichText(line)}
              </p>
            ))}
            {bullets.length > 0 && (
              <ul className={isHow ? "how-list" : undefined}>
                {bullets.map((item, bulletIndex) => (
                  <li key={bulletIndex}>{renderRichText(item)}</li>
                ))}
              </ul>
            )}
          </section>
        );
      })}
    </div>
  );
}

export function AnswerPanel({
  result,
  busy,
  workingLabel,
  partialMarkdown
}: {
  result: ResearchAnswer | null;
  busy?: boolean;
  workingLabel?: string;
  partialMarkdown?: string;
}) {
  const liveMarkdown = result?.answer || partialMarkdown || "";
  const showLive = Boolean(liveMarkdown);
  const confidence = result
    ? Math.max(0, Math.min(100, Math.round(result.confidence * 100)))
    : null;
  const provenance =
    result?.mode === "llm" ? "AI-assisted summary" : result ? "From archive evidence" : null;
  const confidenceBadge =
    confidence != null
      ? `${result?.confidence_label ?? "Confidence"} (${confidence}%)`
      : null;

  return (
    <section className="panel answer-panel" aria-live="polite">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Evidence-backed result</p>
          <h2>Answer</h2>
        </div>
        <div className="badges">
          {provenance && <span className="confidence provenance">{provenance}</span>}
          {confidenceBadge && <span className="confidence">{confidenceBadge}</span>}
        </div>
      </div>

      {busy && !showLive && (
        <div className="working-card">
          <span className="spinner" aria-hidden="true" />
          <div>
            <p className="working-title">Working through the archive</p>
            <p className="working-copy">{workingLabel || "Searching and comparing sources…"}</p>
          </div>
        </div>
      )}

      {showLive ? (
        <StructuredAnswer markdown={liveMarkdown} />
      ) : !busy ? (
        <p className="empty">The answer, documents, and sources will appear here.</p>
      ) : null}

      {result?.confidence_note && (
        <p className="confidence-note">{result.confidence_note}</p>
      )}

      {result && (
        <div className="confidence-track">
          <span style={{ width: `${confidence ?? 0}%` }} />
        </div>
      )}
    </section>
  );
}
