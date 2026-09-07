import json
from pathlib import Path

from gestaltx.agent.arbitration import arbitrate_claims

ROOT = Path(__file__).resolve().parents[1]


def test_1c_000_golden_matches_arbitration() -> None:
    golden = json.loads((ROOT / "eval/golden/1c_answers.json").read_text(encoding="utf-8"))
    claims = [
        {"entity": "Gloamreach", "claim": "Gloamreach founded year", "value": "Contested", "tier": 2, "source": "wiki/Gloamreach"},
        {"entity": "Gloamreach", "claim": "Gloamreach founded year", "value": "246 AS", "tier": 1, "source": "codex/Gloamreach"},
        {"entity": "Gloammarch", "claim": "Gloamreach founded year", "value": "321 AS", "tier": 1, "source": "codex/Gloammarch"},
    ]
    result = arbitrate_claims(
        [claim for claim in claims if claim["entity"] == "Gloamreach"],
        claim="Gloamreach founded year",
    )
    actual = result["value"] if isinstance(result, dict) else result.value
    assert actual == golden["1c_000"]["answer"] == "246 AS"


def test_all_question_ids_are_unique() -> None:
    questions = json.loads((ROOT / "eval/questions/sample_questions.json").read_text(encoding="utf-8"))
    assert len(questions) == 20
    ids = [item.get("qid") or item.get("id") for item in questions]
    assert all(ids)
    assert len(set(ids)) == 20
