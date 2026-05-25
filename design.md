# DESIGN.md — Cockpit Stern Design System
## API-Driven · Versioned · Hyperpersonalisable · Penpot-Native
> Version 2.0 · 2026-05-25

---

## ARCHITECTURE GLOBALE

```
NLP utilisateur
    ↓ Penpot MCP (66 tools)
Penpot Design File (source de vérité visuelle)
    ↓ skill: penpot-to-design-md
tokens.json (extrait depuis Penpot)
    ↓
DESIGN.md (ce fichier — spec authoritative)
    ↓ Claude Code CLI
Composants React (headless, invariants)
    ↓ Design API
Version Registry (immutable snapshots)
    ↓ CSS cascade RBAC
Interface End-User (hyperpersonnalisée)
```

**Règle fondamentale** :
Penpot est la source de vérité visuelle.
DESIGN.md est la source de vérité technique.
Les deux sont synchronisés par le pipeline NLP→Penpot→DESIGN.md.
Jamais de valeur hardcodée dans les composants.

---

## MODÈLE D'INVARIANCE ET D'IMMUTABILITÉ

### Invariant = contrat de composant (TypeScript interface)
L'interface d'un composant ne change JAMAIS entre versions.
Si un breaking change est nécessaire → nouveau composant, pas modification.

```typescript
// INVARIANT v1 — ne change jamais
interface ButtonProps {
  label: string
  onClick: () => void
  variant: 'primary' | 'secondary' | 'ghost' | 'danger'
  size: 'sm' | 'md' | 'lg'
  agent?: 'sp' | 'clone' | 'anti' | 'real'
  loading?: boolean
  disabled?: boolean
}
// Si besoin d'un nouveau prop → ButtonV2Props extends ButtonProps
```

### Immutable = snapshot versionné (git-like)
Chaque version publiée est un objet content-addressed.
Le pointeur HEAD peut être déplacé (rollback).
Les versions passées ne peuvent pas être modifiées.

```
Versions:
  v1.0.0 · hash:abc123 · "Initial dark theme"
  v1.1.0 · hash:def456 · "Amber accent pour décisions"
  v1.2.0 · hash:ghi789 · "Penpot NLP: purple header Cindy"
  HEAD ──────────────────► v1.2.0

Rollback vers v1.1.0:
  HEAD ──────────────────► v1.1.0  (v1.2.0 préservé)
```

---

## LAYERS DE PERSONNALISATION (CSS CASCADE RBAC)

```
LAYER 0 — Design Tokens Base     [admin · immutable par version]
LAYER 1 — Tenant Theme           [tenant admin · override tokens]
LAYER 2 — Role Layout            [role-based · menus, sections]
LAYER 3 — User Preferences       [per-user · couleurs, layout]
LAYER 4 — Session State          [éphémère · panels ouverts, scroll]
```

### Implémentation CSS cascade
```css
/* LAYER 0 — base (version v1.1.0) */
:root {
  --agent-sp: #1BB68A;
  --agent-clone: #7B6EE8;
  --agent-anti: #E05A2B;
  --agent-real: #C9851A;
  --bg-void: #07070D;
  /* ... tous les tokens */
}

/* LAYER 1 — tenant override */
[data-tenant="acme"] {
  --agent-clone: #0066FF;  /* brand color Acme */
}

/* LAYER 2 — role layout */
[data-role="coach"] {
  --sidebar-width: 320px;
  --show-anti-panel: block;
}
[data-role="client"] {
  --sidebar-width: 0px;
  --show-anti-panel: none;
}

/* LAYER 3 — user preference (injecté dynamiquement) */
[data-user="benoit"] {
  --agent-sp: var(--user-pref-sp, #1BB68A);
  --font-scale: var(--user-pref-font-scale, 1);
}
```

### UserPreferences schema (stocké en Postgres JSONB)
```typescript
interface UserPreferences {
  userId: string
  version: string          // version de base sur laquelle s'appliquent les overrides

  theme: {
    agentColors: {
      sp?: string          // hex override
      clone?: string
      anti?: string
      real?: string
    }
    fontScale?: number     // 0.8 → 1.2
    reducedMotion?: boolean
    highContrast?: boolean
  }

  layout: {
    sidebarWidth?: number
    sidebarPosition?: 'left' | 'right'
    compactMode?: boolean
    visibleSections?: string[]    // RBAC-gated
    menuOrder?: string[]          // drag-and-drop order
    pinnedAgents?: AgentType[]
  }

  components: {
    [componentId: string]: {
      labels?: Record<string, string>     // override labels
      visible?: boolean                    // show/hide
      position?: { x: number; y: number } // custom placement
    }
  }
}
```

---

## DESIGN API — Endpoints

```
# VERSIONS
GET  /design/versions              → liste toutes les versions
GET  /design/versions/{v}          → snapshot immutable complet
POST /design/versions              → crée nouvelle version depuis tokens.json
POST /design/versions/rollback/{v} → déplace HEAD vers v
GET  /design/versions/diff/{v1}/{v2} → diff entre deux versions

# TOKENS
GET  /design/tokens                → tokens de la version active (HEAD)
GET  /design/tokens/{v}            → tokens d'une version spécifique
POST /design/tokens/import         → importe depuis Penpot (via pipeline)

# COMPOSANTS
GET  /design/components            → registry des composants disponibles
GET  /design/components/{id}       → spec complète (props + tokens utilisés)
GET  /design/components/{id}/variants → toutes les variantes

# PERSONNALISATION
GET  /design/user/{id}/preferences → préférences utilisateur
PUT  /design/user/{id}/preferences → sauvegarde overrides
DELETE /design/user/{id}/preferences/{key} → reset une préférence
GET  /design/user/{id}/css-vars    → génère les CSS vars personnalisées

# RBAC
GET  /design/rbac/{role}           → config layout + permissions par rôle
PUT  /design/rbac/{role}           → met à jour config rôle (admin)

# NLP → DESIGN
POST /design/nlp/intent            → analyse NLP → intent design
POST /design/nlp/to-penpot         → NLP → Penpot via MCP
POST /design/penpot/extract        → extrait tokens depuis file Penpot
POST /design/penpot/sync           → sync Penpot → DESIGN.md → nouvelle version
```

---

## PIPELINE NLP → PENPOT → DESIGN.md

### Étape 1 — NLP Intent Analysis
```python
# POST /design/nlp/intent
# Input: "je veux un cockpit sombre avec accent violet pour le clone"
# Output:
{
  "intent": "theme_override",
  "elements": [
    {"token": "--agent-clone", "value": "violet/purple", "confidence": 0.92},
    {"token": "--bg-void", "value": "dark", "confidence": 0.88}
  ],
  "penpot_instructions": "Create a dark workspace panel with purple (#7B3FE8) accent..."
}
```

### Étape 2 — Penpot MCP Execution
```
Claude Code CLI + Penpot MCP (66 tools) :

→ penpot/create-color-style: {name: "agent-clone-custom", color: "#7B3FE8"}
→ penpot/apply-color-to-components: {color: "agent-clone-custom", targets: [...]}
→ penpot/export-design-tokens: {format: "json", file: "tokens.json"}
```

### Étape 3 — Token Extraction (skill: penpot-to-design-md)
```python
# Lit tokens.json exporté par Penpot
# Mappe vers DESIGN.md token names
# Crée PR ou écrit directement selon mode (HITL/MITL/YOLO)
token_map = {
  "agent/sp/default": "--agent-sp",
  "agent/clone/default": "--agent-clone",
  "semantic/background/void": "--bg-void",
  # ...
}
```

### Étape 4 — Version Creation
```
tokens.json → hash(tokens) → version_id
Postgres: INSERT INTO design_versions (id, tokens, created_at, created_by)
Redis: SET design:HEAD design_versions:{id}
Conformance Agent: vérifie que tous les composants compilent avec les nouveaux tokens
```

---

## COMPOSANT ÉDITABILITÉ — Spécification

Chaque composant est éditable par l'utilisateur selon son RBAC.
L'édition est **toujours non-destructive** : delta over base, jamais modification base.

### EditableComponent wrapper
```typescript
interface EditableComponentProps {
  componentId: string      // identifiant unique dans le registry
  editableProps: string[]  // quels props sont éditables par l'user
  rbacKey?: string         // permission requise pour éditer
  children: React.ReactNode
}

// Usage :
<EditableComponent
  componentId="topbar-energy-label"
  editableProps={['label', 'visible']}
  rbacKey="user.preferences.edit"
>
  <EnergySlider label="Énergie" />
</EditableComponent>
```

### Edit Mode (shift+click sur tout composant)
```
Shift+Click sur n'importe quel composant → Edit Panel apparaît:
  ├── Onglet Style: CSS var overrides (color picker, font scale)
  ├── Onglet Content: labels éditables (si rbac ok)
  ├── Onglet Layout: position, visible, taille
  └── Onglet Reset: remet les valeurs par défaut
Toutes les modifications → POST /design/user/{id}/preferences
```

### Drag-and-drop sections
```typescript
// Layout config stockée en JSONB par user:
{
  "menuOrder": ["profile", "energy", "okr", "agents", "memory"],
  "sidebarSections": {
    "profile": { "visible": true, "collapsed": false },
    "agents": { "visible": true, "collapsed": false },
    "okr": { "visible": true, "collapsed": true }
  }
}
```

---

## DESIGN TOKENS — Référence complète

### Couleurs agents (invariants identitaires)
```css
:root {
  --agent-sp:          #1BB68A; /* teal   · Vrai SP · flow · amplification */
  --agent-sp-dim:      #0D6B52; /* teal foncé · états inactifs */
  --agent-sp-glow:  rgba(27,182,138,0.12);

  --agent-clone:       #7B6EE8; /* purple · Clone IA · stratégie · profondeur */
  --agent-clone-dim:   #4A3FA8;
  --agent-clone-glow: rgba(123,110,232,0.12);

  --agent-anti:        #E05A2B; /* coral  · Anti SP · tension · challenge */
  --agent-anti-dim:    #8C3518;
  --agent-anti-glow:  rgba(224,90,43,0.12);

  --agent-real:        #C9851A; /* amber  · Réel · décision · authenticité */
  --agent-real-dim:    #7A4F0E;
  --agent-real-glow:  rgba(201,133,26,0.12);

  /* SEMANTIC */
  --color-ok:          #1BB68A;
  --color-warn:        #C9851A;
  --color-stop:        #E05A2B;
  --color-info:        #4A8FE8;

  /* BACKGROUNDS */
  --bg-void:           #07070D;
  --bg-surface:        #0F0F1A;
  --bg-raised:         #161625;
  --bg-overlay:        #1D1D30;

  /* TEXT */
  --text-primary:      #F2F2FA;
  --text-secondary:    #9090B0;
  --text-tertiary:     #5A5A7A;

  /* BORDERS */
  --border-subtle:  rgba(255,255,255,0.06);
  --border-default: rgba(255,255,255,0.10);
  --border-strong:  rgba(255,255,255,0.18);
  --border-focus:   #7B6EE8;

  /* SPACING — 4px base */
  --s1:4px; --s2:8px; --s3:12px; --s4:16px; --s5:20px;
  --s6:24px; --s8:32px; --s10:40px; --s12:48px; --s16:64px;

  /* RADIUS */
  --r-sm:6px; --r-md:10px; --r-lg:16px; --r-xl:24px; --r-full:9999px;

  /* TYPOGRAPHY */
  --font-display: 'Syne', 'DM Sans', system-ui, sans-serif;
  --font-mono:    'JetBrains Mono', 'Fira Code', monospace;

  /* MOTION */
  --ease-snap:  cubic-bezier(0.34,1.56,0.64,1);
  --ease-flow:  cubic-bezier(0.4,0,0.2,1);
  --dur-fast:   80ms;
  --dur-base:   160ms;
  --dur-slow:   280ms;
  --dur-pulse:  2000ms;
}
```

---

## NEUROSCIENCES — 6 PRINCIPES CODIFIÉS

### P1 — Anti-DMN · Ancre visuelle permanente
```
Implémentation: agent indicator pulse visible en topbar 100% du temps
Spec: opacity jamais < 0.4 sur l'agent actif · pulse animation --dur-pulse
Test: eye-tracking simulé → point de retour < 800ms après décrochage
```

### P2 — Dopamine Loop · Feedback < 100ms
```
Implémentation: --dur-fast: 80ms sur tous les états interactifs
Spec: idle→hover→active→done en 4 états visuels distincts
Test: Lighthouse performance · INP < 100ms sur toutes les interactions
```

### P3 — Miller's Law · Max 5 chunks
```
Implémentation: jamais > 5 options dans un message Clone
Spec: progressive disclosure obligatoire si > 5 items
Test: cognitive load audit par écran (score max 7)
```

### P4 — Predictive Processing · Layout stable
```
Implémentation: agents toujours SP|CLONE|ANTI|REAL · jamais réordonnés
Spec: aucun changement de layout sans action utilisateur explicite
Test: A/B test retention 30 jours · layout stable > layout flexible
```

### P5 — One Task Per Screen · Focus unique
```
Implémentation: une seule CTA primaire par vue · HITL bloque tout
Spec: z-index modal > 9000 · backdrop inert sur tout le reste
Test: user test · temps de décision sur HITL < 5 secondes
```

### P6 — Accessibilité Neurodivergente
```
TDAH  : ancre pulse · timer visible si tâche > 30s · 0 notification pendant focus
THPI  : densité expandable · tous raccourcis clavier documentés
TSA   : layout 100% stable · icône + label obligatoire · 0 animation scroll
Vision: ratio contraste WCAG AAA (7:1) sur text primary
Moteur: focus ring visible · tab order logique · touch targets 44px min
```

---

## COMPOSANTS — REGISTRY

| Composant | Invariant v | Tokens utilisés | RBAC édition |
|---|---|---|---|
| AgentBadge | v1 | --agent-{type}, --dur-pulse | non |
| ChatMessage | v1 | --agent-{type}-glow, --bg-* | label uniquement |
| DryRunDiff | v1 | --color-ok/warn/stop | non |
| HitlModal | v1 | --agent-real, --bg-raised | non |
| EnergySlider | v1 | --agent-sp/real/anti | label, visible |
| OkrAlignmentBadge | v1 | --color-ok/warn/stop | visible |
| ConformanceIndicator | v1 | --color-ok/warn/stop | visible |
| TopBar | v1 | tous agents | ordre sections |
| Sidebar | v1 | --bg-surface, --border-* | sections + ordre |
| ChatInput | v1 | --border-focus, --bg-overlay | placeholder |

---

## PENPOT INTÉGRATION

### Penpot MCP dans docker-compose
```yaml
penpot:
  image: penpotapp/backend:latest
  # ... config standard Penpot

penpot-mcp:
  image: ghcr.io/astrateam-net/penpot-mcp:latest
  ports: ["8787:8787"]
  environment:
    PENPOT_API_URL: http://penpot:6060
    PENPOT_ACCESS_TOKEN: ${PENPOT_ACCESS_TOKEN}
  depends_on: [penpot]
```

### .mcp.json pour Claude Code CLI
```json
{
  "mcpServers": {
    "penpot": {
      "type": "http",
      "url": "http://localhost:8787/mcp"
    }
  }
}
```

### 66 tools disponibles (11 catégories)
```
shapes       · create-rect, create-text, create-group, ...
styles       · create-color-style, apply-fill, apply-stroke, ...
typography   · create-font-style, apply-typography, ...
layout       · create-frame, set-grid, set-flex, ...
components   · create-component, detach-component, ...
pages        · create-page, navigate-page, ...
export       · export-design-tokens, export-assets, ...
query        · get-components, get-colors, get-typography, ...
transform    · resize, move, rotate, ...
prototype    · add-interaction, create-flow, ...
tokens       · get-tokens, set-token, export-tokens, ...
```

---

## FICHIERS DU SYSTÈME

```
design-system/
├── DESIGN.md                    ← ce fichier (spec authoritative)
├── design-system.html           ← référence visuelle interactive
├── skills/
│   └── penpot-to-design-md.md   ← skill Claude Code CLI
├── tokens/
│   ├── base.css                 ← layer 0 tokens
│   ├── tenant.css               ← layer 1 template
│   └── tokens.json              ← export Penpot (source)
├── components/                  ← composants headless
│   ├── AgentBadge/
│   │   ├── index.tsx            ← implémentation
│   │   ├── types.ts             ← interface invariante v1
│   │   └── AgentBadge.stories.tsx
│   └── ... (un dossier par composant)
├── adapters/
│   ├── langgraph.adapter.ts
│   ├── obot.adapter.ts
│   └── dify.adapter.ts
└── api/
    └── design-api.ts            ← client SDK Design API
```

---

*DESIGN.md v2.0 · 2026-05-25*
*Neuroscience: DMN (Buckner 2008), Miller 1956, Clark 2015, Yablonski 2020*
*Penpot MCP: github.com/penpot/penpot/tree/develop/mcp (66 tools)*
