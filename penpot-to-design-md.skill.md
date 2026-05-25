# SKILL: penpot-to-design-md
## Pipeline NLP → Penpot → DESIGN.md → Version
> Pour Claude Code CLI · Utilise Penpot MCP (66 tools)

---

## DÉCLENCHEURS

Utilise cette skill quand :
- L'utilisateur décrit un design en NLP ("je veux du violet pour le clone")
- Un fichier Penpot a été modifié et les tokens doivent être synchronisés
- POST /design/nlp/to-penpot est appelé
- POST /design/penpot/sync est appelé

---

## ÉTAPE 1 — Analyse NLP → Intent

```python
# Analyse le texte libre de l'utilisateur
# Identifie les intentions de design (couleurs, typo, layout, spacing)
# Retourne un objet DesignIntent structuré

INTENT_PATTERNS = {
  "color_agent": r"(sp|clone|anti|réel|sparring|vrai).*(couleur|color|#[0-9a-fA-F]{3,6})",
  "background":  r"(fond|background|bg).*(sombre|dark|clair|light|#[0-9a-fA-F]{3,6})",
  "typography":  r"(police|font|taille|size).*(plus grande|plus petite|[0-9]+px)",
  "density":     r"(compact|spacieux|aéré|dense)",
  "accent":      r"accent.*(couleur|#[0-9a-fA-F]{3,6})",
}

# Si NLP insuffisant → demande clarification avant de continuer
# Ne jamais assumer une couleur sans confirmation si ambiguë
```

---

## ÉTAPE 2 — Penpot MCP Execution

```
# Via Claude Code CLI + Penpot MCP configuré dans .mcp.json

# 1. Ouvre ou crée le fichier design de référence
penpot/navigate-page: {fileId: DESIGN_FILE_ID, pageId: "tokens"}

# 2. Met à jour les color styles
penpot/create-color-style: {
  name: "agent/clone/default",
  color: "<valeur extraite de l'intent>",
  opacity: 1
}

# 3. Applique aux composants référencés
penpot/apply-color-to-components: {
  styleId: "agent/clone/default",
  scope: "fill"
}

# 4. Exporte les tokens en JSON
penpot/export-tokens: {
  format: "w3c-design-tokens",  # format standard
  output: "tokens/tokens.json"
}
```

---

## ÉTAPE 3 — Extraction tokens.json → CSS vars

```python
# Lit tokens.json (format W3C Design Tokens)
# Mappe vers les CSS var names du DESIGN.md

TOKEN_MAP = {
  # Format: "penpot_token_path": "--css-var-name"
  "agent.sp.default.$value":      "--agent-sp",
  "agent.sp.dim.$value":          "--agent-sp-dim",
  "agent.clone.default.$value":   "--agent-clone",
  "agent.clone.dim.$value":       "--agent-clone-dim",
  "agent.anti.default.$value":    "--agent-anti",
  "agent.anti.dim.$value":        "--agent-anti-dim",
  "agent.real.default.$value":    "--agent-real",
  "agent.real.dim.$value":        "--agent-real-dim",
  "semantic.ok.$value":           "--color-ok",
  "semantic.warn.$value":         "--color-warn",
  "semantic.stop.$value":         "--color-stop",
  "background.void.$value":       "--bg-void",
  "background.surface.$value":    "--bg-surface",
  "background.raised.$value":     "--bg-raised",
  "background.overlay.$value":    "--bg-overlay",
  "text.primary.$value":          "--text-primary",
  "text.secondary.$value":        "--text-secondary",
  "text.tertiary.$value":         "--text-tertiary",
  "typography.display.$value":    "--font-display",
  "typography.mono.$value":       "--font-mono",
  "motion.dur.fast.$value":       "--dur-fast",
  "motion.dur.base.$value":       "--dur-base",
  "motion.ease.flow.$value":      "--ease-flow",
  "motion.ease.snap.$value":      "--ease-snap",
}

def extract_tokens(tokens_json: dict) -> dict:
    result = {}
    for penpot_path, css_var in TOKEN_MAP.items():
        value = deep_get(tokens_json, penpot_path.split('.'))
        if value:
            result[css_var] = value
    return result
```

---

## ÉTAPE 4 — Mise à jour DESIGN.md

```python
# Lit DESIGN.md existant
# Localise la section "## DESIGN TOKENS — Référence complète"
# Remplace les valeurs modifiées uniquement
# Préserve tout le reste du fichier (doc, principes, etc.)

def update_design_md(design_md_path: str, new_tokens: dict):
    with open(design_md_path, 'r') as f:
        content = f.read()

    for css_var, new_value in new_tokens.items():
        # Regex qui trouve la ligne du CSS var et remplace la valeur
        pattern = rf'({re.escape(css_var)}:\s+)#[0-9a-fA-F]{{3,8}}'
        replacement = rf'\g<1>{new_value}'
        content = re.sub(pattern, replacement, content)

    with open(design_md_path, 'w') as f:
        f.write(content)

    print(f"DESIGN.md updated: {len(new_tokens)} tokens modified")
```

---

## ÉTAPE 5 — Création de version (Design API)

```python
import hashlib, json
from datetime import datetime

def create_design_version(tokens: dict, author: str, description: str) -> str:
    version_data = {
        "tokens": tokens,
        "created_at": datetime.utcnow().isoformat(),
        "created_by": author,
        "description": description
    }

    version_hash = hashlib.sha256(
        json.dumps(tokens, sort_keys=True).encode()
    ).hexdigest()[:12]

    # POST /design/versions
    response = design_api.post("/design/versions", {
        "id": version_hash,
        "data": version_data
    })

    # Met HEAD à jour
    design_api.post(f"/design/versions/rollback/{version_hash}")

    return version_hash
```

---

## ÉTAPE 6 — Conformance Check post-update

```bash
# Vérifie que tous les composants compilent avec les nouveaux tokens
# Lance le ConformanceAgent en mode surface+structure only (pas substance)
# Si score < 90% → rollback automatique vers version précédente

curl -X POST http://localhost:8000/ada/conformance/check \
  -H "Content-Type: application/json" \
  -d '{"scope": ["surface", "structure"], "auto_rollback": true, "threshold": 0.90}'
```

---

## ACCEPTANCE TEST — Skill complet

```bash
# Test end-to-end du pipeline NLP → version créée

python -c "
import asyncio
from app.skills.penpot_to_design_md import PenpotToDesignMdSkill

async def test():
    skill = PenpotToDesignMdSkill()

    # Simule intent NLP
    intent = await skill.analyze_nlp('je veux que le clone soit en violet foncé')
    assert '--agent-clone' in [e['token'] for e in intent['elements']]
    print('NLP analysis OK')

    # Extrait tokens depuis un fichier de test
    tokens = await skill.extract_from_penpot(mock_penpot_file)
    assert '--agent-clone' in tokens
    print('Token extraction OK')

    # Vérifie que DESIGN.md est mis à jour
    await skill.update_design_md(tokens)
    with open('DESIGN.md') as f:
        content = f.read()
    assert tokens['--agent-clone'] in content
    print('DESIGN.md update OK')

    # Vérifie qu'une version est créée
    version_id = await skill.create_version(tokens, 'test', 'NLP test')
    assert version_id is not None
    print(f'Version created OK: {version_id}')

asyncio.run(test())
"
```

---

*Skill: penpot-to-design-md · v1.0 · 2026-05-25*
*Dépend de: Penpot MCP (ghcr.io/astrateam-net/penpot-mcp) · Design API (Composant 14)*
