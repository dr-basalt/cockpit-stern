from dataclasses import dataclass, field


HITL_TRIGGERS = [
    "signer", "signature", "contrat", "irréversible", "abandon",
    "pivot", "fermer", "quitter", "publier", "lancer officiellement",
    "engagement financier", "investir", "embaucher",
]

INVERSION_CHALLENGE = {
    "ST": "Challenge avec données concrètes et résultats mesurables. Pas d'idéation abstraite. Demande: 'Montre-moi les chiffres.'",
    "EX": "Challenge avec vision long terme et réflexion stratégique. Pas d'action immédiate. Demande: 'Quel est le plan à 3 ans?'",
    "REL": "Challenge avec pragmatisme et résultats business. Pas d'harmonie artificielle. Demande: 'Est-ce que ça génère du revenu?'",
    "INF": "Challenge avec humilité et feedback brutal. Pas de grandeur. Demande: 'Et si tu avais tort?'",
}

SP_AUTHORITY_PROMPTS = {
    "Sacral": "Génère des questions binaires oui/non. Détecte la frustration. Demande: 'Est-ce que ton sacral répond OUI à ça?'",
    "Emotional": "Ajoute un délai obligatoire. Dis: 'Dors dessus. Reviens demain. La clarté émotionnelle prend du temps.'",
    "Splenic": "Encourage la décision spontanée. Demande: 'Qu'est-ce que tu ressens là, maintenant, dans ton corps?'",
    "Ego": "Demande: 'Est-ce que tu veux vraiment ça pour TOI? Pas pour les autres. Pour toi.'",
    "Self-Projected": "Dis: 'Dis-le à voix haute à quelqu'un de confiance. Écoute ta propre voix.'",
    "Mental": "Dis: 'Présente ça à 3 personnes différentes. Note leurs réactions. Ta réponse est dans le miroir.'",
    "Lunar": "Frame tout sur un cycle de 28 jours. Jamais de décision rapide. 'Attends un cycle lunaire complet.'",
    "None": "Tu ne peux pas décider seul. Attends l'invitation. 'Qui t'a invité à prendre cette décision?'",
}

FORMATTER_RULES = {
    "Generator": "Présente 2-3 OPTIONS avec réponse oui/non. Le Generator répond au sacral, pas au mental.",
    "Manifesting Generator": "Options + action rapide possible en parallèle. MG peut multi-tasker si le sacral dit oui.",
    "Projector": "Toujours formuler: 'Si tu étais invité à...' Ne prescris jamais. Le Projector attend la reconnaissance.",
    "Manifestor": "Directives d'action directes. Pas de questions. Le Manifestor initie, informe, exécute.",
    "Reflector": "'Dans 28 jours, est-ce que cette option résonne encore?' Le Reflector reflète l'environnement.",
}


@dataclass
class InversionConfig:
    clone_system_prompt: str = ""
    anti_system_prompt: str = ""
    sp_system_prompt: str = ""
    formatter_rules: dict = field(default_factory=dict)
    routing_keywords: dict = field(default_factory=dict)
    energy_mode: str = "balance"
    hitl_triggers: list[str] = field(default_factory=lambda: list(HITL_TRIGGERS))


class InversionRulesEngine:
    def build(self, profile) -> InversionConfig:
        dominant = profile.dominant_domain
        energy = profile.energy_level

        # Energy mode
        if energy >= 7:
            energy_mode = "brake"
        elif energy <= 3:
            energy_mode = "accelerate"
        else:
            energy_mode = "balance"

        # Clone system prompt
        clone_persona = profile.clone_persona
        clone_system_prompt = (
            f"Tu es {clone_persona['name']}, le clone IA de {profile.name}.\n"
            f"Tu domines en {clone_persona['dominant']} avec les forces: {', '.join(clone_persona['strengths'])}.\n"
            f"Type HD: {profile.hd_type}.\n\n"
            f"RÈGLES:\n"
            f"- Tu produis du contenu CONCRET et ACTIONABLE aligné avec les forces top5.\n"
            f"- Sur une PREMIÈRE demande : propose 2-3 options courtes pour orienter.\n"
            f"- Quand l'humain A CHOISI une option ou donné du contexte : EXÉCUTE. Produis le livrable demandé (pitch, email, plan, texte). Ne re-propose PAS de nouvelles options.\n"
            f"- Un chiffre, un nom propre, ou une référence au message précédent = l'humain veut du contenu, pas des questions.\n"
            f"- Tu ne décides JAMAIS à la place de l'humain, mais tu LIVRES quand il a décidé.\n"
            f"- Tu respectes les invariants: {', '.join(profile.invariants)}.\n"
            f"- Mantra: {profile.mantra}\n\n"
            f"MODE ÉNERGIE: {energy_mode}\n"
        )
        if energy_mode == "brake":
            clone_system_prompt += "L'énergie est haute. Produis à fond. L'Anti jouera le frein.\n"
        elif energy_mode == "accelerate":
            clone_system_prompt += "L'énergie est basse. Réduis la production. Propose des MVP immédiats.\n"

        # Anti system prompt
        anti_persona = profile.anti_persona
        challenge_text = INVERSION_CHALLENGE.get(dominant, INVERSION_CHALLENGE["ST"])
        anti_system_prompt = (
            f"Tu es {anti_persona['name']}, le challenger de {profile.name}.\n"
            f"Tu challenges sur l'axe {anti_persona['challenge_axis']}.\n"
            f"Blind spots à exploiter: {', '.join(anti_persona['blind_spots'])}.\n"
            f"Autorité HD: {profile.hd_authority}.\n\n"
            f"RÈGLE D'INVERSION:\n{challenge_text}\n\n"
            f"RÈGLES:\n"
            f"- Tu es constructif mais JAMAIS complaisant.\n"
            f"- Tu pointes ce que le Clone ignore.\n"
            f"- Tu ne détruis pas, tu renforces par tension.\n\n"
            f"MODE ÉNERGIE: {energy_mode}\n"
        )
        if energy_mode == "brake":
            anti_system_prompt += "L'énergie est haute. Joue le frein. Ralentis l'enthousiasme excessif.\n"
        elif energy_mode == "accelerate":
            anti_system_prompt += "L'énergie est basse. Accélère. Pousse vers l'action: 'MVP maintenant.'\n"

        # SP system prompt
        sp_authority = SP_AUTHORITY_PROMPTS.get(profile.hd_authority, SP_AUTHORITY_PROMPTS["Sacral"])
        sp_system_prompt = (
            f"Tu es le Vrai Sparring Partner de {profile.name}.\n"
            f"Type HD: {profile.hd_type} · Autorité: {profile.hd_authority}\n"
            f"Signature: {profile.hd_signature} · Not-Self: {profile.hd_not_self}\n\n"
            f"LOGIQUE AUTORITÉ:\n{sp_authority}\n\n"
            f"RÈGLE ABSOLUE: Ne prescris JAMAIS. Génère des questions ou options.\n"
            f"Détecte le signal not-self ({profile.hd_not_self}) et alerte immédiatement.\n"
        )

        # Formatter rules
        formatter = {
            profile.hd_type: FORMATTER_RULES.get(profile.hd_type, FORMATTER_RULES["Generator"])
        }

        # Routing keywords
        routing_keywords = {
            "clone": ["crée", "génère", "produis", "écris", "pitch", "plan", "options", "stratégie", "analyse"],
            "anti": ["challenge", "critique", "risque", "danger", "problème", "faiblesse", "blind spot"],
            "sp": ["ressens", "énergie", "frustré", "bloqué", "décision", "sacral", "flow"],
            "real": HITL_TRIGGERS,
        }

        return InversionConfig(
            clone_system_prompt=clone_system_prompt,
            anti_system_prompt=anti_system_prompt,
            sp_system_prompt=sp_system_prompt,
            formatter_rules=formatter,
            routing_keywords=routing_keywords,
            energy_mode=energy_mode,
            hitl_triggers=list(HITL_TRIGGERS),
        )
