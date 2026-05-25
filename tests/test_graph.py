"""Tests for filter_sp node (synchronous, no LLM calls)."""
import pytest
import asyncio
from unittest.mock import MagicMock
from langchain_core.messages import HumanMessage

from app.agents.nodes.filter_sp import filter_sp_node


def make_state(message: str, hd_type: str = "Generator", hd_not_self: str = "Frustration") -> dict:
    return {
        "messages": [HumanMessage(content=message)],
        "profile": {
            "hd_type": hd_type,
            "hd_authority": "Sacral",
            "hd_not_self": hd_not_self,
            "clifton_top5": [],
            "clifton_bottom5": [],
            "invariants": [],
        },
        "inversion_config": {
            "routing_keywords": {
                "clone": ["crée", "génère", "pitch"],
                "anti": ["challenge", "critique", "risque"],
                "sp": ["ressens", "frustré", "bloqué"],
                "real": ["signer", "contrat"],
            }
        },
        "energy_level": 5,
        "task_type": "production",
        "active_agent": "sp",
        "requires_hitl": False,
        "hitl_token": None,
        "not_self_detected": False,
        "session_id": "test",
        "context": "",
    }


@pytest.mark.asyncio
async def test_production_routing():
    state = make_state("Crée-moi 3 options de pitch pour Cindy")
    result = await filter_sp_node(state)
    assert result["task_type"] == "production"


@pytest.mark.asyncio
async def test_not_self_detection():
    state = make_state("Je suis vraiment frustré par cette situation")
    result = await filter_sp_node(state)
    assert result["not_self_detected"] is True
    assert result["task_type"] == "sacral_stimulus"


@pytest.mark.asyncio
async def test_hitl_trigger():
    state = make_state("Je dois signer ce contrat demain")
    result = await filter_sp_node(state)
    assert result["requires_hitl"] is True
    assert result["hitl_token"] is not None
    assert result["task_type"] == "irreversible_decision"


@pytest.mark.asyncio
async def test_initiation_detection():
    state = make_state("Je veux lancer un nouveau projet")
    result = await filter_sp_node(state)
    assert result["task_type"] == "sacral_stimulus"


@pytest.mark.asyncio
async def test_projector_amertume():
    state = make_state("Personne ne reconnaît mon travail, je suis ignoré", hd_type="Projector", hd_not_self="Amertume")
    result = await filter_sp_node(state)
    assert result["not_self_detected"] is True
