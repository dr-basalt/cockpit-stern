# DONE.md — Cockpit Stern v2
> Build report · 2026-05-26
> Mode: YOLO MITL · No HITL during build

---

## Composants buildés

| # | Composant | Status | Notes |
|---|---|---|---|
| 1 | Config + Database | ✅ | pydantic-settings, SQLAlchemy async + pgvector |
| 2 | HumanProfile | ✅ | Modèle générique, Clifton→Domaine mapping FR/EN |
| 3 | InversionRules Engine | ✅ | 4 system prompts dynamiques, energy modes, HITL triggers |
| 4 | Memory Cascade L1→L4 | ⚠️ | L1 Redis + L2 Mem0 (mock si absent) + L4 pgvector. L3 Graphiti **mock** (pas de Neo4j) |
| 5 | LangGraph Graph | ✅ | filter_sp → supervisor → clone/anti/sp/hitl → formatter → END |
| 6 | FastAPI API | ✅ | REST + WebSocket /chat/stream |
| 7 | Pattern Detector | ✅ | Background task, not-self frequency analysis |
| 8 | Docker + Coolify | ✅ | docker-compose.prod.yml (Traefik + SSL Let's Encrypt) |
| 9 | Frontend Next.js | ✅ | Onboarding, Cockpit (WS+REST), Profile. 10 composants design-system |
| 10 | .env + Alembic | ✅ | .env.example, migrations auto via init_db() |
| 11 | Nango + Obot + MCPClient | ⚠️ | Containers running. MCPClient adapter implémenté. Nango/Obot pas encore configurés avec des intégrations |
| 12 | ADA API + SubAgent Spawner + OKR | ✅ | SCRUDX /ada/agents, /ada/tools, /ada/okr, /ada/conformance |
| 13 | ConformanceAgent + MITLValidator | ✅ | Surface/Structure/Substance checks. MITL via claude-sonnet-4 |
| 14 | Design API + Versioning | ✅ | /design/versions, /design/tokens, /design/user prefs, /design/nlp/intent |

**Score: 12/14 complets, 2/14 partiels (mocks actifs)**

---

## Conformance Report

```
Surface:   100%  (toutes les actions UI ont un équivalent API)
Structure:   0%  (aucun sub-agent spawné → pas de validation structure)
Substance: 100%  (pas d'agents = pas de désalignement)
Overall:    60%
```

Score structure à 0% est normal : aucun sub-agent n'a été spawné via /ada/agents/spawn.
Dès qu'un agent est spawné avec template + OKR, le score monte.

---

## E2E Test Results (2026-05-26)

| Test | Résultat | Détails |
|---|---|---|
| Health check | ✅ | `{"status":"ok","environment":"production"}` |
| Profile CRUD | ✅ | Create + Get + dominant_domain=ST + clone/anti personas |
| Chat → Clone (production) | ✅ | 3 options oui/non, energy_mode=brake, formatage Generator |
| Chat → SP (not-self) | ✅ | not_self_detected=true, energy_mode=accelerate, alerte frustration |
| Chat → HITL (irréversible) | ✅ | requires_hitl=true, hitl_token généré, task=irreversible_decision |
| ADA discovery | ✅ | /ada/agents, /ada/conformance, /ada/tools |
| Design NLP intent | ✅ | "clone en violet" → `--agent-clone: #7B3FE8` |
| WebSocket streaming | ✅ | Events: agent, chunk, meta, done |
| Frontend landing | ✅ | COCKPIT STERN, 2 CTAs |
| Frontend onboarding | ✅ | Formulaire complet → redirect cockpit |
| Frontend cockpit | ✅ | Agent badges, energy slider, chat WS/REST |

---

## Infrastructure

| Ressource | Détails |
|---|---|
| VPS | Hetzner cpx32 · 4vCPU x86 · 8GB RAM · `178.104.251.192` · Nuremberg |
| OS | Ubuntu 24.04 · Docker 29.5.2 · Compose v5.1.4 |
| SSL | Let's Encrypt via Traefik v2.11 DNS challenge (Cloudflare) |
| GitHub | [dr-basalt/cockpit-stern](https://github.com/dr-basalt/cockpit-stern) |

### Services running (8/8)

| Container | Status | URL |
|---|---|---|
| backend (FastAPI) | UP | `https://api-stern-os2.ori3com.cloud` |
| frontend (Next.js 15) | UP | `https://stern-os2.ori3com.cloud` |
| postgres (pgvector:16) | Healthy | interne |
| redis (7-alpine) | Healthy | interne |
| traefik (v2.11) | UP | SSL terminaison |
| langfuse (v2) | UP | `https://trace-stern-os2.ori3com.cloud` |
| nango (server) | UP | `https://nango-stern-os2.ori3com.cloud` |
| obot | UP | `https://obot-stern-os2.ori3com.cloud` |

---

## LLM Routing (via OpenRouter)

| Agent | Modèle | Tier | Coût |
|---|---|---|---|
| filter_sp + supervisor | Heuristique (pas de LLM) | — | $0 |
| clone + anti + sp | `openrouter/deepseek/deepseek-chat-v3-0324` | pro | ~$0.001/1K |
| formatter | `openrouter/google/gemini-2.0-flash-001` | evergreen | ~$0 |
| MITL validator | `openrouter/anthropic/claude-sonnet-4` | max | ~$0.01/1K |
| Fallback (tous) | `openrouter/anthropic/claude-haiku-4-5` | — | ~$0.001/1K |

---

## Commandes

### Démarrage local (dev)
```bash
cp .env.example .env
# Remplir les clés API dans .env
docker compose up -d
# Frontend: http://localhost:3000
# Backend:  http://localhost:8000
# Health:   http://localhost:8000/health
```

### Démarrage production
```bash
# Sur le VPS
cd /opt/cockpit-stern
git pull origin main
docker compose -f docker-compose.prod.yml up -d --build
```

### Mise à jour
```bash
ssh root@178.104.251.192 "cd /opt/cockpit-stern && git pull && docker compose -f docker-compose.prod.yml up -d --build"
```

### Tests
```bash
PYTHONPATH=./backend python3 -m pytest tests/ -v
```

---

## Mocks actifs

Voir `MOCKS.md`

---

*DONE.md généré le 2026-05-26 · 14 composants · 15 tests · 8 containers · E2E vert*
