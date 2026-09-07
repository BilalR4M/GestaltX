export const SAMPLE_QUESTIONS = [
  { id: "1c_000", question: "In what year was Gloamreach founded?" },
  { id: "1c_003", question: "Resolve the archive claim identified as sample question 1c_003." },
  { id: "pointer", question: "Which higher-authority source resolves the disputed founding date of Gloamreach?" }
];

export function QuestionPicker({ onPick, disabled }: {
  onPick: (question: string) => void;
  disabled?: boolean;
}) {
  return (
    <div className="question-picker" aria-label="Sample questions">
      {SAMPLE_QUESTIONS.map((sample) => (
        <button key={sample.id} type="button" disabled={disabled} onClick={() => onPick(sample.question)}>
          <span>{sample.id}</span>{sample.question}
        </button>
      ))}
    </div>
  );
}
