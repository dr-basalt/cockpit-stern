"""Tests for API schemas (no DB required)."""

from app.api.profile import ProfileCreate, ProfileUpdate


def test_profile_create_schema():
    data = ProfileCreate(
        name="Test",
        hd_type="Generator",
        hd_authority="Sacral",
        hd_profile="4/1",
        hd_definition="Simple",
        hd_signature="Satisfaction",
        hd_not_self="Frustration",
        clifton_top5=["Idéation", "Futuriste", "Stratégique", "Individualisation", "Contexte"],
        clifton_bottom5=["Discipline", "Harmonie", "Prudent", "Équitable"],
        mantra="Revenue before infra",
        invariants=["Revenue before infra"],
    )
    assert data.name == "Test"
    assert data.energy_level == 5  # default


def test_profile_update_partial():
    data = ProfileUpdate(energy_level=8)
    dump = data.model_dump(exclude_none=True)
    assert dump == {"energy_level": 8}
    assert "name" not in dump
