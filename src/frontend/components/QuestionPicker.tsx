export const SAMPLE_QUESTIONS = [
  {
    id: "1c_000",
    title: "Contested founding year",
    hint: "Secondary sources disagree or say the date is unsettled. Research should follow the official record, not the first hit.",
    question: "In what year was Gloamreach founded?"
  },
  {
    id: "1c_003",
    title: "Forging date with wrong popular years",
    hint: "Casual accounts often cite the wrong year. Prefer the higher-authority inventory or armory source.",
    question: "In which year was the Gauntlet of Sorrowfell actually forged?"
  },
  {
    id: "pointer",
    title: "Which source settles the dispute?",
    hint: "Ask for the document that resolves the conflict — not only the numeric year.",
    question: "Which higher-authority source resolves the disputed founding date of Gloamreach?"
  }
];

export function QuestionPicker({ onPick, disabled }: {
  onPick: (question: string) => void;
  disabled?: boolean;
}) {
  return (
    <div className="question-picker" aria-label="Sample research prompts">
      <p className="picker-intro">
        Try a sample prompt. Each one is chosen to show a different research habit — contested facts,
        decoy years, and following a pointer to a stronger source.
      </p>
      {SAMPLE_QUESTIONS.map((sample) => (
        <button
          key={sample.id}
          type="button"
          disabled={disabled}
          onClick={() => onPick(sample.question)}
          title={sample.hint}
        >
          <span className="sample-title">{sample.title}</span>
          <span className="sample-hint">{sample.hint}</span>
          <span className="sample-question">{sample.question}</span>
        </button>
      ))}
    </div>
  );
}
