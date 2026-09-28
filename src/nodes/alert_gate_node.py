"""AgentCore Platform v1.0"""

# Outer post_process node. Assembles the final alert payload and enforces the
# non-suppressible CRITICAL/EMERGENCY alert requirement via the S-3 output-gate
# hook (_extra_security_gate_output — preservation variant, not filtering).

from typing import Any, ClassVar

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event

_NON_SUPPRESSIBLE_SEVERITIES = ("critical", "emergency")


class AlertGateNode(FunctionNode):
    """Assemble the alert payload; CRITICAL/EMERGENCY severity is non-suppressible."""

    # S-1: explicit by design, not inherited implicitly.
    required_trust_level: ClassVar[TrustLevel] = TrustLevel.ANONYMOUS

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        severity = state.get("severity", "normal")
        cause_hypotheses = state.get("cause_hypotheses", [])
        recommendation = state.get("recommendation", "")

        alert_payload = {
            "severity": severity,
            "cause_hypotheses": cause_hypotheses,
            "recommendation": recommendation,
            "metric_variance": state.get("metric_variance", {}),
            "suppressible": severity not in _NON_SUPPRESSIBLE_SEVERITIES,
        }

        emit_trace_event(
            "alert_gated",
            {"correlation_id": state.get("correlation_id"), "severity": severity},
            state,
        )
        return {
            "alert_payload": alert_payload,
            "formatted_output": alert_payload,
            "status": AgentStatus.SUCCESS.value,
        }

    def _extra_security_gate_output(self, state: dict[str, Any]) -> dict[str, Any]:
        """S-3 preservation variant: CRITICAL/EMERGENCY alerts must never be silently
        suppressed or emptied by output filtering. Non-raising — reads/returns `state`.
        """
        alert_payload = state.get("alert_payload") or {}
        severity = alert_payload.get("severity", state.get("severity", "normal"))

        if severity in _NON_SUPPRESSIBLE_SEVERITIES:
            if not alert_payload.get("recommendation") or alert_payload.get("suppressible", False):
                return {
                    "status": AgentStatus.ERROR.value,
                    "error_log": [
                        f"AlertGateNode: {severity.upper()} alert was suppressed or missing "
                        "recommendation — non-suppressible alert violation (S-3)"
                    ],
                }
        return state
