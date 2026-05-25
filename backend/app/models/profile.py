import uuid
from datetime import datetime
from typing import Literal

from sqlalchemy import String, Integer, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

CLIFTON_DOMAINS: dict[str, str] = {
    # Strategic Thinking
    "Analytique": "ST", "Analytical": "ST",
    "Contexte": "ST", "Context": "ST",
    "Futuriste": "ST", "Futuristic": "ST",
    "Idéation": "ST", "Ideation": "ST",
    "Intellectualisme": "ST", "Intellection": "ST",
    "Input": "ST",
    "Stratégique": "ST", "Strategic": "ST",
    "Studieux": "ST", "Learner": "ST",
    # Executing
    "Réalisateur": "EX", "Achiever": "EX",
    "Arrangeur": "EX", "Arranger": "EX",
    "Focus": "EX",
    "Discipline": "EX", "Consistency": "EX",
    "Responsabilité": "EX", "Responsibility": "EX",
    "Restaurer": "EX", "Restorative": "EX",
    "Activateur": "EX", "Activator": "EX",
    "Adaptabilité": "EX", "Adaptability": "EX",
    "Prudent": "EX", "Deliberative": "EX",
    # Relationship Building
    "Connexion": "REL", "Connectedness": "REL",
    "Développeur": "REL", "Developer": "REL",
    "Empathie": "REL", "Empathy": "REL",
    "Harmonie": "REL", "Harmony": "REL",
    "Inclusion": "REL", "Includer": "REL",
    "Individualisation": "REL", "Individualization": "REL",
    "Positivité": "REL", "Positivity": "REL",
    "Relationnel": "REL", "Relator": "REL",
    # Influencing
    "Charisme": "INF", "Woo": "INF",
    "Communication": "INF",
    "Compétition": "INF", "Competition": "INF",
    "Conviction": "INF", "Belief": "INF",
    "Importance": "INF", "Significance": "INF",
    "Maximisation": "INF", "Maximizer": "INF",
    "Commandement": "INF", "Command": "INF",
    "Assurance": "INF", "Self-Assurance": "INF",
}

HD_TYPES = Literal["Generator", "Manifesting Generator", "Projector", "Manifestor", "Reflector"]
HD_AUTHORITIES = Literal["Sacral", "Emotional", "Splenic", "Ego", "Self-Projected", "Mental", "Lunar", "None"]
HD_DEFINITIONS = Literal["Simple", "Split", "Triple Split", "Quadruple Split"]


class HumanProfile(Base):
    __tablename__ = "profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Human Design
    hd_type: Mapped[str] = mapped_column(String(50))
    hd_authority: Mapped[str] = mapped_column(String(50))
    hd_profile: Mapped[str] = mapped_column(String(10))
    hd_definition: Mapped[str] = mapped_column(String(50))
    hd_cross: Mapped[str | None] = mapped_column(String(255), nullable=True)
    hd_signature: Mapped[str] = mapped_column(String(100))
    hd_not_self: Mapped[str] = mapped_column(String(100))

    # Clifton
    clifton_top5: Mapped[list[str]] = mapped_column(ARRAY(String))
    clifton_bottom5: Mapped[list[str]] = mapped_column(ARRAY(String))
    clifton_all34: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)

    # Identity
    mantra: Mapped[str] = mapped_column(String(500))
    invariants: Mapped[list[str]] = mapped_column(ARRAY(String))

    # Dynamic state
    energy_level: Mapped[int] = mapped_column(Integer, default=5)

    @property
    def dominant_domain(self) -> str:
        counts: dict[str, int] = {"ST": 0, "EX": 0, "REL": 0, "INF": 0}
        for strength in self.clifton_top5:
            domain = CLIFTON_DOMAINS.get(strength)
            if domain:
                counts[domain] += 1
        return max(counts, key=counts.get)

    @property
    def clone_persona(self) -> dict:
        domain = self.dominant_domain
        domain_labels = {"ST": "Réflexion Stratégique", "EX": "Exécution", "REL": "Relation", "INF": "Influence"}
        return {
            "name": f"Clone-{self.name}",
            "dominant": domain_labels.get(domain, domain),
            "strengths": self.clifton_top5,
            "hd_type": self.hd_type,
            "mode": "production",
        }

    @property
    def anti_persona(self) -> dict:
        domain = self.dominant_domain
        inversion_map = {"ST": "EX", "EX": "ST", "REL": "INF", "INF": "REL"}
        return {
            "name": f"Anti-{self.name}",
            "challenge_axis": inversion_map.get(domain, "ST"),
            "blind_spots": self.clifton_bottom5,
            "hd_authority": self.hd_authority,
            "mode": "challenge",
        }
