"""AgentCore Platform v1.0"""

# ADR-005: State must be a flat TypedDict — never Pydantic BaseModel.
# LangGraph checkpoints use msgpack serialization; Pydantic objects
# cause silent corruption.  Extend AgentState with agent-specific
# fields only.  Do NOT add credentials, secrets, or Pydantic models.

from typing import NotRequired

from framework.schemas.agent_state import AgentState


# Type-check note: the wheel ships no py.typed, so mypy resolves AgentState to Any
# and reports every NotRequired below as valid-type. The fields are correct (the state
# contract requires NotRequired) -- the report is a packaging artifact, suppressed per field.
# Drop these ignores once the wheel ships py.typed.
class State(AgentState):
    """Agent state for RET-C2-068 Traffic Anomaly & Conversion Alert Agent.

    All shared fields (user_input, status, session_id, node_history,
    error_log, hitl_*, etc.) are inherited from AgentState.
    """

    # Input metrics (traffic / conversion / basket) for the current day.
    traffic_metrics: NotRequired[dict]  # type: ignore[valid-type]
    # Operator-provided pre-computed baseline for the same metrics.
    baseline_metrics: NotRequired[dict]  # type: ignore[valid-type]
    # Per-metric variance/delta produced by BaselineCompare.
    metric_variance: NotRequired[dict]  # type: ignore[valid-type]
    # Anomaly severity tier: normal / watch / critical / emergency.
    severity: NotRequired[str]  # type: ignore[valid-type]
    # LLM-generated cause-pattern hypotheses for the classified anomaly.
    cause_hypotheses: NotRequired[list[str]]  # type: ignore[valid-type]
    # LLM-generated actionable recommendation text.
    recommendation: NotRequired[str]  # type: ignore[valid-type]
    # Final assembled alert payload (post_process output).
    alert_payload: NotRequired[dict]  # type: ignore[valid-type]
