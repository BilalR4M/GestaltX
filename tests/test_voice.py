"""Voice and human-readable answer engine checks."""

from __future__ import annotations

from gestaltx.agent.evidence import RetrievalLog, build_dossier, friendly_title
from gestaltx.agent.scratchpad import ClaimRecord, Scratchpad
from gestaltx.agent.synthesize import synthesize_answer
from gestaltx.agent.voice import prose_for_voice_check, violations


def test_violations_catch_we_and_paths():
    text = "We will trust codex/codex_vaeloria_i.pdf because you can trust it."
    found = violations(text)
    assert any(item.startswith("pronoun:") for item in found)
    assert any(item.startswith("slop:") for item in found)
    assert any(item.startswith("artifact:") for item in found)


def test_friendly_title_inserts_colon():
    title = friendly_title(
        "codex/codex_vaeloria_i_gazetteer.pdf",
        {"title": "Codex Vaeloria I Gazetteer Of The Sundered Realms"},
    )
    assert "I:" in title or "I :" in title
    assert "Gazetteer" in title


def test_dossier_attributes_rival_values():
    claims = [
        ClaimRecord(
            claim="founding year",
            value="246 AS",
            source="codex/codex_vaeloria_i_gazetteer_of_the_sundered_realms.pdf",
            tier=1,
            confidence=0.9,
            quote="Gloamreach - founded: 246 AS.",
            metadata={
                "title": "Codex Vaeloria I Gazetteer Of The Sundered Realms",
                "source_family": "codex",
                "page_start": 24,
            },
        ),
        ClaimRecord(
            claim="founding year",
            value="Contested",
            source="wiki/gloamreach.md",
            tier=2,
            confidence=0.5,
            quote="founding is contested; consult the Codex",
            metadata={"title": "Gloamreach", "source_family": "wiki", "contested": True},
        ),
        ClaimRecord(
            claim="founding year",
            value="286 AS",
            source="ephemera/contract_concerning_the_sceptre_of_final_winter.txt",
            tier=4,
            confidence=0.4,
            quote="dated 286 AS",
            metadata={"title": "Contract Concerning The Sceptre Of Final Winter", "source_family": "ephemera"},
        ),
    ]
    winners = [claims[0]]
    findings = build_dossier(claims, winners)
    roles = {f.role for f in findings}
    assert "settles" in roles
    assert "pointer" in roles or "disputes" in roles
    rival = next(f for f in findings if f.value == "286 AS" or "286" in (f.said or ""))
    assert "286" in rival.said or rival.value == "286 AS"


def test_synthesize_has_no_voice_violations_and_attributes_conflict():
    pad = Scratchpad(entities=["Gloamreach"], intent="date")
    pad.add_claim(
        ClaimRecord(
            claim="founding year",
            value="246 AS",
            source="codex/codex_vaeloria_i_gazetteer_of_the_sundered_realms.pdf",
            tier=1,
            confidence=0.95,
            quote="Gloamreach - founded: 246 AS.",
            metadata={
                "title": "Codex Vaeloria I Gazetteer Of The Sundered Realms",
                "source_family": "codex",
                "page_start": 24,
            },
        )
    )
    pad.add_claim(
        ClaimRecord(
            claim="founding year",
            value="286 AS",
            source="ephemera/contract_concerning_the_sceptre_of_final_winter.txt",
            tier=4,
            confidence=0.4,
            quote="286 AS",
            metadata={
                "title": "Contract Concerning The Sceptre Of Final Winter",
                "source_family": "ephemera",
            },
        )
    )
    pad.add_claim(
        ClaimRecord(
            claim="founding year",
            value="Contested",
            source="wiki/gloamreach.md",
            tier=2,
            confidence=0.5,
            quote="founding is contested; consult the Codex",
            metadata={"title": "Gloamreach", "source_family": "wiki", "contested": True},
        )
    )
    retrieval = RetrievalLog()
    retrieval.passages = 8
    retrieval.documents = {
        "codex/codex_vaeloria_i_gazetteer_of_the_sundered_realms.pdf",
        "wiki/gloamreach.md",
        "ephemera/contract_concerning_the_sceptre_of_final_winter.txt",
    }
    result = synthesize_answer(
        "In what year was Gloamreach founded?",
        pad,
        llm=None,
        retrieval=retrieval,
    )
    prose = prose_for_voice_check(result["answer"])
    assert violations(prose) == []
    assert "246 AS" in result["answer"]
    assert "286" in result["answer"]
    # Rival year attributed to a named document, not only a bare number.
    assert "Contract" in result["answer"] or "contract" in result["answer"].casefold()
    assert result["confidence"] < 1.0
    assert result["confidence_label"] in {"High", "Reasonable", "Low"}
    assert "## Answer" in result["answer"]
    assert "## What the documents say" in result["answer"]
    assert "## Sources" in result["answer"]
