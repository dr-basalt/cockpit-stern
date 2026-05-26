import json
import logging
from dataclasses import dataclass

import litellm

logger = logging.getLogger(__name__)

MODEL = "openrouter/anthropic/claude-sonnet-4"
FALLBACK_MODEL = "openrouter/anthropic/claude-haiku-4-5"


@dataclass
class ValidationResult:
    approved: bool = False
    confidence: float = 0.0
    reason: str = ""
    risks: list[str] = None
    invariant_check: str = ""

    def __post_init__(self):
        if self.risks is None:
            self.risks = []


class MITLValidator:
    """Validates agent actions against profile + OKR alignment before MITL execution."""

    async def validate(self, dry_run_diff: dict, agent_okr, profile) -> ValidationResult:
        prompt = self._build_prompt(dry_run_diff, agent_okr, profile)

        try:
            response = await litellm.acompletion(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                max_tokens=1024,
            )
            data = json.loads(response.choices[0].message.content)
            return ValidationResult(**data)
        except Exception as e:
            logger.warning(f"MITL validation failed ({MODEL}), trying fallback: {e}")
            try:
                response = await litellm.acompletion(
                    model=FALLBACK_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=1024,
                )
                # Try to parse, fallback to safe default
                try:
                    data = json.loads(response.choices[0].message.content)
                    return ValidationResult(**data)
                except json.JSONDecodeError:
                    pass
            except Exception as e2:
                logger.error(f"MITL fallback also failed: {e2}")

            # Default: reject if validation fails
            return ValidationResult(
                approved=False,
                confidence=0.0,
                reason="Validation service unavailable — defaulting to reject",
                risks=["validation_unavailable"],
            )

    def _build_prompt(self, diff: dict, okr, profile) -> str:
        okr_title = getattr(okr, "title", str(okr)) if okr else "N/A"
        okr_why = getattr(okr, "why", "") if okr else "N/A"
        okr_krs = getattr(okr, "key_results", []) if okr else []

        return f"""Tu es le validateur d'alignement du Cockpit Stern.

PROFIL UTILISATEUR:
- HD Type: {profile.hd_type} | Autorité: {profile.hd_authority}
- Top 5 Clifton: {', '.join(profile.clifton_top5)}
- Mantra: {profile.mantra}
- Invariants: {json.dumps(profile.invariants)}
- Signature: {profile.hd_signature}
- Not-self: {profile.hd_not_self}

OKR RESPONSABLE:
- Titre: {okr_title}
- Why: {okr_why}
- Key Results: {json.dumps(okr_krs)}

ACTION PROPOSÉE (dry-run):
{json.dumps(diff, indent=2)}

QUESTION: Cette action est-elle alignée avec le profil, le mantra,
les invariants et les OKR ? Réponds en JSON strict:
{{
  "approved": bool,
  "confidence": 0.0-1.0,
  "reason": "explication courte",
  "risks": ["risque 1", ...],
  "invariant_check": "quel invariant est respecté ou violé"
}}"""
