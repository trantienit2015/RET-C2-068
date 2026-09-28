"""AgentCore Platform v1.0"""

# Inner subgraph node (Cat 2) — deterministic. Zero-arg constructor (PB-6 discovery).

from typing import Any, ClassVar

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event
from src.services.service import classify_severity


class AnomalyClassifyNode(FunctionNode):
    """Inner step 2: classify severity tier (normal/watch/critical/emergency) from variance."""

    # S-1: explicit by design, not inherited implicitly.
    required_trust_level: ClassVar[TrustLevel] = TrustLevel.ANONYMOUS

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        # Inner subgraph edges are unconditional (linear topology, no per-step route()) —
        # a node running after an upstream ERROR must NOT overwrite status back to SUCCESS.
        if state.get("status") == AgentStatus.ERROR.value:
            emit_trace_event(
                "anomaly_classify_skipped",
                {"correlation_id": state.get("correlation_id"), "reason": "upstream error"},
                state,
            )
            return {"status": state.get("status")}

        variance = state.get("metric_variance", {})
        severity = classify_severity(variance)
        emit_trace_event(
            "anomaly_classified",
            {"correlation_id": state.get("correlation_id"), "severity": severity},
            state,
        )
        return {
            "severity": severity,
            "status": AgentStatus.SUCCESS.value,
        }
