# BLUEPRINT — Cockpit Sparring Partner
## Native AI Digital Agency · Generic Agent Kernel
> Plan d'exécution GetShitDone · YOLO MITL · Pas de staging
> Source technique : "Designing Agentic AI Applications" — O'Reilly (Albada, Ch.5-8)

---

## INTENT

Construire un système multi-agents générique qui :
1. Prend en entrée le profil d'un humain (Human Design + Clifton 34 + mantra + invariants)
2. Configure automatiquement 4 agents personnalisés (VRAI_SP · CLONE · ANTI · REAL)
3. Route chaque input vers l'agent correct selon hd_authority + energy_level
4. Formate chaque output selon le hd_type de l'utilisateur
5. Maintient une mémoire cascade L1→L4 par profil isolé
6. S'autodéploie sur Coolify via docker-compose

L'individu réel ne reçoit que ce qu'il peut traiter selon son type.
Le digital twin (Clone + Anti) opère en continu sans lui.

---

## STRUCTURE CIBLE

```
cockpit-sparring/
├── start.md                         # entry point Claude Code CLI
├── blueprint.md                     # ce fichier
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py
│       ├── core/
│       │   ├── config.py            # pydantic-settings, toutes les env vars
│       │   └── database.py          # SQLAlchemy async + pgvector
│       ├── models/
│       │   ├── profile.py           # HumanProfile — modèle générique
│       │   └── session.py
│       ├── agents/
│       │   ├── state.py             # AgentState TypedDict
│       │   ├── graph.py             # LangGraph graph complet
│       │   └── nodes/
│       │       ├── filter_sp.py     # VRAI_SP — entry point unique
│       │       ├── supervisor.py    # profile-aware router
│       │       ├── clone.py         # ST-dominant producer
│       │       ├── anti.py          # blind-spot challenger
│       │       └── formatter.py     # HD-type output formatter
│       ├── services/
│       │   ├── inversion.py         # InversionRules engine
│       │   ├── memory.py            # cascade L1(Redis)→L2(Mem0)→L3(Graphiti)→L4(pgvector)
│       │   ├── profile_store.py     # Postgres CRUD
│       │   └── pattern_detector.py  # background task, détection patterns
│       └── api/
│           ├── chat.py              # POST /chat + WebSocket /chat/stream
│           ├── profile.py           # CRUD /profile
│           └── session.py
├── frontend/
│   ├── package.json
│   ├── next.config.ts
│   ├── vercel.json
│   └── src/
│       ├── app/
│       │   ├── onboarding/page.tsx  # formulaire profil complet
│       │   ├── cockpit/page.tsx     # interface principale
│       │   └── profile/page.tsx    # édition profil
│       └── components/
│           ├── AgentBadge.tsx
│           ├── EnergySlider.tsx
│           ├── ChatStream.tsx
│           └── HitlModal.tsx
├── alembic/
│   ├── alembic.ini
│   └── versions/
├── tests/
│   ├── test_inversion.py
│   ├── test_graph.py
│   ├── test_memory.py
│   └── test_api.py
├── docker-compose.yml               # dev local
├── docker-compose.coolify.yml       # prod Coolify
├── .env.example
└── MOCKS.md                         # généré automatiquement si mock activé
```

---

## DÉPENDANCES D'EXÉCUTION

```
profile.py → database.py → config.py
inversion.py → profile.py
memory.py → config.py → database.py
state.py (autonome)
filter_sp.py → state.py → inversion.py → memory.py
supervisor.py → state.py → inversion.py
clone.py → state.py → inversion.py → memory.py
anti.py → state.py → inversion.py
formatter.py → state.py → inversion.py
graph.py → tous les nodes
api/chat.py → graph.py → memory.py
api/profile.py → profile_store.py
main.py → tous les api
docker-compose → tout le backend
frontend → api (via env NEXT_PUBLIC_API_URL)
```

---

## COMPOSANT 1 — Config + Database

### config.py
Utilise pydantic-settings. Variables requises :
```python
DATABASE_URL: str          # postgresql+asyncpg://...
REDIS_URL: str             # redis://...
ANTHROPIC_API_KEY: str
LITELLM_MASTER_KEY: str    # optionnel
LANGFUSE_PUBLIC_KEY: str
LANGFUSE_SECRET_KEY: str
LANGFUSE_HOST: str         # https://cloud.langfuse.com ou self-hosted
MEM0_API_KEY: str          # optionnel — si absent, use local mode
GRAPHITI_NEO4J_URI: str    # optionnel — si absent, skip L3
GRAPHITI_NEO4J_USER: str
GRAPHITI_NEO4J_PASSWORD: str
SECRET_KEY: str
ENVIRONMENT: str           # development | production
```

### database.py
SQLAlchemy async avec pgvector. Crée l'extension pgvector au démarrage si absente.

### Migrations Alembic
Crée les tables : profiles, sessions, interactions, memory_embeddings

## ACCEPTANCE TEST 1
```bash
cd backend && python -c "
from app.core.config import settings
from app.core.database import engine
print('Config OK:', settings.ENVIRONMENT)
import asyncio
async def test():
    async with engine.connect() as conn:
        result = await conn.execute(text('SELECT 1'))
        print('DB OK:', result.scalar())
asyncio.run(test())
"
# PASS si les deux prints s'affichent sans exception
```

---

## COMPOSANT 2 — HumanProfile (modèle générique)

### models/profile.py

```python
# Modèle GÉNÉRIQUE — applicable à n'importe quel humain
# Les valeurs Benoit sont des INSTANCES, pas des valeurs par défaut

class HumanProfile(Base):
    # Identité
    id: UUID
    name: str
    created_at: datetime
    updated_at: datetime

    # Human Design — champs obligatoires
    hd_type: Literal[
        "Generator", "Manifesting Generator", "Projector",
        "Manifestor", "Reflector"
    ]
    hd_authority: Literal[
        "Sacral", "Emotional", "Splenic", "Ego",
        "Self-Projected", "Mental", "Lunar", "None"
    ]
    hd_profile: str          # "4/1", "2/4", "6/2", "1/3", etc.
    hd_definition: Literal[
        "Simple", "Split", "Triple Split", "Quadruple Split"
    ]
    hd_cross: str | None     # nom de la Croix incarnée (optionnel)
    hd_signature: str        # état d'alignement (ex: "Satisfaction")
    hd_not_self: str         # signal d'arrêt (ex: "Frustration")

    # Clifton StrengthsFinder
    clifton_top5: list[str]     # top 5 — puissance maximale
    clifton_bottom5: list[str]  # blind spots — déléguer
    clifton_all34: list[str] | None  # liste complète si disponible

    # Identité profonde
    mantra: str
    invariants: list[str]    # axiomes non-négociables

    # État dynamique (mis à jour par check-in)
    energy_level: int        # 1-10, défaut 5

    # Computed (pas stocké en DB, calculé à la volée)
    @property
    def dominant_domain(self) -> str:
        # ST (Réflexion Stratégique) | EX (Exécution) | REL (Relation) | INF (Influence)
        # Inféré depuis clifton_top5

    @property
    def clone_persona(self) -> dict:
        # Persona Clone basée sur top5 + hd_type

    @property
    def anti_persona(self) -> dict:
        # Persona Anti basée sur bottom5 + hd_authority
```

### Mapping Clifton → Domaine
```python
CLIFTON_DOMAINS = {
    "Analytique": "ST", "Contexte": "ST", "Futuriste": "ST",
    "Idéation": "ST", "Intellectualisme": "ST", "Input": "ST",
    "Stratégique": "ST", "Studieux": "ST",
    "Réalisateur": "EX", "Arrangeur": "EX", "Focus": "EX",
    "Discipline": "EX", "Responsabilité": "EX", "Restaurer": "EX",
    "Activateur": "EX", "Adaptabilité": "EX", "Prudent": "EX",
    "Connexion": "REL", "Développeur": "REL", "Empathie": "REL",
    "Harmonie": "REL", "Inclusion": "REL", "Individualisation": "REL",
    "Positivité": "REL", "Relationnel": "REL",
    "Charisme": "INF", "Communication": "INF", "Compétition": "INF",
    "Conviction": "INF", "Importance": "INF", "Maximisation": "INF",
    # Ajoute les variantes FR/EN
}
```

## ACCEPTANCE TEST 2
```bash
python -c "
from app.models.profile import HumanProfile
p = HumanProfile(
    name='Test User',
    hd_type='Generator',
    hd_authority='Sacral',
    hd_profile='4/1',
    hd_definition='Simple',
    hd_signature='Satisfaction',
    hd_not_self='Frustration',
    clifton_top5=['Idéation','Futuriste','Stratégique','Individualisation','Contexte'],
    clifton_bottom5=['Discipline','Harmonie','Prudent','Équitable'],
    mantra='Test mantra',
    invariants=['Revenue before infra'],
    energy_level=7
)
print('Dominant domain:', p.dominant_domain)     # doit retourner 'ST'
print('Clone persona:', p.clone_persona)          # dict non vide
print('Anti persona:', p.anti_persona)            # dict non vide
"
# PASS si les 3 prints retournent des valeurs cohérentes
```

---

## COMPOSANT 3 — InversionRules Engine

### services/inversion.py

C'est le CŒUR : transforme un HumanProfile en 4 system prompts dynamiques.

#### Règle d'inversion
PAS un miroir exact. Complément de tension sur l'axe le plus extrême.
```
Si dominant ST → Anti challenge avec données concrètes, pas d'idéation
Si dominant EX → Anti challenge avec vision long terme, pas d'action immédiate
Si dominant REL → Anti challenge avec pragmatisme, pas d'harmonie
Si dominant INF → Anti challenge avec humilité, pas de grandeur
```

#### InversionConfig dataclass
```python
@dataclass
class InversionConfig:
    clone_system_prompt: str      # généré depuis top5 + hd_type + dominant_domain
    anti_system_prompt: str       # généré depuis bottom5 + inversion rule + energy_mode
    sp_system_prompt: str         # adapté au hd_authority
    formatter_rules: dict         # output rules selon hd_type
    routing_keywords: dict        # {agent: [keywords]} pour routing léger
    energy_mode: str              # "brake" | "balance" | "accelerate"
    hitl_triggers: list[str]      # phrases qui déclenchent real (HITL)
```

#### Logique energy_mode
```python
energy >= 7  → "brake"       # Anti joue le frein, Clone en pleine production
energy 4-6   → "balance"     # équilibre
energy <= 3  → "accelerate"  # Anti accélère ("MVP maintenant"), Clone en veille
```

#### Logique output formatter selon hd_type
```python
"Generator":             # Présente 2-3 OPTIONS à répondre oui/non
"Manifesting Generator": # Options + action rapide possible en parallèle
"Projector":             # Toujours formulation "Si tu étais invité à..."
"Manifestor":            # Directives d'action directes, pas de questions
"Reflector":             # "Dans 28 jours, est-ce que cette option résonne encore ?"
```

#### Logique SP selon hd_authority
```python
"Sacral":        # Génère questions binaires oui/non · détecte frustration
"Emotional":     # Ajoute délai · "Dors dessus · reviens demain"
"Splenic":       # Encourage décision spontanée · "Qu'est-ce que tu ressens là maintenant ?"
"Ego":           # "Est-ce que tu veux vraiment ça pour toi ?"
"Self-Projected":# "Dis-le à voix haute à quelqu'un de confiance"
"Mental":        # "Présente ça à 3 personnes · note leurs réactions"
"Lunar":         # Frame sur cycle 28 jours · jamais de décision rapide
"None":          # Projector → ne peut décider seul, toujours invitation externe
```

#### Triggers HITL (real)
Mots-clés qui déclenchent une décision RÉELLE de l'utilisateur :
```python
HITL_TRIGGERS = [
    "signer", "signature", "contrat", "irréversible", "abandon",
    "pivot", "fermer", "quitter", "publier", "lancer officiellement",
    "engagement financier", "investir", "embaucher"
]
```

## ACCEPTANCE TEST 3
```bash
python -c "
from app.services.inversion import InversionRulesEngine
from app.models.profile import HumanProfile

engine = InversionRulesEngine()
profile = HumanProfile(
    hd_type='Generator', hd_authority='Sacral', hd_profile='4/1',
    hd_definition='Simple', hd_signature='Satisfaction', hd_not_self='Frustration',
    clifton_top5=['Idéation','Futuriste','Stratégique','Individualisation','Contexte'],
    clifton_bottom5=['Discipline','Harmonie','Prudent','Équitable'],
    mantra='test', invariants=['Revenue before infra'], energy_level=7
)
config = engine.build(profile)
assert len(config.clone_system_prompt) > 100, 'Clone prompt trop court'
assert len(config.anti_system_prompt) > 100, 'Anti prompt trop court'
assert config.energy_mode == 'brake', f'Energy mode incorrect: {config.energy_mode}'
assert 'Generator' in config.formatter_rules, 'Formatter rule manquante'
print('InversionRules OK')
"
```

---

## COMPOSANT 4 — Memory Cascade L1→L4

### services/memory.py

```python
class MemoryService:
    """
    Cascade mémoire — lecture en ordre L1→L2→L3→L4
    Écriture en cascade inverse L4→L3→L2→L1
    Chaque profile_id est une bulle ISOLÉE
    """

    # L1 — Redis <1ms
    # Stocke : profil actif, état session, energy check-in du jour
    # TTL : profil 15min, session 24h, energy 12h

    # L2 — Mem0 (conversationnel moyen terme)
    # Stocke : historique conversations, patterns de décision extraits
    # Interface : mem0_client.add(messages, user_id=str(profile_id))
    #             mem0_client.search(query, user_id=str(profile_id))
    # Si MEM0_API_KEY absent : utilise mem0 local avec postgres backend

    # L3 — Graphiti (knowledge graph temporel)
    # Stocke : relations causales, entités nommées (leads, projets, décisions)
    # Connexion : Neo4j via GRAPHITI_NEO4J_URI
    # Si GRAPHITI_NEO4J_URI absent : MOCK → log "L3 skipped, no Neo4j" dans MOCKS.md

    # L4 — pgvector (RAG sémantique)
    # Stocke : embeddings des invariants, mantras, patterns de frustration
    # Modèle embedding : text-embedding-3-small via LiteLLM
    # Table : memory_embeddings (profile_id, content, embedding vector(1536), metadata)

    async def get_context(self, profile_id: UUID, query: str) -> str:
        # Tente L1 → L2 → L3 → L4 en cascade
        # Retourne le contexte pertinent agrégé

    async def store_interaction(self, profile_id: UUID, interaction: dict):
        # Écrit dans L2 + L4 async
        # L1 mis à jour si session active

    async def get_decision_history(self, profile_id: UUID) -> list[dict]:
        # Historique des décisions sacrales (HITL confirmées)

    async def detect_not_self(self, profile_id: UUID, message: str) -> bool:
        # Détecte si le message contient le signal not_self du profil
        # Ex: pour Generator → détecte frustration
```

## ACCEPTANCE TEST 4
```bash
python -c "
import asyncio
from uuid import uuid4
from app.services.memory import MemoryService

async def test():
    svc = MemoryService()
    pid = uuid4()
    await svc.store_interaction(pid, {
        'role': 'user',
        'content': 'Je veux lancer un nouveau projet',
        'agent': 'sp'
    })
    ctx = await svc.get_context(pid, 'nouveau projet')
    print('Memory store+retrieve OK, context len:', len(ctx))
    not_self = await svc.detect_not_self(pid, 'Je suis frustré par ce blocage')
    print('Not-self detection:', not_self)  # True si profil Generator chargé

asyncio.run(test())
"
```

---

## COMPOSANT 5 — LangGraph Graph

### agents/state.py
```python
from typing import TypedDict, Annotated, Literal
from langgraph.graph.message import add_messages
from uuid import UUID

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    profile: dict                    # HumanProfile.model_dump()
    inversion_config: dict           # InversionConfig sérialisé
    energy_level: int                # 1-10 au moment de la requête
    task_type: Literal[
        "production",                # → Clone
        "challenge",                 # → Anti
        "sacral_stimulus",           # → SP
        "flow",                      # → SP
        "irreversible_decision"      # → HITL real
    ]
    active_agent: str                # pour le frontend
    requires_hitl: bool
    hitl_token: str | None           # UUID si HITL requis
    not_self_detected: bool          # frustration ou not-self détecté
    session_id: str
    context: str                     # contexte mémoire injecté
```

### agents/graph.py — Topology complète

```python
# NODES :
# 1. filter_sp    — entry point UNIQUE, classify + sacral stimulus
# 2. supervisor   — route vers clone | anti | sp | real
# 3. clone        — production ST-dominant, 3 options toujours
# 4. anti         — challenge blind spots
# 5. sp_response  — réponse flux direct (pas de routing clone/anti)
# 6. formatter    — post-processing HD-type obligatoire sur tous outputs
# 7. hitl         — interrupt() pour décisions irréversibles

# EDGES conditionnels :
# filter_sp → supervisor : toujours
# supervisor → clone      : task_type == "production" and not requires_hitl
# supervisor → anti       : task_type == "challenge"
# supervisor → sp_response: task_type in ["sacral_stimulus", "flow"]
# supervisor → hitl       : requires_hitl == True
# clone → formatter
# anti → formatter
# sp_response → formatter
# formatter → END
# hitl → [interrupt] → formatter → END

# LLM ROUTING via LiteLLM :
# filter_sp + formatter + supervisor : "koyeb/gemini-flash-2.0"  (evergreen, $0)
# clone + anti                       : "together/deepseek-v3"     (pro, $0.001/1K)
# sp_response                        : "together/deepseek-v3"     (pro)
# hitl confirmation format           : "anthropic/claude-sonnet-4" (max, $0.01/1K)
# Fallback si provider down          : "anthropic/claude-haiku-4-5" toujours

# LANGFUSE callbacks sur tous les nodes
# Trace : session_id, profile_id, active_agent, task_type
```

#### filter_sp.py — logique détaillée
```python
async def filter_sp_node(state: AgentState) -> AgentState:
    """
    VRAI_SP — entry point unique.
    
    Logique :
    1. Détecte not_self (frustration pour Generator, etc.)
       → Si détecté : ajoute WARNING, force task_type="sacral_stimulus"
    2. Détecte initiation sans sacral
       → Patterns : "je veux lancer", "j'ai décidé de", "je vais commencer"
       → Pour Generator/MG : TOUJOURS questionner l'origine (sacral ou mental ?)
    3. Détecte HITL triggers
       → Si trouvé : requires_hitl=True, génère hitl_token
    4. Enrichit le contexte depuis MemoryService
    5. Classifie task_type (heuristique keywords + LLM léger si incertain)
    6. Génère stimulus adapté au hd_authority si task_type=sacral_stimulus
    
    RÈGLE ABSOLUE : Ne prescrit jamais. Génère des questions ou options.
    Pour Generator : toujours des options binaires (oui/non)
    """
```

## ACCEPTANCE TEST 5
```bash
python -c "
import asyncio
from app.agents.graph import build_graph
from app.agents.state import AgentState

async def test():
    graph = build_graph()
    
    # Test 1: routing production → clone
    state1 = {
        'messages': [{'role': 'user', 'content': 'Crée-moi 3 options de pitch pour Cindy'}],
        'profile': {'hd_type': 'Generator', 'hd_authority': 'Sacral', 
                    'clifton_top5': ['Idéation','Futuriste','Stratégique','Individualisation','Contexte'],
                    'clifton_bottom5': ['Discipline','Harmonie','Prudent','Équitable'],
                    'hd_not_self': 'Frustration', 'invariants': []},
        'energy_level': 7, 'session_id': 'test-1'
    }
    result1 = await graph.ainvoke(state1)
    assert result1['active_agent'] == 'clone', f'Expected clone, got {result1[\"active_agent\"]}'
    print('Test 1 OK — routing clone')
    
    # Test 2: routing challenge → anti
    state2 = dict(state1)
    state2['messages'] = [{'role': 'user', 'content': 'Je vais lancer un nouveau projet aujourd hui'}]
    state2['session_id'] = 'test-2'
    result2 = await graph.ainvoke(state2)
    assert result2['active_agent'] in ['anti', 'sp'], f'Expected anti or sp, got {result2[\"active_agent\"]}'
    print('Test 2 OK — routing anti/sp pour initiation')
    
    # Test 3: not-self detection
    state3 = dict(state1)
    state3['messages'] = [{'role': 'user', 'content': 'Je suis vraiment frustré par cette situation'}]
    state3['session_id'] = 'test-3'
    result3 = await graph.ainvoke(state3)
    assert result3['not_self_detected'] == True, 'Not-self non détecté'
    print('Test 3 OK — not-self détecté')
    
    print('Graph OK — tous les tests passent')

asyncio.run(test())
"
```

---

## COMPOSANT 6 — API FastAPI

### api/chat.py

```
POST /api/chat
Body: {
    "session_id": "uuid",
    "profile_id": "uuid",
    "message": "string",
    "energy_level": int | null    # override profil si fourni
}
Response: {
    "message": "string",
    "active_agent": "clone|anti|sp|real",
    "task_type": "string",
    "requires_hitl": false,
    "hitl_token": null | "uuid",
    "not_self_detected": false,
    "metadata": {
        "routing_reason": "string",
        "energy_mode": "brake|balance|accelerate",
        "context_sources": ["l1","l2","l4"]
    }
}

POST /api/chat/hitl/{hitl_token}
Body: { "decision": "yes" | "no" }
Response: { "message": "string", "active_agent": "real" }

WebSocket ws://host/api/chat/stream/{session_id}
→ Stream des tokens de réponse
→ Envoie d'abord : {"type": "routing", "agent": "clone", "task_type": "production"}
→ Puis stream : {"type": "token", "content": "..."}
→ Fin : {"type": "done", "metadata": {...}}

PUT /api/profile/{profile_id}/energy
Body: { "energy_level": int }  # check-in rapide

POST /api/profile
GET /api/profile/{profile_id}
PUT /api/profile/{profile_id}
DELETE /api/profile/{profile_id}
```

### main.py
```python
# FastAPI app avec :
# - CORS pour localhost:3000 + vercel.app domains + domaine Coolify configuré
# - Lifespan pour init DB + Redis pool au démarrage
# - /health endpoint (retourne DB status + Redis status)
# - /docs désactivé en production
# Middleware : request logging avec session_id + profile_id
```

## ACCEPTANCE TEST 6
```bash
# Lance le serveur en background
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
sleep 3

# Health check
curl -sf http://localhost:8000/health | python -c "
import sys, json
d = json.load(sys.stdin)
assert d['status'] == 'ok', f'Health failed: {d}'
print('Health OK')
"

# Crée un profil
curl -sf -X POST http://localhost:8000/api/profile \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "Test User",
    "hd_type": "Generator",
    "hd_authority": "Sacral",
    "hd_profile": "4/1",
    "hd_definition": "Simple",
    "hd_signature": "Satisfaction",
    "hd_not_self": "Frustration",
    "clifton_top5": ["Idéation","Futuriste","Stratégique","Individualisation","Contexte"],
    "clifton_bottom5": ["Discipline","Harmonie","Prudent","Équitable"],
    "mantra": "Test",
    "invariants": ["Revenue before infra"],
    "energy_level": 7
  }' | python -c "
import sys, json
d = json.load(sys.stdin)
assert 'id' in d, 'Profile ID manquant'
print('Profile created OK:', d['id'])
"

kill %1  # stop le serveur background
```

---

## COMPOSANT 7 — Background: Pattern Detector

### services/pattern_detector.py

```python
# Tâche background (asyncio ou arq) qui tourne toutes les heures
# Pour chaque profil actif (session dans les 24h) :
#
# 1. Analyse les interactions L2 (Mem0)
# 2. Détecte :
#    - Fréquence not_self_detected (si > 3/jour → alert dans prochain SP message)
#    - Patterns d'initiation sans sacral récurrents
#    - Topics récurrents dans les requests clone (= vrais OKR du moment)
#    - Décisions HITL yes/no ratio (calibrage du threshold)
#
# 3. Met à jour L4 (pgvector) avec les patterns détectés
# 4. Expose via GET /api/profile/{id}/patterns
#
# Pas de LLM dans ce composant — pure analyse statistique
# Si volume insuffisant (<10 interactions) : skip silencieusement
```

---

## COMPOSANT 8 — Docker + Coolify

### docker-compose.yml (dev local)
```yaml
version: "3.9"
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    env_file: .env
    depends_on:
      postgres: {condition: service_healthy}
      redis: {condition: service_healthy}
    volumes:
      - ./backend:/app  # hot reload dev
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: cockpit_sparring
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes: [postgres_data:/var/lib/postgresql/data]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 5s
      retries: 5

  redis:
    image: redis:7.4-alpine
    command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
    volumes: [redis_data:/data]
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s

  langfuse:
    image: langfuse/langfuse:latest
    ports: ["3010:3000"]
    env_file: .env
    depends_on:
      postgres: {condition: service_healthy}
    environment:
      DATABASE_URL: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres/langfuse
      NEXTAUTH_URL: http://localhost:3010
      NEXTAUTH_SECRET: ${SECRET_KEY}
      SALT: ${LANGFUSE_SALT}

volumes:
  postgres_data:
  redis_data:
```

### docker-compose.coolify.yml (prod)
Idem mais :
- Supprime les volumes dev (bind mounts)
- Ajoute les labels Traefik pour Coolify
- Commande uvicorn sans --reload, avec workers : `--workers 2`
- Langfuse sur sous-domaine `trace.${DOMAIN}`
- Backend sur `api.${DOMAIN}`
- Healthchecks plus strict (retries: 10)

Labels Traefik backend :
```yaml
traefik.enable: "true"
traefik.http.routers.cockpit-api.rule: "Host(`api.${DOMAIN}`)"
traefik.http.routers.cockpit-api.tls.certresolver: "letsencrypt"
traefik.http.services.cockpit-api.loadbalancer.server.port: "8000"
```

## ACCEPTANCE TEST 8
```bash
docker compose up -d
sleep 10
curl -sf http://localhost:8000/health
echo "Docker stack OK"
docker compose logs backend | grep -v ERROR | tail -5
docker compose down
```

---

## COMPOSANT 9 — Frontend Next.js

### Stack frontend
```
Next.js 15 (app router)
Tailwind CSS 4
shadcn/ui (components)
Zustand (state management)
React Query (server state)
Framer Motion (transitions agents)
```

### /onboarding/page.tsx
Formulaire profil en 4 étapes (wizard) :
- Étape 1 : Human Design (sélecteurs visuels avec explication de chaque type/autorité)
- Étape 2 : Clifton 34 (rank drag-and-drop, ou import CSV si disponible)
- Étape 3 : Mantra + invariants (textarea guidé)
- Étape 4 : Energy check-in initial + confirmation

### /cockpit/page.tsx
Layout :
```
┌─────────────────────────────────────────────────────┐
│  [SP●] [CLONE●] [ANTI○] [REAL○]    énergie: 7/10  │  ← Header agents + energy
├──────────┬──────────────────────────────────────────┤
│ PROFIL   │                                          │
│          │        ZONE CHAT                         │
│ HD: Gen  │  [VRAI SP] Tu as mentionné Cindy...     │
│ 4/1      │                                          │
│ Sacral   │  [USER] Oui. Je confirme le RDV.        │
│          │                                          │
│ Top 5:   │  [CLONE IA] 3 options de pitch:         │
│ Idéation │    A) Focus douleur TDAH               │
│ Futuriste│    B) Angle outil-compagnon             │
│ Stratég. │    C) ROI temps libéré                 │
│          │                                          │
│ Énergie  │  > _____________________________ [→]    │
│ [=====○] │                                          │
└──────────┴──────────────────────────────────────────┘
```

Couleurs agents (CSS variables) :
```css
--agent-sp:    #1D9E75  /* teal */
--agent-clone: #7F77DD  /* purple */
--agent-anti:  #D85A30  /* coral */
--agent-real:  #BA7517  /* amber */
```

Le badge agent actif pulse (framer-motion) quand il répond.
Si requires_hitl=true → modal centré : "Décision sacrée — Oui ou Non ?"
Si not_self_detected=true → banner discret en haut : "Signal [not_self] détecté"

### vercel.json
```json
{
  "rewrites": [
    {"source": "/api/:path*", "destination": "https://api.${DOMAIN}/:path*"}
  ],
  "env": {
    "NEXT_PUBLIC_API_URL": "https://api.${DOMAIN}"
  }
}
```

## ACCEPTANCE TEST 9
```bash
cd frontend
npm run build
echo "Next.js build OK si exit 0"
# Vérifie les routes critiques
npx next info | grep "Next.js"
```

---

## COMPOSANT 10 — .env.example + DONE.md

### .env.example
```bash
# Base
ENVIRONMENT=development
SECRET_KEY=change-me-in-production
DOMAIN=cockpit.yourdomain.com

# Database
POSTGRES_USER=cockpit
POSTGRES_PASSWORD=change-me
DATABASE_URL=postgresql+asyncpg://cockpit:change-me@postgres/cockpit_sparring

# Redis
REDIS_URL=redis://redis:6379

# LLM
ANTHROPIC_API_KEY=sk-ant-...
LITELLM_MASTER_KEY=sk-...  # optionnel

# Langfuse
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=http://langfuse:3000
LANGFUSE_SALT=change-me

# Mem0
MEM0_API_KEY=  # laisser vide pour mode local

# Graphiti / Neo4j (optionnel — L3 skippé si absent)
GRAPHITI_NEO4J_URI=
GRAPHITI_NEO4J_USER=
GRAPHITI_NEO4J_PASSWORD=

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## ORDRE D'EXÉCUTION FINAL

```
1.  Crée la structure de répertoires complète
2.  Génère .env.example et requirements.txt
3.  Implémente config.py + database.py
4.  RUN ACCEPTANCE TEST 1
5.  Implémente models/profile.py + migration Alembic
6.  RUN ACCEPTANCE TEST 2
7.  Implémente services/inversion.py
8.  RUN ACCEPTANCE TEST 3
9.  Implémente services/memory.py (L1+L2+L4 ; L3 mock si Neo4j absent)
10. RUN ACCEPTANCE TEST 4
11. Implémente agents/state.py + agents/nodes/* + agents/graph.py
12. RUN ACCEPTANCE TEST 5
13. Implémente api/* + main.py
14. RUN ACCEPTANCE TEST 6
15. Implémente services/pattern_detector.py (background)
16. Génère docker-compose.yml + docker-compose.coolify.yml
17. RUN ACCEPTANCE TEST 8
18. Génère frontend Next.js complet
19. RUN ACCEPTANCE TEST 9
20. Génère DONE.md avec :
    - Liste composants buildés avec statut ✅/⚠️
    - Liste des mocks actifs (depuis MOCKS.md)
    - Commande de démarrage local : `docker compose up -d`
    - Commande de déploiement Coolify : instructions push + env vars
    - URL health check post-deploy
```

---

*Blueprint généré par OREILLY · 2026-05-25*
*Pattern : Supervisor + Specialist Nodes — O'Reilly Ch.5*
*Memory : cascade L1→L4 — O'Reilly Ch.6*
*State management : TypedDict + LangGraph — O'Reilly Ch.8*


---

## COMPOSANT 11 — MCP Gateway (Nango + Obot)

### Rôle dans l'architecture
Nango = credential store (tokens OAuth 700+ SaaS)
Obot = MCP gateway + tool catalog + RBAC
LangGraph nodes appellent Obot. Obot appelle Nango pour les tokens.
LangGraph reste le chef d'orchestre. Obot ne voit que des résultats MCP.

### docker-compose additions
```yaml
nango:
  image: nangohq/nango:latest
  ports: ["3003:3003"]
  environment:
    SERVER_URL: http://nango:3003
    SECRET_KEY: ${NANGO_SECRET_KEY}
    POSTGRES_URL: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres/nango
  depends_on:
    postgres: {condition: service_healthy}

obot:
  image: ghcr.io/obot-platform/obot:latest
  ports: ["8080:8080"]
  environment:
    OBOT_SERVER_URL: http://obot:8080
    OBOT_POSTGRES_DSN: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres/obot
  depends_on:
    postgres: {condition: service_healthy}
    nango: {condition: service_started}

sim:
  image: ghcr.io/simstudio/sim:latest
  ports: ["3001:3000"]
  environment:
    DATABASE_URL: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres/sim
    NEXTAUTH_SECRET: ${SECRET_KEY}
  depends_on:
    postgres: {condition: service_healthy}
```

### MCPClient dans les agents LangGraph
```python
# services/mcp_client.py
class MCPClient:
    """
    Adapter entre LangGraph nodes et Obot MCP gateway.
    Les nodes ne savent pas que Nango existe — ils appellent MCPClient.
    MCPClient résout les tokens via Nango de façon transparente.
    """
    def __init__(self, obot_url: str, nango_url: str, nango_secret: str):
        self.obot = obot_url
        self.nango = nango_url
        self.nango_secret = nango_secret

    async def call(
        self,
        tool_name: str,
        profile_id: str,
        params: dict,
        dry_run: bool = False
    ) -> dict:
        # 1. Récupère token depuis Nango
        token = await self._get_token(profile_id, tool_name)
        # 2. Si dry_run → retourne diff sans exécuter
        if dry_run:
            return await self._dry_run(tool_name, params, token)
        # 3. Execute via Obot MCP
        return await self._execute(tool_name, params, token)

    async def discover_tools(self, profile_id: str) -> list[dict]:
        # Retourne tous les tools disponibles pour ce profil
        # depuis le catalog Obot filtré par RBAC

    async def _dry_run(self, tool_name: str, params: dict, token: str) -> dict:
        # Simule l'exécution, retourne diff lisible
        # Format: {action, target, content_before, content_after, risk_level}
```

### Permissions par agent
```python
AGENT_TOOL_PERMISSIONS = {
    "clone": {
        "access": "read_write",
        "tools": ["notion", "github", "calendar", "search", "file", "email_draft"]
    },
    "anti": {
        "access": "read_only",
        "tools": ["notion_read", "calendar_read", "okr_read"]
    },
    "sp": {
        "access": "notify_only",
        "tools": ["notification", "message_draft"]
    },
    "real": {
        "access": "none",
        "tools": []
    }
}
```

## ACCEPTANCE TEST 11
```bash
# Nango health
curl -sf http://localhost:3003/health | python -c "
import sys, json; d=json.load(sys.stdin)
assert d.get('status') == 'ok'; print('Nango OK')"

# Obot health
curl -sf http://localhost:8080/api/healthz | python -c "
import sys, json; d=json.load(sys.stdin)
assert d.get('status') == 'ok'; print('Obot OK')"

# MCPClient discover (avec mock token si Nango pas encore configuré)
python -c "
import asyncio
from app.services.mcp_client import MCPClient
from uuid import uuid4

async def test():
    client = MCPClient(
        obot_url='http://localhost:8080',
        nango_url='http://localhost:3003',
        nango_secret='test'
    )
    tools = await client.discover_tools(str(uuid4()))
    print(f'Tools discovered: {len(tools)}')
    print('MCPClient OK')

asyncio.run(test())"
```

---

## COMPOSANT 12 — ADA (Agent Discovery API) + Sub-agent Spawner

### Principe
ADA est le pont entre Couche A (headless backends) et Couche B (Cockpit UI).
Le Cockpit ne connaît pas LangGraph, Obot, Sim, n8n.
Il appelle ADA. ADA sait où aller chercher.
L'UI se génère dynamiquement depuis ce que ADA découvre.

### api/ada.py — endpoints complets

```
# DISCOVERY
GET  /ada/agents                    → liste tous les agents actifs
GET  /ada/agents/{id}               → détail agent (persona, tools, RACI, BPMN)
GET  /ada/agents/{id}/skills        → tools accessibles + permissions
GET  /ada/agents/{id}/memory        → état mémoire courant
GET  /ada/tools                     → catalog tools depuis Obot
GET  /ada/workflows                 → workflows Sim.ai disponibles
GET  /ada/surface/snapshot          → état UI courant sérialisé (headless test)

# SCRUDX AGENTS
POST   /ada/agents/spawn            → crée un sous-agent depuis template
POST   /ada/agents/{id}/task        → déclenche une tâche
PUT    /ada/agents/{id}/config      → met à jour persona/tools/RACI
DELETE /ada/agents/{id}             → supprime un agent

# OKR
GET  /ada/okr                       → arbre OKR complet
POST /ada/okr/spawn                 → crée sous-OKR depuis OKR parent
GET  /ada/okr/alignment/{agent_id}  → score alignement agent ↔ OKR
POST /ada/okr/align                 → force alignement d'un agent sur OKR

# DRY-RUN
POST /ada/agents/{id}/dryrun        → simule tâche, retourne diff lisible
GET  /ada/dryrun/{token}            → récupère résultat dry-run
POST /ada/dryrun/{token}/approve    → valide → execute
POST /ada/dryrun/{token}/reject     → annule

# EXÉCUTION MODES
POST /ada/agents/{id}/task
Body: {
  "task": "string",
  "mode": "yolo" | "mitl" | "hitl",
  "dry_run": false,
  "okr_check": true
}
```

### Sub-agent Spawner
```python
# services/spawner.py

@dataclass
class SubAgentTemplate:
    role: str              # "growth_hacker", "content_writer", "data_analyst"
    profession: str        # métier humain de référence
    ddd_context: str       # bounded context DDD
    bpmn_xml: str          # flow BPMN valide
    raci: dict             # {responsible, accountable, consulted, informed}
    tools: list[str]       # tool names depuis catalog Obot
    okr_parent_id: str     # OKR dont ce sous-agent est responsable
    execution_mode: str    # "yolo" | "mitl" | "hitl"
    model_tier: str        # "evergreen" | "pro" | "max"

class SubAgentSpawner:
    async def spawn(
        self,
        template: SubAgentTemplate,
        profile: HumanProfile,
        inversion_config: InversionConfig
    ) -> SpawnedAgent:
        """
        1. Génère le system prompt depuis template + profil HD + OKR parent
        2. Configure les tools depuis MCPClient
        3. Enregistre dans le registry ADA
        4. Crée le node LangGraph correspondant dynamiquement
        5. Retourne l'agent prêt à recevoir des tâches
        """

    async def spawn_agency_from_okr(
        self,
        root_okr: OKR,
        profile: HumanProfile
    ) -> list[SpawnedAgent]:
        """
        Depuis un OKR racine, génère récursivement l'équipe d'agents.
        Chaque sous-OKR → 1 agent spécialisé.
        L'alignement HD du profil guide le choix des personas.
        """
```

### OKR Tree + Alignment
```python
# models/okr.py
class OKR(Base):
    id: UUID
    profile_id: UUID
    parent_id: UUID | None       # None = OKR racine entreprise
    title: str
    why: str                     # raison d'être (connecté au mantra)
    key_results: list[str]
    owner_agent_id: UUID | None  # sous-agent responsable
    alignment_score: float       # 0-1, calculé vs profil HD + essence
    level: int                   # 0=company, 1=product, 2=sprint, 3=task
    status: str                  # active | completed | paused

# L'alignment_score est recalculé à chaque modification
# via embedding similarity entre le contenu OKR et le profil identity
```

## ACCEPTANCE TEST 12
```bash
python -c "
import asyncio
from app.api.ada import ada_router
from app.services.spawner import SubAgentSpawner, SubAgentTemplate

async def test():
    spawner = SubAgentSpawner()

    # Spawn un sous-agent growth
    template = SubAgentTemplate(
        role='growth_hacker',
        profession='Growth Marketer',
        ddd_context='acquisition',
        bpmn_xml='<definitions>...</definitions>',
        raci={'responsible': 'clone', 'accountable': 'real', 'consulted': 'anti', 'informed': 'sp'},
        tools=['search', 'notion', 'calendar'],
        okr_parent_id='okr-root-id',
        execution_mode='mitl',
        model_tier='pro'
    )

    agent = await spawner.spawn(template, mock_profile, mock_inversion)
    assert agent.id is not None
    assert agent.status == 'ready'
    print(f'Sub-agent spawned OK: {agent.role} / {agent.id}')

    # Test discovery
    from httpx import AsyncClient
    async with AsyncClient(app=app, base_url='http://test') as client:
        r = await client.get('/ada/agents')
        assert r.status_code == 200
        agents = r.json()
        assert len(agents) >= 1
        print(f'ADA discovery OK: {len(agents)} agents')

asyncio.run(test())"
```

---

## COMPOSANT 13 — Conformance Agent (E2E headless validator)

### Principe
Tout doit être agentable. Ce composant EN EST la preuve.
Un agent IA peut naviguer l'intégralité du système sans UI,
vérifier que tout est conforme, et corriger ce qui ne l'est pas.

Conformance à trois niveaux :
- SURFACE   = chaque action UI a un équivalent API (zero UI-only)
- STRUCTURE = chaque agent a DDD + BPMN + RACI + OKR valides
- SUBSTANCE = chaque contenu est aligné avec le profil HD + essence + OKR

### agents/nodes/conformance.py
```python
@dataclass
class ConformanceReport:
    surface: float           # 0-1, % actions UI couvertes par API
    structure: float         # 0-1, % agents avec schema complet
    substance: float         # 0-1, % contenu aligné OKR + HD
    issues: list[dict]       # [{level, component, issue, fixable, fix_action}]
    overall: float           # moyenne pondérée
    timestamp: datetime

class ConformanceAgent:
    """
    Agent autonome qui tourne en background (toutes les 6h)
    et sur demand via POST /ada/conformance/check

    Surface check :
    - Crawl tous les endpoints ADA
    - Vérifie que chaque action UI documentée a un équivalent REST
    - Teste les endpoints avec Playwright headless en parallèle
    - Score = nb endpoints API / nb actions UI référencées

    Structure check :
    - Récupère tous les agents depuis /ada/agents
    - Vérifie pour chacun : BPMN valide, RACI complet, OKR attaché
    - Vérifie que les tools assignés existent dans Obot catalog
    - Vérifie cohérence execution_mode vs RACI accountable

    Substance check :
    - Pour chaque agent : embedding du system_prompt
    - Calcule similarité avec embedding du profil (mantra + invariants + OKR)
    - Seuil : > 0.75 = aligné, 0.5-0.75 = dérive, < 0.5 = désaligné
    - Pour chaque OKR : vérifie que le why est cohérent avec le mantra

    Auto-fix (si fixable=true) :
    - Structure : complète les champs manquants via LLM + profil
    - Substance : régénère le system_prompt via InversionRules
    - Surface : log les gaps, génère ticket pour dev
    """

    async def run_full_check(self, profile_id: UUID) -> ConformanceReport:
        surface = await self._check_surface()
        structure = await self._check_structure(profile_id)
        substance = await self._check_substance(profile_id)
        return ConformanceReport(
            surface=surface.score,
            structure=structure.score,
            substance=substance.score,
            issues=surface.issues + structure.issues + substance.issues,
            overall=(surface.score * 0.2 + structure.score * 0.4 + substance.score * 0.4),
            timestamp=datetime.utcnow()
        )

    async def fix_issues(self, report: ConformanceReport, profile: HumanProfile):
        for issue in report.issues:
            if issue["fixable"]:
                await self._apply_fix(issue, profile)
```

### API endpoints conformance
```
GET  /ada/conformance                    → dernier rapport
POST /ada/conformance/check              → déclenche check complet
POST /ada/conformance/fix                → corrige les issues fixables
GET  /ada/conformance/stream             → WebSocket temps réel
GET  /ada/conformance/{component}        → rapport par composant
GET  /ada/surface/snapshot               → état surface sérialisé
POST /ada/surface/replay/{action_id}     → rejoue une action headless
```

### MITL Alignment Validator
```python
# Utilisé par les agents en mode MITL avant d'exécuter
class MITLValidator:
    """
    Vision model qui valide qu'une action est alignée
    avant exécution automatique (sans HITL).

    Input:
    - dry_run_diff: ce que l'agent s'apprête à faire
    - agent_okr: OKR dont cet agent est responsable
    - profile: HD + Clifton + mantra + invariants

    Output:
    - approved: bool
    - confidence: float (0-1)
    - reason: str
    - risks: list[str]

    Modèle utilisé: claude-sonnet-4 (max tier)
    — décision de validation = tier max toujours
    — jamais de modèle evergreen pour valider des actions
    """

    async def validate(
        self,
        dry_run_diff: dict,
        agent_okr: OKR,
        profile: HumanProfile
    ) -> ValidationResult:
        prompt = self._build_validation_prompt(dry_run_diff, agent_okr, profile)
        result = await litellm.acompletion(
            model="anthropic/claude-sonnet-4",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return ValidationResult(**json.loads(result.choices[0].message.content))

    def _build_validation_prompt(self, diff, okr, profile) -> str:
        return f"""
Tu es le validateur d'alignement du Cockpit Stern.

PROFIL UTILISATEUR:
- HD Type: {profile.hd_type} | Autorité: {profile.hd_authority}
- Top 5 Clifton: {', '.join(profile.clifton_top5)}
- Mantra: {profile.mantra}
- Invariants: {json.dumps(profile.invariants)}
- Signature (état aligné): {profile.hd_signature}
- Not-self (signal arrêt): {profile.hd_not_self}

OKR RESPONSABLE:
- Titre: {okr.title}
- Why: {okr.why}
- Key Results: {json.dumps(okr.key_results)}

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
}}
"""
```

## ACCEPTANCE TEST 13
```bash
python -c "
import asyncio
from app.agents.nodes.conformance import ConformanceAgent
from uuid import uuid4

async def test():
    agent = ConformanceAgent()
    report = await agent.run_full_check(uuid4())

    print(f'Surface:   {report.surface:.0%}')
    print(f'Structure: {report.structure:.0%}')
    print(f'Substance: {report.substance:.0%}')
    print(f'Overall:   {report.overall:.0%}')
    print(f'Issues:    {len(report.issues)}')

    assert report.overall >= 0.0, 'Score invalide'
    print('Conformance Agent OK')

asyncio.run(test())"
```

---

## ORDRE D'EXÉCUTION FINAL — MISE À JOUR

```
1-9.   [inchangés — composants 1 à 9]
10.    Composant 10 : .env.example + Alembic migrations finales
11.    Composant 11 : Nango + Obot + Sim dans docker-compose
       RUN ACCEPTANCE TEST 11
12.    Composant 12 : ADA API + SubAgentSpawner + OKR tree
       RUN ACCEPTANCE TEST 12
13.    Composant 13 : ConformanceAgent + MITLValidator
       RUN ACCEPTANCE TEST 13
14.    Intégration finale : ConformanceAgent tourne sur stack complète
       POST /ada/conformance/check → rapport > 80% overall = DONE
15.    Génère DONE.md avec conformance report intégré
```

---

## ARCHITECTURE FINALE COMPLÈTE

```
╔══════════════════════════════════════════════════════════════════╗
║              COUCHE B — COCKPIT STERN (custom build)            ║
║                                                                  ║
║  Profile Kernel ──► InversionRules ──► 4 Agents configurés      ║
║       │                                      │                   ║
║  OKR Tree ──► SubAgentSpawner ──► N agents (DDD+BPMN+RACI)      ║
║       │                                      │                   ║
║  ConformanceAgent ◄── MITLValidator ◄── dry_run diffs           ║
║                                                                  ║
║  UI Shell (custom brand, discovery-driven depuis ADA)            ║
╠══════════════════════════════════════════════════════════════════╣
║              ADA — Agent Discovery API (pont)                    ║
║  SCRUDX /agents · /tools · /workflows · /okr · /conformance      ║
╠══════════════════════════════════════════════════════════════════╣
║              COUCHE A — HEADLESS BACKENDS (composable)           ║
║                                                                  ║
║  LangGraph ──── Obot ──── Nango ──── Sim.ai ──── n8n            ║
║  (graphs)    (MCP gw)  (tokens)   (viz edit)  (triggers)        ║
╚══════════════════════════════════════════════════════════════════╝

RÈGLE ABSOLUE : Tout ce que l'UI peut faire, l'API peut faire.
               Tout ce que l'API peut faire, un agent peut faire.
               Zero fonctionnalité UI-only. Zero action non-agentable.
```

*Composants 11-13 ajoutés — 2026-05-25*


---

## COMPOSANT 14 — Design API + Versioning + Hyperpersonnalisation

### Rôle
Le Design API est le registre central de toutes les versions d'interface.
Il expose les tokens, composants, préférences utilisateur et RBAC.
Il est la colle entre Penpot (source visuelle) et les composants React (rendu).

### Modèles Postgres

```sql
-- Versions immutables (content-addressed)
CREATE TABLE design_versions (
  id          VARCHAR(12) PRIMARY KEY,  -- hash SHA256[:12]
  tokens      JSONB NOT NULL,
  description TEXT,
  created_by  VARCHAR(255),
  created_at  TIMESTAMPTZ DEFAULT NOW()
);
-- Une fois insérée, jamais modifiée.

-- Pointeur HEAD (une seule ligne)
CREATE TABLE design_head (
  singleton   BOOLEAN PRIMARY KEY DEFAULT TRUE CHECK(singleton),
  version_id  VARCHAR(12) REFERENCES design_versions(id),
  updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Préférences utilisateur (delta non-destructif)
CREATE TABLE user_preferences (
  user_id     UUID NOT NULL,
  base_version VARCHAR(12) REFERENCES design_versions(id),
  preferences JSONB NOT NULL DEFAULT '{}',
  updated_at  TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (user_id)
);

-- Config RBAC par rôle
CREATE TABLE role_layout_config (
  role        VARCHAR(100) PRIMARY KEY,
  config      JSONB NOT NULL DEFAULT '{}',
  updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Audit log des rollbacks
CREATE TABLE design_version_history (
  id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  version_id  VARCHAR(12) REFERENCES design_versions(id),
  action      VARCHAR(50),  -- 'publish' | 'rollback' | 'preview'
  actor       VARCHAR(255),
  created_at  TIMESTAMPTZ DEFAULT NOW()
);
```

### services/design_api.py
```python
class DesignVersionService:
    async def get_active_tokens(self) -> dict:
        # Redis cache first → Postgres fallback
        cached = await redis.get("design:tokens:active")
        if cached: return json.loads(cached)
        head = await db.fetchone("SELECT version_id FROM design_head")
        version = await db.fetchone(
            "SELECT tokens FROM design_versions WHERE id=$1", head.version_id
        )
        await redis.setex("design:tokens:active", 300, json.dumps(version.tokens))
        return version.tokens

    async def publish_version(self, tokens: dict, description: str, actor: str) -> str:
        version_id = sha256(json.dumps(tokens, sort_keys=True))[:12]
        await db.execute(
            "INSERT INTO design_versions(id,tokens,description,created_by) VALUES($1,$2,$3,$4) ON CONFLICT DO NOTHING",
            version_id, tokens, description, actor
        )
        await db.execute(
            "INSERT INTO design_head(singleton,version_id,updated_at) VALUES(TRUE,$1,NOW()) ON CONFLICT(singleton) DO UPDATE SET version_id=$1,updated_at=NOW()",
            version_id
        )
        await redis.delete("design:tokens:active")  # invalide cache
        await self._log_action(version_id, 'publish', actor)
        return version_id

    async def rollback(self, version_id: str, actor: str):
        # Vérifie que la version existe
        exists = await db.fetchone("SELECT id FROM design_versions WHERE id=$1", version_id)
        if not exists: raise ValueError(f"Version {version_id} not found")
        await db.execute(
            "UPDATE design_head SET version_id=$1,updated_at=NOW() WHERE singleton=TRUE",
            version_id
        )
        await redis.delete("design:tokens:active")
        await self._log_action(version_id, 'rollback', actor)

class UserPreferencesService:
    async def get_css_vars(self, user_id: UUID) -> str:
        """Génère les CSS vars personnalisées pour injection dans le <head>"""
        prefs = await self.get_preferences(user_id)
        active = await design_version_svc.get_active_tokens()
        overrides = {}
        if theme := prefs.get('theme', {}):
            for agent, color in theme.get('agentColors', {}).items():
                if color: overrides[f'--agent-{agent}'] = color
            if scale := theme.get('fontScale'):
                overrides['--font-scale'] = str(scale)
        # Merge: active tokens + user overrides
        vars_lines = [f"  {k}: {v};" for k,v in {**active, **overrides}.items()]
        return f"[data-user='{user_id}'] {{\n" + "\n".join(vars_lines) + "\n}"
```

### docker-compose addition
```yaml
penpot:
  image: penpotapp/backend:latest
  environment:
    PENPOT_FLAGS: enable-access-tokens
  # ... config standard

penpot-frontend:
  image: penpotapp/frontend:latest
  # ...

penpot-mcp:
  image: ghcr.io/astrateam-net/penpot-mcp:latest
  ports: ["8787:8787"]
  environment:
    PENPOT_API_URL: http://penpot:6060
    PENPOT_ACCESS_TOKEN: ${PENPOT_ACCESS_TOKEN}
  depends_on: [penpot]
```

### .mcp.json (Claude Code CLI)
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

### api/design.py — endpoints complets
```
GET  /design/versions              → liste
GET  /design/versions/{v}          → snapshot immutable
POST /design/versions              → publie nouvelle version
POST /design/versions/rollback/{v} → rollback
GET  /design/versions/diff/{v1}/{v2} → diff tokens
GET  /design/tokens                → tokens HEAD actifs
GET  /design/user/{id}/preferences → prefs utilisateur
PUT  /design/user/{id}/preferences → sauvegarde overrides
GET  /design/user/{id}/css-vars    → CSS vars générées pour injection
GET  /design/rbac/{role}           → config layout rôle
PUT  /design/rbac/{role}           → update config (admin)
POST /design/nlp/intent            → NLP → DesignIntent
POST /design/penpot/sync           → Penpot → tokens → nouvelle version
```

### Frontend: injection CSS vars au runtime
```typescript
// _app.tsx (Next.js)
export default function App({ Component, pageProps, session }) {
  const { data: cssVars } = useQuery({
    queryKey: ['design-css-vars', session?.userId],
    queryFn: () => fetch(`/design/user/${session.userId}/css-vars`).then(r => r.text()),
    staleTime: 5 * 60 * 1000
  })

  return (
    <>
      {cssVars && <style data-design-prefs>{cssVars}</style>}
      <div data-user={session?.userId} data-role={session?.role}>
        <Component {...pageProps} />
      </div>
    </>
  )
}
```

## ACCEPTANCE TEST 14
```bash
python -c "
import asyncio, hashlib, json
from app.services.design_api import DesignVersionService, UserPreferencesService
from uuid import uuid4

async def test():
    svc = DesignVersionService()
    pref_svc = UserPreferencesService()

    # Crée une version
    tokens = {'--agent-sp': '#1BB68A', '--agent-clone': '#7B6EE8', '--bg-void': '#07070D'}
    v1 = await svc.publish_version(tokens, 'Test v1', 'test-actor')
    print(f'Version published: {v1}')

    # Publie v2
    tokens2 = {**tokens, '--agent-clone': '#9B7EF8'}
    v2 = await svc.publish_version(tokens2, 'Test v2 purple lighter', 'test-actor')
    print(f'Version v2: {v2}')

    # Vérifie HEAD = v2
    active = await svc.get_active_tokens()
    assert active['--agent-clone'] == '#9B7EF8', 'HEAD incorrect'
    print('HEAD = v2 OK')

    # Rollback vers v1
    await svc.rollback(v1, 'test-actor')
    active_after = await svc.get_active_tokens()
    assert active_after['--agent-clone'] == '#7B6EE8', 'Rollback failed'
    print('Rollback OK')

    # User preferences
    uid = uuid4()
    await pref_svc.save_preferences(uid, {
        'theme': {'agentColors': {'clone': '#FF00FF'}}
    })
    css = await pref_svc.get_css_vars(uid)
    assert '--agent-clone: #FF00FF' in css
    print('User preferences + CSS vars OK')

    print('Design API COMPLET OK')

asyncio.run(test())
"
```

---

## ORDRE D'EXÉCUTION — MISE À JOUR FINALE

```
1-13.  [inchangés]
14.    Composant 14 : Design API + Penpot + Versioning + Prefs
       RUN ACCEPTANCE TEST 14
15.    Copie skills/penpot-to-design-md.skill.md dans le projet
16.    Ajoute .mcp.json avec Penpot MCP endpoint
17.    Lance le pipeline NLP test:
         POST /design/nlp/intent {"text": "test theme sombre violet clone"}
         → vérifie DesignIntent retourné
18.    Génère DONE.md final avec:
         - 14 composants buildés
         - Conformance report > 80%
         - Versions design créées
         - Mocks actifs (MOCKS.md)
         - Commandes démarrage
```

---

## ARCHITECTURE FINALE AVEC COMPOSANT 14

```
╔══════════════════════════════════════════════════════════════════════╗
║  COUCHE B — COCKPIT STERN (custom)                                   ║
║  Profile Kernel · 4 Agents · OKR Spawner · Conformance Agent         ║
║                                                                       ║
║  UI Shell (Next.js) ← CSS vars injectées par Design API              ║
║    ↑ composants invariants v1 · headless · adapter-agnostiques        ║
╠══════════════════════════════════════════════════════════════════════╣
║  DESIGN API (Composant 14)                                            ║
║  Version Registry · User Prefs · RBAC Layout · NLP→Intent            ║
╠══════════════════════════════════════════════════════════════════════╣
║  ADA API (Composant 12) · Conformance (13)                            ║
╠══════════════════════════════════════════════════════════════════════╣
║  COUCHE A — HEADLESS BACKENDS                                         ║
║  LangGraph · Obot · Nango · Sim.ai · n8n · Penpot + Penpot MCP       ║
╚══════════════════════════════════════════════════════════════════════╝

RÈGLE ABSOLUE : Penpot = source de vérité visuelle
               DESIGN.md = source de vérité technique
               Design API = source de vérité runtime
               Les trois sont synchronisés. Jamais de divergence.
```

*Composant 14 ajouté — 2026-05-25*
