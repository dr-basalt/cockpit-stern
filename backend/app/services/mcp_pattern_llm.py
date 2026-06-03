"""LLM-assisted pattern detection for MCP composition.

Prend le résultat de l'introspecteur (bounded contexts, entities, relations, gaps)
et demande au LLM de découvrir des patterns de composition non évidents :
- Apophénie contrôlée : voir des connexions entre BC non reliés
- Raisonnement abductif : inférer des workflows depuis les gaps
- DDD émergent : proposer des aggregates cross-BC
- Skills inédites : compositions que les règles statiques ne voient pas
"""

import json
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Tu es un architecte méta-systémique spécialisé en composition de SaaS et d'interfaces.

Tu reçois le résultat d'une introspection de capabilities (MCP, REST, GraphQL, CLI — tout est normalisé en SCRUDX).

GRAMMAIRE DE COMPOSITION — utilise ces opérateurs dans tes raisonnements :

**Structurels :** SCRUDX (Search·Create·Read·Update·Delete·eXecute), ONTOLOGIE (entités/relations), TAXONOMIE (hiérarchie), AST (arbre syntaxique)
**Gouvernance :** RACI (Responsible·Accountable·Consulted·Informed), OKR (objectifs/résultats), BPMN (processus/lifecycle)
**Raisonnement :** BACKWARD CHAINING (but→étapes), BACKWARD REASONING (effet→cause), META-SYSTÉMIQUE (système qui pense le système)
**Profilage :** HD (Human Design), CLIFTON5/34 (forces/blind spots), MBTI, OCEAN (Big Five)
**Exécution :** ÉVOLUTIONNAIRE (irréversible, p(n)→p(n+1)), RCE (Reverse Cascade Execution — déployer par dépendance inverse), RC (Reinforcement Coding), RL (Reinforcement Learning)
**Infrastructure :** SERVERLESS, STORAGELESS, ANYLESS, NOCODE, NO-ANY, EDGE, AAAS (Anything As A Service)
**Intelligence :** NOLLM (minimiser les appels LLM), IA-TO-GNN (LLM discovery → GNN cache → convergence déterministe)

PRINCIPES :
- Composition par INTERFACES pas par héritage — "que sais-tu faire ?" pas "de quel type es-tu ?"
- Maximalisme : utiliser le meilleur de chaque SaaS sans rien sacrifier
- Tuilage compensatoire : un gap dans un BC est comblé par un autre BC
- La valeur est dans le × (la composition), pas dans les composants
- NOLLM : si un pattern est détecté, le stocker dans un graphe pour ne plus appeler le LLM
- IA-TO-GNN : chaque insight du LLM doit être structuré pour être réutilisable sans LLM

Ta mission :
1. **COMPOSITIONS INÉDITES** : chaînes de tools cross-BC, taguées par energy_mode (HD) et opérateurs utilisés
2. **WORKFLOWS LIFECYCLE** : processus BPMN cross-BC avec RACI et conditions
3. **AGGREGATES CROSS-BC** : entités virtuelles émergentes avec widget UI
4. **GAPS COMPENSABLES** : ops manquantes comblées par tuilage inter-BC
5. **UI WIDGETS ÉMERGENTS** : composants qui n'existent que grâce à la composition
6. **GNN CACHE HINTS** : pour chaque pattern découvert, la structure Neo4j qui permettrait de le retrouver sans LLM la prochaine fois

Contexte utilisateur : solopreneur tech, HD Generator 4/1 (autorité sacrale), multi-potentiel HPI, CLIFTON top: Strategic·Ideation·Futuristic·Input·Learner, gère business + coaching + dev personnel. Son cockpit (Stern OS) doit réduire la dispersion cognitive et augmenter l'exécution alignée.

Réponds en JSON structuré uniquement."""

USER_PROMPT_TEMPLATE = """Voici l'introspection MCP de mon cockpit :

## Bounded Contexts ({total_bcs})
{bcs_summary}

## Relations détectées ({total_relations})
{relations_summary}

## Gaps identifiés ({total_gaps} au total, principaux)
{gaps_summary}

## Skills déjà suggérées par les règles mécaniques
{existing_skills}

---

Découvre ce que les règles mécaniques ne voient pas. Réponds en JSON :

```json
{{
  "novel_compositions": [
    {{
      "name": "nom_du_skill",
      "pattern": "AGGREGATE|ENRICH|CROSS_WRITE|SYNC|TRIGGER|PIPELINE|RECONCILIATION",
      "tools": ["server.tool_name", ...],
      "description": "ce que ça fait et POURQUOI c'est utile (pas évident)",
      "trigger": "quand/comment déclencher",
      "value": "la valeur que ça crée et qu'aucun SaaS ne fait seul",
      "energy_mode": "brake|balance|accelerate (selon énergie HD)"
    }}
  ],
  "cross_bc_aggregates": [
    {{
      "name": "NomAggregate",
      "sources": ["BC1.Entity", "BC2.Entity", ...],
      "description": "entité virtuelle qui émerge de la composition",
      "ui_widget": "type de widget pour visualiser"
    }}
  ],
  "lifecycle_workflows": [
    {{
      "name": "nom_workflow",
      "trigger": "événement déclencheur",
      "steps": [
        {{"bc": "BC", "tool": "tool_name", "condition": "si applicable"}},
      ],
      "description": "processus métier complet"
    }}
  ],
  "gap_compensations": [
    {{
      "gap": "BC.Entity manque Op",
      "compensation": "comment un autre BC comble ce gap",
      "tools": ["tool1", "tool2"]
    }}
  ],
  "emergent_widgets": [
    {{
      "name": "nom_widget",
      "type": "timeline|kanban|matrix|radar|heatmap|priority_card|pipeline",
      "sources": ["BC1.tool", "BC2.tool", ...],
      "description": "widget qui n'existe que grâce à la composition"
    }}
  ],
  "gnn_cache_hints": [
    {{
      "pattern_id": "identifiant unique du pattern",
      "cypher": "MERGE (p:Pattern {{name: ...}}) MERGE (bc1:BC {{name: ...}}) MERGE (p)-[:COMPOSES]->(bc1) ...",
      "description": "comment stocker ce pattern dans Neo4j pour le retrouver sans LLM",
      "reuse_condition": "quand réutiliser ce cache (ex: mêmes BC connectés, même profil HD)"
    }}
  ]
}}
```"""


def _build_prompt(introspection: dict) -> str:
    """Build the user prompt from introspection results."""
    bcs = introspection["bounded_contexts"]
    bcs_summary = "\n".join(
        f"- **{bc['name']}** ({bc['mcp_server']}) : {bc['entity_count']} entities, {bc['total_tools']} tools\n"
        + "\n".join(
            f"  - {e['name']} [{e['scrudx']}] : {', '.join(op['tool'] for op in e['operations'])}"
            for e in bc["entities"]
        )
        for bc in bcs
    )

    relations = introspection["relations"]
    relations_summary = "\n".join(
        f"- {r['from']} → {r['to']} via `{r['param']}` ({r['type']})"
        for r in relations
    ) or "Aucune relation détectée"

    gaps = introspection["gaps"][:20]
    gaps_summary = "\n".join(
        f"- {g['bc']}.{g['entity']} manque **{g['missing']}** — {g['description']}"
        for g in gaps
    )

    existing = introspection.get("suggested_skills", [])
    existing_skills = "\n".join(
        f"- {s['name']} [{s['pattern']}] : {s['description']}"
        for s in existing
    ) or "Aucune"

    stats = introspection["stats"]

    return USER_PROMPT_TEMPLATE.format(
        total_bcs=stats["total_bcs"],
        bcs_summary=bcs_summary,
        total_relations=stats["total_relations"],
        relations_summary=relations_summary,
        total_gaps=stats["total_gaps"],
        gaps_summary=gaps_summary,
        existing_skills=existing_skills,
    )


async def detect_patterns_llm(introspection: dict) -> dict:
    """Call LLM to discover novel composition patterns from introspection data."""
    api_key = settings.OPENROUTER_API_KEY
    if not api_key:
        return {"error": "OPENROUTER_API_KEY not configured"}

    user_prompt = _build_prompt(introspection)

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "anthropic/claude-sonnet-4",
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.7,
                    "max_tokens": 4096,
                },
            )

            if r.status_code != 200:
                return {"error": f"LLM call failed: {r.status_code}", "detail": r.text}

            response = r.json()
            content = response["choices"][0]["message"]["content"]

            # Extract JSON from response (might be wrapped in ```json ... ```)
            json_str = content
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0]
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0]

            result = json.loads(json_str.strip())

            return {
                "llm_patterns": result,
                "model": "anthropic/claude-sonnet-4",
                "prompt_tokens": response.get("usage", {}).get("prompt_tokens", 0),
                "completion_tokens": response.get("usage", {}).get("completion_tokens", 0),
            }

    except json.JSONDecodeError as e:
        logger.warning(f"LLM returned non-JSON: {e}")
        return {"error": "LLM response not valid JSON", "raw": content[:1000]}
    except Exception as e:
        logger.error(f"LLM pattern detection failed: {e}")
        return {"error": str(e)}
