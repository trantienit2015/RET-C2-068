# RET-C2-068 — Unit Tests: AnomalyClassifyNode

from framework.schemas.agent_status import AgentStatus
from src.nodes.anomaly_classify_node import AnomalyClassifyNode


class TestAnomalyClassifyNode:
    def setup_method(self):
        self.node = AnomalyClassifyNode()

    def test_normal_when_no_variance(self):
        state = {"metric_variance": {}, "node_history": [], "error_log": []}
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS
        assert result["severity"] == "normal"

    def test_emergency_on_large_variance(self):
        state = {"metric_variance": {"traffic": -0.6}, "node_history": [], "error_log": []}
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS
        assert result["severity"] == "emergency"

    def test_watch_on_small_variance(self):
        state = {"metric_variance": {"conversion": 0.18}, "node_history": [], "error_log": []}
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS
        assert result["severity"] == "watch"

    def test_upstream_error_preserved_not_overwritten(self):
        state = {"status": AgentStatus.ERROR.value, "node_history": [], "error_log": ["upstream failed"]}
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.ERROR.value


# S-4 emit_trace_event coverage: assert a domain event fires on both the
# upstream-error passthrough path and the success path. Symbol is monkeypatched
# in the node module's own namespace (patching shared.utils.audit_logger does
# not intercept the already-imported ref).
class TestS4EmitTraceEventCoverage:
    def test_emits_on_upstream_error_and_success(self, monkeypatch):
        import src.nodes.anomaly_classify_node as mod

        calls = []
        monkeypatch.setattr(mod, "emit_trace_event", lambda *a, **k: calls.append(a[0]))

        AnomalyClassifyNode().execute({"status": AgentStatus.ERROR.value, "node_history": [], "error_log": []})
        assert "anomaly_classify_skipped" in calls

        calls.clear()
        AnomalyClassifyNode().execute({"metric_variance": {"traffic": -0.6}, "node_history": [], "error_log": []})
        assert "anomaly_classified" in calls
