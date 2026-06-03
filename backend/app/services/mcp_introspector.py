"""MCP Introspector — fait émerger le DDD, les gaps et les skills depuis les MCP tools.

Couche 0 → Couche 2 du framework de composition :
  MCP tools → Entities SCRUDX → Bounded Contexts → Relations → Gaps → Skills suggérées
"""

import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# --- SCRUDX verb mapping ---

VERB_TO_SCRUDX = {
    # Search
    "list": "S", "search": "S", "find": "S", "query": "S", "browse": "S", "filter": "S",
    # Create
    "create": "C", "add": "C", "send": "C", "new": "C", "insert": "C", "post": "C",
    "compose": "C", "quick_add": "C", "draft": "C",
    # Read
    "get": "R", "read": "R", "fetch": "R", "view": "R", "show": "R", "detail": "R",
    "retrieve": "R",
    # Update
    "update": "U", "edit": "U", "modify": "U", "patch": "U", "rename": "U",
    "replace": "U", "move": "U", "respond": "U", "transfer": "U",
    # Delete
    "delete": "D", "remove": "D", "archive": "D", "trash": "D", "revoke": "D",
    # eXecute
    "run": "X", "execute": "X", "trigger": "X", "sync": "X", "export": "X",
    "import": "X", "duplicate": "X", "copy": "X",
}

# Param names that hint at cross-BC relations
RELATION_PARAMS = {
    "email": "Communication",
    "attendees": "Communication",
    "calendar_id": "Scheduling",
    "event_id": "Scheduling",
    "file_id": "Storage",
    "document_id": "Storage",
    "folder_id": "Storage",
    "contact_id": "CRM",
    "deal_id": "CRM",
    "issue_id": "ProjectManagement",
    "project_id": "ProjectManagement",
    "page_id": "KnowledgeBase",
    "database_id": "KnowledgeBase",
    "url": "External",
}

# BC metadata
BC_META = {
    "google-calendar": {"bc_name": "Scheduling", "domain": "Time & Events"},
    "gmail": {"bc_name": "Communication", "domain": "Email"},
    "google-drive": {"bc_name": "Storage", "domain": "Files"},
    "google-docs": {"bc_name": "Documents", "domain": "Knowledge"},
    "google-sheets": {"bc_name": "Spreadsheets", "domain": "Data"},
    "slack": {"bc_name": "Messaging", "domain": "Communication"},
    "notion": {"bc_name": "KnowledgeBase", "domain": "Knowledge"},
    "hubspot": {"bc_name": "CRM", "domain": "Sales"},
    "linear": {"bc_name": "ProjectManagement", "domain": "Execution"},
    "stripe": {"bc_name": "Billing", "domain": "Finance"},
    "todoist": {"bc_name": "TaskManagement", "domain": "Execution"},
    "outlook": {"bc_name": "Communication_MS", "domain": "Email"},
}


@dataclass
class EntityOp:
    tool_name: str
    op: str  # S, C, R, U, D, X
    params: dict


@dataclass
class Entity:
    name: str
    operations: list[EntityOp] = field(default_factory=list)
    scrudx_mask: str = ""  # e.g. "S·C·R·U·D"

    def compute_mask(self):
        ops = set(op.op for op in self.operations)
        self.scrudx_mask = "·".join(o for o in "SCRUDX" if o in ops)


@dataclass
class BoundedContext:
    mcp_server: str
    name: str
    domain: str
    entities: dict[str, Entity] = field(default_factory=dict)
    all_params: set = field(default_factory=set)


@dataclass
class Relation:
    from_bc: str
    from_entity: str
    to_bc: str
    param: str
    relation_type: str  # ENRICH, SYNC, TRIGGER, AGGREGATE, CROSS_WRITE


@dataclass
class Gap:
    bc: str
    entity: str
    missing_op: str  # e.g. "U" (no update available)
    description: str


@dataclass
class SuggestedSkill:
    name: str
    pattern: str  # ENRICH, AGGREGATE, CROSS_WRITE, etc.
    tools: list[str]
    description: str
    trigger: str


def _parse_tool_name(tool_name: str) -> tuple[str, str]:
    """Extract (verb, entity) from tool name like 'list_events' → ('list', 'event')."""
    parts = tool_name.lower().replace("-", "_").split("_")

    # Try prefix match: first word = verb
    if parts[0] in VERB_TO_SCRUDX:
        verb = parts[0]
        entity_parts = parts[1:]
    # Try two-word verb: "quick_add"
    elif len(parts) >= 2 and f"{parts[0]}_{parts[1]}" in VERB_TO_SCRUDX:
        verb = f"{parts[0]}_{parts[1]}"
        entity_parts = parts[2:]
    # Fallback: look for verb anywhere
    else:
        verb = None
        entity_parts = parts
        for i, p in enumerate(parts):
            if p in VERB_TO_SCRUDX:
                verb = p
                entity_parts = parts[:i] + parts[i + 1:]
                break

    # Normalize entity: plural → singular, join parts
    entity = "_".join(entity_parts) if entity_parts else "unknown"
    entity = re.sub(r"s$", "", entity)  # naive depluralize
    entity = re.sub(r"ie$", "y", entity)  # emails → email, entries → entry
    entity = entity.strip("_") or "unknown"

    # Capitalize for display
    entity = entity.replace("_", " ").title().replace(" ", "")

    return verb or "unknown", entity


def introspect_tools(tools_by_server: dict[str, list[dict]]) -> dict:
    """Main introspection function.

    Args:
        tools_by_server: { "google-calendar": [{"name": "list_events", "description": ..., "params": {...}}, ...], ... }

    Returns:
        Full introspection result with BCs, entities, relations, gaps, suggested skills.
    """
    bounded_contexts: dict[str, BoundedContext] = {}
    all_relations: list[Relation] = []
    all_gaps: list[Gap] = []
    suggested_skills: list[SuggestedSkill] = []

    # --- COUCHE 0: Parse tools → entities + SCRUDX ---
    for server_key, tools in tools_by_server.items():
        meta = BC_META.get(server_key, {"bc_name": server_key.title(), "domain": "Other"})
        bc = BoundedContext(
            mcp_server=server_key,
            name=meta["bc_name"],
            domain=meta["domain"],
        )

        for tool in tools:
            tool_name = tool.get("name", "")
            params = tool.get("params", {})
            description = tool.get("description", "")

            verb, entity_name = _parse_tool_name(tool_name)
            op = VERB_TO_SCRUDX.get(verb, "?")

            if entity_name not in bc.entities:
                bc.entities[entity_name] = Entity(name=entity_name)

            bc.entities[entity_name].operations.append(
                EntityOp(tool_name=tool_name, op=op, params=params)
            )

            # Track all params for relation detection
            for param_name in params:
                bc.all_params.add(param_name.lower())

        # Compute SCRUDX masks
        for entity in bc.entities.values():
            entity.compute_mask()

        bounded_contexts[server_key] = bc

    # --- COUCHE 1: Detect relations via shared params ---
    bc_list = list(bounded_contexts.values())
    for i, bc_a in enumerate(bc_list):
        for param_name in bc_a.all_params:
            # Check if this param hints at another BC
            for hint_param, hint_bc in RELATION_PARAMS.items():
                if hint_param in param_name and hint_bc != bc_a.name:
                    # Find the target BC
                    for bc_b in bc_list:
                        if bc_b.name == hint_bc and bc_b.mcp_server != bc_a.mcp_server:
                            all_relations.append(Relation(
                                from_bc=bc_a.name,
                                from_entity=f"{bc_a.name}.{param_name}",
                                to_bc=bc_b.name,
                                param=param_name,
                                relation_type="ENRICH",
                            ))

    # Deduplicate relations
    seen_rels = set()
    unique_relations = []
    for r in all_relations:
        key = (r.from_bc, r.to_bc, r.param)
        if key not in seen_rels:
            seen_rels.add(key)
            unique_relations.append(r)
    all_relations = unique_relations

    # --- COUCHE 2: Detect gaps ---
    full_scrudx = set("SCRUD")
    for bc in bounded_contexts.values():
        for entity in bc.entities.values():
            entity_ops = set(op.op for op in entity.operations)
            # Only flag gaps for entities with at least 2 operations (skip trivial ones)
            if len(entity_ops) >= 2:
                missing = full_scrudx - entity_ops
                for m in missing:
                    op_names = {"S": "Search", "C": "Create", "R": "Read", "U": "Update", "D": "Delete"}
                    all_gaps.append(Gap(
                        bc=bc.name,
                        entity=entity.name,
                        missing_op=m,
                        description=f"{bc.name}.{entity.name} n'a pas de {op_names.get(m, m)}",
                    ))

    # --- COUCHE 2b: Suggest compositions / skills ---
    connected_bcs = set(bounded_contexts.keys())

    # AGGREGATE skill: if we have Scheduling + Communication + KnowledgeBase → morning_brief
    if {"google-calendar", "gmail"} <= connected_bcs:
        suggested_skills.append(SuggestedSkill(
            name="morning_brief",
            pattern="AGGREGATE",
            tools=["google-calendar.list_events", "gmail.list_emails"],
            description="Briefing du matin : agenda + emails non lus → priorite du jour",
            trigger="cron 07:00 ou intention 'briefing du jour'",
        ))

    if {"google-calendar", "gmail", "notion"} <= connected_bcs:
        suggested_skills.append(SuggestedSkill(
            name="morning_brief_full",
            pattern="AGGREGATE",
            tools=["google-calendar.list_events", "gmail.list_emails", "notion.fetch"],
            description="Briefing complet : agenda + emails + notes Notion → priority_card",
            trigger="cron 07:00 ou intention 'briefing complet'",
        ))

    # ENRICH skill: calendar event → email history with attendee
    if {"google-calendar", "gmail"} <= connected_bcs:
        suggested_skills.append(SuggestedSkill(
            name="prep_meeting",
            pattern="ENRICH",
            tools=["google-calendar.get_event", "gmail.list_emails", "google-drive.list_files"],
            description="Prepare un meeting : lit l'event, cherche les emails et fichiers lies aux attendees",
            trigger="intention 'prepare mon rdv de X'",
        ))

    # CROSS_WRITE: email → task
    if {"gmail", "linear"} <= connected_bcs:
        suggested_skills.append(SuggestedSkill(
            name="email_to_issue",
            pattern="CROSS_WRITE",
            tools=["gmail.read_email", "linear.create_issue"],
            description="Transforme un email en issue Linear (extrait titre, description, priorite)",
            trigger="intention 'transforme ce mail en tache'",
        ))

    if {"gmail", "google-calendar"} <= connected_bcs:
        suggested_skills.append(SuggestedSkill(
            name="email_to_event",
            pattern="CROSS_WRITE",
            tools=["gmail.read_email", "google-calendar.create_event"],
            description="Transforme un email en event calendar (extrait qui, quand, sujet)",
            trigger="intention 'planifie un rdv depuis ce mail'",
        ))

    # SYNC: calendar → notion (meeting notes)
    if {"google-calendar", "notion"} <= connected_bcs:
        suggested_skills.append(SuggestedSkill(
            name="meeting_notes_sync",
            pattern="SYNC",
            tools=["google-calendar.list_events", "notion.notion-create-pages"],
            description="Cree une page Notion pour chaque meeting du jour (template notes)",
            trigger="cron 08:00 ou intention 'prepare mes notes de meeting'",
        ))

    # AGGREGATE: weekly review
    if {"google-calendar", "gmail", "linear"} <= connected_bcs:
        suggested_skills.append(SuggestedSkill(
            name="weekly_review",
            pattern="AGGREGATE",
            tools=["google-calendar.list_events", "gmail.list_emails", "linear.list_issues"],
            description="Revue hebdo : events passes + threads ouverts + issues → retro",
            trigger="cron dimanche 18:00 ou intention 'weekly review'",
        ))

    # TRIGGER: new urgent email → calendar block
    if {"gmail", "google-calendar"} <= connected_bcs:
        suggested_skills.append(SuggestedSkill(
            name="urgent_email_blocker",
            pattern="TRIGGER",
            tools=["gmail.list_emails", "google-calendar.create_event"],
            description="Si email urgent detecte → bloque 30min dans le calendrier pour traiter",
            trigger="poll gmail toutes les 15min ou webhook",
        ))

    # Drive + Docs composition
    if {"google-drive", "google-docs"} <= connected_bcs:
        suggested_skills.append(SuggestedSkill(
            name="doc_from_template",
            pattern="CROSS_WRITE",
            tools=["google-drive.list_files", "google-docs.create_document"],
            description="Cree un Google Doc depuis un template Drive (brief, proposal, etc.)",
            trigger="intention 'cree un doc depuis template X'",
        ))

    # Build output
    return {
        "bounded_contexts": [
            {
                "mcp_server": bc.mcp_server,
                "name": bc.name,
                "domain": bc.domain,
                "entities": [
                    {
                        "name": e.name,
                        "scrudx": e.scrudx_mask,
                        "operations": [
                            {"tool": op.tool_name, "op": op.op, "params": list(op.params.keys())}
                            for op in e.operations
                        ],
                    }
                    for e in bc.entities.values()
                ],
                "entity_count": len(bc.entities),
                "total_tools": sum(len(e.operations) for e in bc.entities.values()),
            }
            for bc in bounded_contexts.values()
        ],
        "relations": [
            {
                "from": r.from_bc,
                "to": r.to_bc,
                "param": r.param,
                "type": r.relation_type,
            }
            for r in all_relations
        ],
        "gaps": [
            {
                "bc": g.bc,
                "entity": g.entity,
                "missing": g.missing_op,
                "description": g.description,
            }
            for g in all_gaps
        ],
        "suggested_skills": [
            {
                "name": s.name,
                "pattern": s.pattern,
                "tools": s.tools,
                "description": s.description,
                "trigger": s.trigger,
            }
            for s in suggested_skills
        ],
        "stats": {
            "total_bcs": len(bounded_contexts),
            "total_entities": sum(len(bc.entities) for bc in bounded_contexts.values()),
            "total_tools": sum(
                sum(len(e.operations) for e in bc.entities.values())
                for bc in bounded_contexts.values()
            ),
            "total_relations": len(all_relations),
            "total_gaps": len(all_gaps),
            "total_suggested_skills": len(suggested_skills),
        },
    }
