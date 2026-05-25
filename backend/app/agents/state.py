from typing import TypedDict, Annotated, Literal

from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    profile: dict  # HumanProfile.model_dump() equivalent
    inversion_config: dict  # InversionConfig serialized
    energy_level: int  # 1-10
    task_type: Literal[
        "production",  # → Clone
        "challenge",  # → Anti
        "sacral_stimulus",  # → SP
        "flow",  # → SP
        "irreversible_decision",  # → HITL real
    ]
    active_agent: str
    requires_hitl: bool
    hitl_token: str | None
    not_self_detected: bool
    session_id: str
    context: str  # memory context injected
