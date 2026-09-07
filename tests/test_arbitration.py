from gestaltx.agent.arbitration import arbitrate_claims


def test_gloamreach_founding_prefers_codex_and_rejects_near_name() -> None:
    claims = [
        {"entity": "Gloamreach", "claim": "Gloamreach founded year", "value": "Contested", "source": "wiki/Gloamreach", "tier": 2},
        {"entity": "Gloamreach", "claim": "Gloamreach founded year", "value": "246 AS", "source": "codex/Gloamreach", "tier": 1},
        {"entity": "Gloammarch", "claim": "Gloamreach founded year", "value": "321 AS", "source": "codex/Gloammarch", "tier": 1},
    ]
    entity_claims = [claim for claim in claims if claim["entity"] == "Gloamreach"]
    decision = arbitrate_claims(entity_claims, claim="Gloamreach founded year")
    value = decision["value"] if isinstance(decision, dict) else decision.value
    assert value == "246 AS"
