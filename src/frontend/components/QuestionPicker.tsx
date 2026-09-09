export const SAMPLE_QUESTIONS = [
  { id: "1c_000", question: "In what year was Gloamreach founded?" },
  { id: "1c_003", question: "In which year was the Gauntlet of Sorrowfell actually forged?" },
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
          {sample.question}
        </button>
      ))}
    </div>
  );
}
