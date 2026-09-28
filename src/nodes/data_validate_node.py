"""AgentCore Platform v1.0"""

# Node contract (agents_layer_design.md §1):
#  - Extend FunctionNode; implement execute(state) -> dict
#  - Return ONLY the fields this node changes (never full state)
#  - Return AgentStatus enum constants — never plain strings [A1]
#  - Never import from mediator/, api/, or other agents

import json
from typing import Any, ClassVar

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event

_REQUIRED_METRIC_KEYS = ("traffic", "conversion", "basket")


class DataValidateNode(FunctionNode):
    """Outer pre_process: validate traffic/conversion/basket metrics vs baseline.

    Expects state["user_input"] to be a JSON string of the form:
        {"traffic_metrics": {"traffic": <num>, "conversion": <num>, "basket": <num>},
         "baseline_metrics": {"traffic": <num>, "conversion": <num>, "basket": <num>}}
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
                "traffic_data_validation_failed",
                {"correlation_id": state.get("correlation_id"), "reason": "missing traffic/baseline metrics"},
                state,
            )
            return {
                "status": AgentStatus.ERROR.value,
                "error_log": ["DataValidateNode: traffic_metrics/baseline_metrics missing or malformed"],
            }

        missing = [k for k in _REQUIRED_METRIC_KEYS if k not in traffic_metrics or k not in baseline_metrics]
        if missing:
            emit_trace_event(
                "traffic_data_validation_failed",
                {"correlation_id": state.get("correlation_id"), "missing_keys": missing},
                state,
            )
            return {
                "status": AgentStatus.ERROR.value,
                "error_log": [f"DataValidateNode: missing metric key(s) {missing}"],
            }

        validated_input = json.dumps(
            {"traffic_metrics": traffic_metrics, "baseline_metrics": baseline_metrics},
            ensure_ascii=False,
        )
        emit_trace_event(
            "traffic_data_validated",
            {"correlation_id": state.get("correlation_id"), "metrics": list(traffic_metrics.keys())},
            state,
        )
        return {
            "traffic_metrics": traffic_metrics,
            "baseline_metrics": baseline_metrics,
            "validated_input": validated_input,
            "status": AgentStatus.SUCCESS.value,
        }
