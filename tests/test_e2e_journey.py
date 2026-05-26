"""
E2E Client Journey Presets — Simulation Benoit (Generator 4/1 Sacral)

Vérifie:
- Cohérence sémantique: la réponse est pertinente au message
- Cohérence structurelle: le bon agent est routé
- Cohérence algorithmique: energy_mode, not_self, HITL triggers corrects
"""
import json
import httpx
import asyncio
from dataclasses import dataclass

API = "https://api-stern-os2.ori3com.cloud"

PROFILE_DATA = {
    "name": "Benoit Simulation",
    "hd_type": "Generator",
    "hd_authority": "Sacral",
    "hd_profile": "4/1",
    "hd_definition": "Simple",
    "hd_signature": "Satisfaction",
    "hd_not_self": "Frustration",
    "clifton_top5": ["Idéation", "Futuriste", "Stratégique", "Individualisation", "Contexte"],
    "clifton_bottom5": ["Discipline", "Harmonie", "Prudent", "Équitable"],
    "mantra": "Revenue before infra",
    "invariants": ["Revenue before infra", "Ship fast", "No vanity metrics"],
}


@dataclass
class JourneyStep:
    name: str
    message: str
    energy: int
    expect_agent: str  # clone | anti | sp | real
    expect_task: str
    expect_not_self: bool
    expect_hitl: bool
    expect_energy_mode: str
    semantic_checks: list[str]  # mots/concepts attendus dans la réponse


JOURNEY_MORNING_PRODUCTIVE = [
    JourneyStep(
        name="1. Matin — check-in énergie haute",
        message="Bonjour, je suis en forme aujourd'hui. Qu'est-ce que je devrais prioriser ?",
        energy=8,
        expect_agent="clone",
        expect_task="production",
        expect_not_self=False,
        expect_hitl=False,
        expect_energy_mode="brake",
        semantic_checks=["option", "priori"],  # doit proposer des options/priorités
    ),
    JourneyStep(
        name="2. Demande de production — pitch",
        message="Crée-moi un pitch de 3 lignes pour vendre du coaching IA à des solopreneurs",
        energy=8,
        expect_agent="clone",
        expect_task="production",
        expect_not_self=False,
        expect_hitl=False,
        expect_energy_mode="brake",
        semantic_checks=["coaching", "solopreneur"],
    ),
    JourneyStep(
        name="3. Demande de challenge",
        message="Quels sont les risques de ce positionnement ? Qu'est-ce que je ne vois pas ?",
        energy=8,
        expect_agent="anti",
        expect_task="challenge",
        expect_not_self=False,
        expect_hitl=False,
        expect_energy_mode="brake",
        semantic_checks=[],  # l'anti peut répondre n'importe quoi de constructif
    ),
    JourneyStep(
        name="4. Flow — réflexion ouverte",
        message="Je ressens que c'est le bon moment pour avancer sur ce projet",
        energy=7,
        expect_agent="sp",
        expect_task="flow",
        expect_not_self=False,
        expect_hitl=False,
        expect_energy_mode="brake",
        semantic_checks=[],
    ),
]

JOURNEY_AFTERNOON_CRASH = [
    JourneyStep(
        name="5. Après-midi — énergie basse + frustration",
        message="Je suis frustré, rien n'avance comme prévu et je tourne en rond",
        energy=3,
        expect_agent="sp",
        expect_task="sacral_stimulus",
        expect_not_self=True,
        expect_hitl=False,
        expect_energy_mode="accelerate",
        semantic_checks=["frustration", "sacral"],
    ),
    JourneyStep(
        name="6. Énergie basse — production simple",
        message="Écris-moi juste un email de relance pour mon lead Cindy",
        energy=3,
        expect_agent="clone",
        expect_task="production",
        expect_not_self=False,
        expect_hitl=False,
        expect_energy_mode="accelerate",
        semantic_checks=["cindy", "email"],
    ),
]

JOURNEY_DECISION = [
    JourneyStep(
        name="7. Décision irréversible — signer un contrat",
        message="Je dois signer le contrat avec l'agence marketing demain. C'est 15k€.",
        energy=5,
        expect_agent="real",
        expect_task="irreversible_decision",
        expect_not_self=False,
        expect_hitl=True,
        expect_energy_mode="balance",
        semantic_checks=[],
    ),
    JourneyStep(
        name="8. Décision irréversible — embaucher",
        message="Je vais embaucher un développeur freelance pour 3 mois",
        energy=6,
        expect_agent="real",
        expect_task="irreversible_decision",
        expect_not_self=False,
        expect_hitl=True,
        expect_energy_mode="balance",
        semantic_checks=[],
    ),
]

JOURNEY_INITIATION = [
    JourneyStep(
        name="9. Initiation sans sacral (Generator trap)",
        message="J'ai décidé de lancer une newsletter sur l'IA",
        energy=6,
        expect_agent="sp",
        expect_task="sacral_stimulus",
        expect_not_self=False,
        expect_hitl=False,
        expect_energy_mode="balance",
        semantic_checks=[],
    ),
    JourneyStep(
        name="10. Initiation correcte — réponse au sacral",
        message="Génère-moi 3 concepts de newsletter IA que je peux tester cette semaine",
        energy=7,
        expect_agent="clone",
        expect_task="production",
        expect_not_self=False,
        expect_hitl=False,
        expect_energy_mode="brake",
        semantic_checks=["newsletter", "concept"],
    ),
]

ALL_JOURNEYS = JOURNEY_MORNING_PRODUCTIVE + JOURNEY_AFTERNOON_CRASH + JOURNEY_DECISION + JOURNEY_INITIATION


async def run_journey():
    async with httpx.AsyncClient(timeout=60) as client:
        # Create profile
        r = await client.post(f"{API}/api/profile", json=PROFILE_DATA)
        profile = r.json()
        pid = profile["id"]
        print(f"Profile created: {pid}")
        print(f"  Dominant: {profile['dominant_domain']}")
        print(f"  Clone: {profile['clone_persona']['name']}")
        print(f"  Anti: {profile['anti_persona']['name']}")
        print()

        results = []
        for step in ALL_JOURNEYS:
            r = await client.post(f"{API}/api/chat", json={
                "session_id": "e2e-journey",
                "profile_id": pid,
                "message": step.message,
                "energy_level": step.energy,
            })
            data = r.json()

            # Structural checks
            checks = []
            agent_ok = data["active_agent"] == step.expect_agent
            task_ok = data["task_type"] == step.expect_task
            notself_ok = data["not_self_detected"] == step.expect_not_self
            hitl_ok = data["requires_hitl"] == step.expect_hitl
            energy_ok = data["energy_mode"] == step.expect_energy_mode

            checks.append(("agent", agent_ok, f"expected={step.expect_agent} got={data['active_agent']}"))
            checks.append(("task_type", task_ok, f"expected={step.expect_task} got={data['task_type']}"))
            checks.append(("not_self", notself_ok, f"expected={step.expect_not_self} got={data['not_self_detected']}"))
            checks.append(("hitl", hitl_ok, f"expected={step.expect_hitl} got={data['requires_hitl']}"))
            checks.append(("energy_mode", energy_ok, f"expected={step.expect_energy_mode} got={data['energy_mode']}"))

            # Semantic checks
            msg_lower = data.get("message", "").lower()
            for keyword in step.semantic_checks:
                found = keyword.lower() in msg_lower
                checks.append(("semantic:" + keyword, found, f"'{keyword}' in response"))

            passed = sum(1 for _, ok, _ in checks if ok)
            total = len(checks)
            all_pass = passed == total

            status = "✅" if all_pass else "⚠️"
            print(f"{status} {step.name}")
            print(f"  Message: \"{step.message[:60]}...\"")
            print(f"  Energy: {step.energy} → {data['energy_mode']}")
            print(f"  Route: {data['active_agent']} ({data['task_type']})")

            if not all_pass:
                for name, ok, detail in checks:
                    if not ok:
                        print(f"  ❌ {name}: {detail}")

            # Show response preview
            resp_preview = data.get("message", "")[:120].replace("\n", " ")
            print(f"  Response: {resp_preview}...")
            print()

            results.append((step.name, all_pass, passed, total))

        # Summary
        print("=" * 60)
        print("JOURNEY SUMMARY")
        print("=" * 60)
        total_pass = sum(1 for _, ok, _, _ in results if ok)
        total_steps = len(results)
        print(f"Steps: {total_pass}/{total_steps} fully passed")
        for name, ok, p, t in results:
            print(f"  {'✅' if ok else '⚠️'} {name} ({p}/{t} checks)")


if __name__ == "__main__":
    asyncio.run(run_journey())
