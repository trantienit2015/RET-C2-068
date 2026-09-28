# RET-C2-068 — Unit Tests: RecommendGenerateNode

from framework.schemas.agent_status import AgentStatus
from src.nodes.recommend_generate_node import RecommendGenerateNode


class FakeLLM:
    """Bare-string fake — RecommendGenerateNode._extract_text() accepts both
    the canonical dict shape and a bare string (backward-compat)."""

    def complete(self, messages: list) -> str:
        return "Restock Zone 3 immediately and verify pricing display."


class DictLLM:
    """Canonical BaseLLM.complete() shape: {"content": str, ...}."""

    def complete(self, messages: list) -> dict:
        return {"content": "Restock Zone 3 immediately and verify pricing display."}


class EmptyLLM:
    """Configured LLM that returns an empty/invalid response — must be treated
    as a provider failure (ERROR), not silently degraded to fallback."""

    def complete(self, messages: list) -> dict:
        return {"content": ""}


class RaisingLLM:
    """Configured LLM whose transport fails — must surface as ERROR."""

    def complete(self, messages: list):
        raise ConnectionError("provider unavailable")


class TestRecommendGenerateNode:
    def test_success_path_with_llm(self):
        node = RecommendGenerateNode(llm=FakeLLM())
        state = {
            "severity": "critical",
            "cause_hypotheses": ["stockout"],
            "node_history": [],
            "error_log": [],
        }
        result = node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS
        assert result["recommendation"]

    def test_normal_severity_no_action(self):
        node = RecommendGenerateNode()
        state = {"severity": "normal", "cause_hypotheses": [], "node_history": [], "error_log": []}
        result = node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS
        assert "No anomaly" in result["recommendation"]

    def test_fallback_without_llm(self):
        node = RecommendGenerateNode()
        state = {"severity": "emergency", "cause_hypotheses": ["stockout"], "node_history": [], "error_log": []}
        result = node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS
        assert result["recommendation"]

    def test_upstream_error_preserved_not_overwritten(self):
        node = RecommendGenerateNode()
        state = {"status": AgentStatus.ERROR.value, "node_history": [], "error_log": ["upstream failed"]}
        result = node.execute(state)
        assert result["status"] == AgentStatus.ERROR.value

    def test_success_path_with_canonical_dict_llm(self):
        node = RecommendGenerateNode(llm=DictLLM())
        state = {"severity": "critical", "cause_hypotheses": ["stockout"], "node_history": [], "error_log": []}
        result = node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS.value
        assert result["recommendation"]

    def test_configured_llm_empty_response_is_error_not_fallback(self):
        # 3m half-fix trap: a configured-but-failing LLM must never silently
        # degrade to the deterministic fallback — that would mask the failure.
        node = RecommendGenerateNode(llm=EmptyLLM())
        state = {"severity": "critical", "cause_hypotheses": ["stockout"], "node_history": [], "error_log": []}
        result = node.execute(state)
        assert result["status"] == AgentStatus.ERROR.value
        assert result["error_log"]

    def test_configured_llm_transport_failure_is_error(self):
        node = RecommendGenerateNode(llm=RaisingLLM())
        state = {"severity": "critical", "cause_hypotheses": ["stockout"], "node_history": [], "error_log": []}
        result = node.execute(state)
        assert result["status"] == AgentStatus.ERROR.value
        assert result["error_log"]


# S-4 emit_trace_event coverage: assert a domain event fires on both the
# upstream-error passthrough path and the success path. Symbol is monkeypatched
# in the node module's own namespace (patching shared.utils.audit_logger does
# not intercept the already-imported ref).
class TestS4EmitTraceEventCoverage:
    def test_emits_on_upstream_error_and_success(self, monkeypatch):
        import src.nodes.recommend_generate_node as mod

        calls = []
        monkeypatch.setattr(mod, "emit_trace_event", lambda *a, **k: calls.append(a[0]))

        RecommendGenerateNode().execute({"status": AgentStatus.ERROR.value, "node_history": [], "error_log": []})
        assert "recommend_generate_skipped" in calls

        calls.clear()
        RecommendGenerateNode().execute(
            {"severity": "normal", "cause_hypotheses": [], "node_history": [], "error_log": []}
        )
        assert "recommendation_generated" in calls
