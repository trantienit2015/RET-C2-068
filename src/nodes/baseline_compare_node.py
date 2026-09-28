"""AgentCore Platform v1.0"""

# Inner subgraph node (Cat 2) — deterministic. Discovered by tests/proof_of_boundary/
# test_pb_invoke_order.py, so the constructor MUST support zero-arg instantiation.

import json
from typing import Any, ClassVar

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event
from src.services.service import compute_variance


class BaselineCompareNode(FunctionNode):
    """Inner step 1: compare current-day metrics vs baseline, produce per-metric variance.

    The inner subgraph only sees state["user_input"] (a JSON string set by the outer
    pre_process / GraphNode.extract_input) — it does NOT see the outer state directly.
    """

    # S-1: explicit by design, not inherited implicitly.
    required_trust_level: ClassVar[TrustLevel] = TrustLevel.ANONYMOUS

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        raw = state.get("user_input", "")
        try:
            payload = json.loads(raw) if isinstance(raw, str) else raw
        except (ValueError, TypeError):
            payload = None

        traffic_metrics = payload.get("traffic_metrics") if isinstance(payload, dict) else None
        baseline_metrics = payload.get("baseline_metrics") if isinstance(payload, dict) else None

        if not isinstance(traffic_metrics, dict) or not isinstance(baseline_metrics, dict):
            emit_trace_event(
                "baseline_compare_failed",
                {"correlation_id": state.get("correlation_id"), "reason": "no metrics in inner input"},
                state,
            )
            return {
                "status": AgentStatus.ERROR.value,
                "error_log": ["BaselineCompareNode: no traffic_metrics/baseline_metrics in inner input"],
            }

        variance = compute_variance(traffic_metrics, baseline_metrics)
        emit_trace_event(
            "baseline_compared",
            {"correlation_id": state.get("correlation_id"), "metric_variance": variance},
            state,
        )
        return {
            "traffic_metrics": traffic_metrics,
            "baseline_metrics": baseline_metrics,
            "metric_variance": variance,
            "status": AgentStatus.SUCCESS.value,
        }
