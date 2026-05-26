# MOCKS.md — Cockpit Stern v2
> Mocks actifs en production · 2026-05-26

---

## Mocks actifs

### L3 — Graphiti (Knowledge Graph temporel)
- **Composant**: `services/memory.py` → `_graphiti_available()`
- **Raison**: `GRAPHITI_NEO4J_URI` non configuré. Pas de Neo4j déployé.
- **Impact**: Les relations causales (leads, projets, décisions) ne sont pas stockées en graph. La mémoire fonctionne avec L1 (Redis) + L2 (Mem0) + L4 (pgvector).
- **Fix**: Déployer Neo4j, configurer `GRAPHITI_NEO4J_URI`, `GRAPHITI_NEO4J_USER`, `GRAPHITI_NEO4J_PASSWORD` dans `.env`.
- **Log**: `L3 skipped, no Neo4j configured`

### L2 — Mem0 (conversationnel moyen terme)
- **Composant**: `services/memory.py` → `_get_mem0()`
- **Raison**: `MEM0_API_KEY` non configuré.
- **Impact**: L'historique conversationnel moyen terme et les patterns de décision ne sont pas persistés. La mémoire court terme (Redis L1) fonctionne.
- **Fix**: Créer un compte Mem0, configurer `MEM0_API_KEY` dans `.env`.
- **Log**: `Mem0 init failed` ou silencieux

### L4 — pgvector (RAG sémantique)
- **Composant**: `models/session.py` → `MemoryEmbedding`
- **Raison**: Extension pgvector créée mais embeddings pas encore générés (nécessite des interactions).
- **Impact**: Le RAG sémantique sera opérationnel dès les premières interactions stockées.
- **Fix**: Automatique — les embeddings se génèrent à mesure que les interactions sont stockées.

### MCPClient — Obot/Nango tools
- **Composant**: `services/mcp_client.py` → `discover_tools()`, `call()`
- **Raison**: Obot et Nango sont déployés mais pas encore configurés avec des intégrations OAuth.
- **Impact**: `discover_tools()` retourne des mock tools `{"name": "...", "available": false, "mock": true}`. `call()` retourne un mock response. Les agents ne peuvent pas agir dans les outils externes (Notion, GitHub, Calendar).
- **Fix**: Configurer les intégrations dans Nango (`https://nango-stern-os2.ori3com.cloud`), puis les tools dans Obot (`https://obot-stern-os2.ori3com.cloud`).

### Penpot MCP — Design pipeline
- **Composant**: `api/design.py` → `POST /design/penpot/sync`
- **Raison**: Penpot MCP non déployé. `.mcp.json` non configuré.
- **Impact**: Le pipeline NLP → Penpot → tokens → version n'est pas opérationnel. L'intent NLP fonctionne (`POST /design/nlp/intent`), la création de version manuelle aussi (`POST /design/versions`).
- **Fix**: Déployer Penpot + Penpot MCP dans le docker-compose. Configurer `.mcp.json`.
- **Response**: `{"status": "mock", "message": "Penpot MCP sync not yet configured."}`

### ConformanceAgent — Playwright headless
- **Composant**: `agents/nodes/conformance.py` → `_check_surface()`
- **Raison**: Pas de Playwright installé. Le surface check utilise une heuristique (comptage endpoints) au lieu de crawler réellement l'UI.
- **Impact**: Le score surface est toujours 1.0 par défaut. Un vrai audit nécessite Playwright.
- **Fix**: Ajouter `playwright` aux dépendances backend, implémenter le crawl headless.

### Langfuse — Callbacks LLM
- **Composant**: `agents/nodes/*.py`
- **Raison**: `LANGFUSE_PUBLIC_KEY` et `LANGFUSE_SECRET_KEY` non configurés.
- **Impact**: Les traces LLM (session_id, profile_id, active_agent, task_type) ne sont pas loguées dans Langfuse. Le service Langfuse tourne (`https://trace-stern-os2.ori3com.cloud`) mais n'est pas connecté aux agents.
- **Fix**: Créer un projet dans Langfuse, configurer les clés dans `.env`.

---

## Résumé

| Mock | Criticité | Effort fix |
|---|---|---|
| L3 Graphiti | Basse | Moyen (deploy Neo4j) |
| L2 Mem0 | Moyenne | Faible (juste une API key) |
| L4 pgvector | Auto-résolu | — |
| MCPClient Obot/Nango | Haute | Moyen (config intégrations) |
| Penpot MCP | Basse | Élevé (deploy Penpot stack) |
| Conformance Playwright | Basse | Faible (pip install + code) |
| Langfuse callbacks | Moyenne | Faible (juste des clés) |

---

*MOCKS.md généré le 2026-05-26*
