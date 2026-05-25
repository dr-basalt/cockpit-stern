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
