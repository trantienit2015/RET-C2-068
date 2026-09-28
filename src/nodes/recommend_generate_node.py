"""AgentCore Platform v1.0"""

# Inner subgraph node (Cat 2) — LLM reasoning. Constructor accepts `llm` with a
# default of None so PB-6 can instantiate the class with zero args.

from typing import Any, ClassVar

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event

_FALLBACK_RECOMMENDATION = (
    "Recommendation generation unavailable — no LLM client configured; escalate to manual review."
)


class RecommendGenerateNode(FunctionNode):
    """Inner step 4: LLM actionable-recommendation authoring from severity + cause hypotheses."""

    # S-1: explicit by design, not inherited implicitly.
    required_trust_level: ClassVar[TrustLevel] = TrustLevel.ANONYMOUS

    def __init__(self, llm: Any = None) -> None:
        self._llm = llm

    @staticmethod
    def _extract_text(raw: Any) -> str:
        """Normalise an LLM response into text.

        AgentCore BaseLLM.complete() returns the canonical dict
        {"content": str, ...}; a bare string is also accepted for
        compatibility with test fakes. Anything else yields "".
        """
        if isinstance(raw, dict):
            content = raw.get("content", "")
            return content if isinstance(content, str) else ""
        if isinstance(raw, str):
            return raw
        return ""

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        # Inner subgraph edges are unconditional — preserve an upstream ERROR instead
        # of overwriting status back to SUCCESS.
        if state.get("status") == AgentStatus.ERROR.value:
            emit_trace_event(
                "recommend_generate_skipped",
                {"correlation_id": state.get("correlation_id"), "reason": "upstream error"},
                state,
            )
            return {"status": state.get("status")}

        severity = state.get("severity", "normal")
        cause_hypotheses = state.get("cause_hypotheses", [])

        if severity == "normal":
            recommendation = "No anomaly detected — no action required."
        elif self._llm is None:
            recommendation = _FALLBACK_RECOMMENDATION
        else:
            # BaseLLM.complete() requires messages: list — a real provider
            # client passes it straight through, so a bare prompt string is a
            # contract violation.
            messages = [
                {
                    "role": "system",
                    "content": "You are a retail ops advisor. Write a concise, actionable recommendation.",
                },
                {
                    "role": "user",
                    "content": f"Anomaly severity: {severity}. Cause hypotheses: {cause_hypotheses}.",
                },
            ]
            try:
                text = self._extract_text(self._llm.complete(messages))
            except (ConnectionError, TimeoutError, ValueError, RuntimeError) as exc:
                emit_trace_event(
                    "recommend_generate_llm_failed",
                    {"correlation_id": state.get("correlation_id"), "reason": type(exc).__name__},
                    state,
                )
                return {
                    "status": AgentStatus.ERROR.value,
                    "error_log": [f"RecommendGenerateNode: configured LLM call failed ({type(exc).__name__})"],
                }
            if not text.strip():
                emit_trace_event(
                    "recommend_generate_llm_degraded",
                    {"correlation_id": state.get("correlation_id"), "reason": "empty_or_invalid_response"},
                    state,
                )
                return {
                    "status": AgentStatus.ERROR.value,
                    "error_log": ["RecommendGenerateNode: configured LLM returned an empty/invalid response"],
                }
            recommendation = text.strip()

        emit_trace_event(
            "recommendation_generated",
            {"correlation_id": state.get("correlation_id"), "severity": severity},
            state,
        )
        return {
            "recommendation": recommendation,
            "status": AgentStatus.SUCCESS.value,
        }
