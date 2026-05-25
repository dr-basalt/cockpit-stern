"""Tests for InversionRules Engine."""
from dataclasses import dataclass


@dataclass
class MockProfile:
    name: str = "Test User"
    hd_type: str = "Generator"
    hd_authority: str = "Sacral"
    hd_profile: str = "4/1"
    hd_definition: str = "Simple"
    hd_signature: str = "Satisfaction"
    hd_not_self: str = "Frustration"
    clifton_top5: list = None
    clifton_bottom5: list = None
    mantra: str = "Test mantra"
    invariants: list = None
    energy_level: int = 7

    def __post_init__(self):
        if self.clifton_top5 is None:
            self.clifton_top5 = ["Idéation", "Futuriste", "Stratégique", "Individualisation", "Contexte"]
        if self.clifton_bottom5 is None:
            self.clifton_bottom5 = ["Discipline", "Harmonie", "Prudent", "Équitable"]
        if self.invariants is None:
            self.invariants = ["Revenue before infra"]

    @property
    def dominant_domain(self) -> str:
        from app.models.profile import CLIFTON_DOMAINS
        counts = {"ST": 0, "EX": 0, "REL": 0, "INF": 0}
        for s in self.clifton_top5:
            d = CLIFTON_DOMAINS.get(s)
            if d:
                counts[d] += 1
        return max(counts, key=counts.get)

    @property
    def clone_persona(self) -> dict:
        return {"name": f"Clone-{self.name}", "dominant": "ST", "strengths": self.clifton_top5, "hd_type": self.hd_type, "mode": "production"}

    @property
    def anti_persona(self) -> dict:
        return {"name": f"Anti-{self.name}", "challenge_axis": "EX", "blind_spots": self.clifton_bottom5, "hd_authority": self.hd_authority, "mode": "challenge"}


def test_inversion_build():
    from app.services.inversion import InversionRulesEngine

    engine = InversionRulesEngine()
    profile = MockProfile()
    config = engine.build(profile)

    assert len(config.clone_system_prompt) > 100, "Clone prompt too short"
    assert len(config.anti_system_prompt) > 100, "Anti prompt too short"
    assert len(config.sp_system_prompt) > 100, "SP prompt too short"
    assert config.energy_mode == "brake", f"Expected brake, got {config.energy_mode}"
    assert "Generator" in config.formatter_rules, "Formatter rule missing"


def test_energy_modes():
    from app.services.inversion import InversionRulesEngine

    engine = InversionRulesEngine()

    # High energy → brake
    p_high = MockProfile(energy_level=8)
    assert engine.build(p_high).energy_mode == "brake"

    # Low energy → accelerate
    p_low = MockProfile(energy_level=2)
    assert engine.build(p_low).energy_mode == "accelerate"

    # Mid energy → balance
    p_mid = MockProfile(energy_level=5)
    assert engine.build(p_mid).energy_mode == "balance"


def test_dominant_domain():
    # ST dominant (4 out of 5 are ST)
    p_st = MockProfile(clifton_top5=["Idéation", "Futuriste", "Stratégique", "Contexte", "Input"])
    assert p_st.dominant_domain == "ST"

    # REL dominant
    p_rel = MockProfile(clifton_top5=["Empathie", "Harmonie", "Développeur", "Relationnel", "Inclusion"])
    assert p_rel.dominant_domain == "REL"


def test_all_hd_types_have_formatter():
    from app.services.inversion import FORMATTER_RULES

    for hd_type in ["Generator", "Manifesting Generator", "Projector", "Manifestor", "Reflector"]:
        assert hd_type in FORMATTER_RULES, f"Missing formatter for {hd_type}"


def test_all_authorities_have_sp_prompt():
    from app.services.inversion import SP_AUTHORITY_PROMPTS

    for auth in ["Sacral", "Emotional", "Splenic", "Ego", "Self-Projected", "Mental", "Lunar", "None"]:
        assert auth in SP_AUTHORITY_PROMPTS, f"Missing SP prompt for {auth}"
