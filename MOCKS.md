# MOCKS.md — Cockpit Stern v2
> Mocks actifs en production · 2026-05-26 (updated)

---

## Mocks actifs

### L3 — Graphiti (Knowledge Graph temporel)
- **Composant**: `services/memory.py` → `_graphiti_available()`
- **Raison**: `GRAPHITI_NEO4J_URI` non configuré
- **Impact**: Relations causales non stockées en graph. Mémoire fonctionne via L1+L2+L4.
- **Fix**: Déployer Neo4j, configurer env vars
- **Criticité**: Basse

### L2 — Mem0 (conversationnel moyen terme)
- **Composant**: `services/memory.py` → `_get_mem0()`
- **Raison**: `MEM0_API_KEY` non configuré
- **Impact**: Historique moyen terme non persisté entre redémarrages
- **Fix**: Configurer `MEM0_API_KEY`
- **Criticité**: Moyenne

### Langfuse callbacks
- **Composant**: `services/langfuse_callback.py`
- **Raison**: `LANGFUSE_PUBLIC_KEY` et `LANGFUSE_SECRET_KEY` non configurés
- **Impact**: Traces LLM non loguées. L'infra Langfuse tourne (`trace-stern-os2.ori3com.cloud`)
- **Fix**: Créer un projet dans Langfuse, configurer les clés
- **Criticité**: Moyenne

### Penpot MCP sync
- **Composant**: `api/design.py` → `POST /design/penpot/sync`
- **Raison**: Penpot stack en cours de stabilisation
- **Impact**: Pipeline NLP → Penpot → tokens pas encore opérationnel. L'intent NLP fonctionne.
- **Fix**: Stabiliser Penpot, configurer `.mcp.json`
- **Criticité**: Basse

## Mocks résolus (depuis dernière version)

- ~~MCPClient Obot/Nango~~ → Obot et Nango containers UP, DSN connectés
- ~~L4 pgvector embeddings~~ → Implémenté via `openrouter/text-embedding-3-small`
- ~~Conformance Playwright~~ → Remplacé par crawl API réel (83% surface)
- ~~HITL endpoint~~ → `POST /api/chat/hitl/{token}` implémenté
- ~~Pattern detector~~ → Background task hourly implémenté
- ~~Langfuse infra~~ → Container running, juste les clés à configurer

---

| Mock | Criticité | Effort fix |
|---|---|---|
| L3 Graphiti | Basse | Moyen |
| L2 Mem0 | Moyenne | Faible |
| Langfuse callbacks | Moyenne | Faible |
| Penpot sync | Basse | Moyen |

*MOCKS.md updated 2026-05-26*
