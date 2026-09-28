"""AgentCore Platform v1.0"""

# Inner subgraph node (Cat 2) — LLM reasoning. Constructor accepts `llm` with a
# default of None so PB-6 (tests/proof_of_boundary/test_pb_invoke_order.py) can
# instantiate the class with zero args.

from typing import Any, ClassVar

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event

_FALLBACK_HYPOTHESES = ["Cause pattern search unavailable — no LLM client configured; manual review recommended."]


class CausePatternSearchNode(FunctionNode):
    """Inner step 3: LLM cause-pattern hypothesis generation for the classified anomaly.

    Open-ended cause-hypothesis generation over multi-metric context is the
    reasoning step that justifies the Agent classification over a plain
    deterministic tool.
    """

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
                "cause_pattern_search_skipped",
                {"correlation_id": state.get("correlation_id"), "reason": "upstream error"},
                state,
            )
            return {"status": state.get("status")}

        severity = state.get("severity", "normal")
        variance = state.get("metric_variance", {})

        if severity == "normal":
            hypotheses: list[str] = []
        elif self._llm is None:
            hypotheses = list(_FALLBACK_HYPOTHESES)
        else:
            # BaseLLM.complete() requires messages: list — a real provider
            # client passes it straight through, so a bare prompt string is a
            # contract violation.
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a retail operations analyst. List the most likely cause "
                        "hypotheses for a store traffic/conversion anomaly, in order of likelihood."
                    ),
                },
                {
                    "role": "user",
                    "content": (f"Severity: {severity}. Per-metric variance vs baseline: {variance}."),
                },
            ]
            try:
                text = self._extract_text(self._llm.complete(messages))
            except (ConnectionError, TimeoutError, ValueError, RuntimeError) as exc:
                emit_trace_event(
                    "cause_pattern_search_llm_failed",
                    {"correlation_id": state.get("correlation_id"), "reason": type(exc).__name__},
                    state,
                )
                return {
                    "status": AgentStatus.ERROR.value,
                    "error_log": [f"CausePatternSearchNode: configured LLM call failed ({type(exc).__name__})"],
                }
            if not text:
                emit_trace_event(
                    "cause_pattern_search_llm_degraded",
                    {"correlation_id": state.get("correlation_id"), "reason": "empty_or_invalid_response"},
                    state,
                )
                return {
                    "status": AgentStatus.ERROR.value,
                    "error_log": ["CausePatternSearchNode: configured LLM returned an empty/invalid response"],
                }
            hypotheses = [line.strip("- ").strip() for line in text.splitlines() if line.strip()]

        emit_trace_event(
            "cause_pattern_searched",
            {"correlation_id": state.get("correlation_id"), "severity": severity, "n_hypotheses": len(hypotheses)},
            state,
        )
        return {
            "cause_hypotheses": hypotheses,
            "status": AgentStatus.SUCCESS.value,
        }
