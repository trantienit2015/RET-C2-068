# RET-C2-068 — Unit Tests: BaselineCompareNode

import json

from framework.schemas.agent_status import AgentStatus
from src.nodes.baseline_compare_node import BaselineCompareNode


class TestBaselineCompareNode:
    def setup_method(self):
        self.node = BaselineCompareNode()

    def test_success_path(self):
        payload = {
            "traffic_metrics": {"traffic": 130, "conversion": 0.05, "basket": 3000},
            "baseline_metrics": {"traffic": 100, "conversion": 0.05, "basket": 3000},
        }
        state = {"user_input": json.dumps(payload), "node_history": [], "error_log": []}
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS
        assert result["metric_variance"]["traffic"] > 0

    def test_missing_metrics_returns_error(self):
        state = {"user_input": json.dumps({}), "node_history": [], "error_log": []}
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.ERROR


# S-4 emit_trace_event coverage: assert a domain event fires on both the reject
# and success paths. Symbol is monkeypatched in the node module's own namespace
# (patching shared.utils.audit_logger does not intercept the already-imported ref).
class TestS4EmitTraceEventCoverage:
    def test_emits_on_reject_and_success(self, monkeypatch):
        import src.nodes.baseline_compare_node as mod

        calls = []
        monkeypatch.setattr(mod, "emit_trace_event", lambda *a, **k: calls.append(a[0]))

        BaselineCompareNode().execute({"user_input": json.dumps({}), "node_history": [], "error_log": []})
        assert "baseline_compare_failed" in calls

        calls.clear()
        payload = {
            "traffic_metrics": {"traffic": 130, "conversion": 0.05, "basket": 3000},
            "baseline_metrics": {"traffic": 100, "conversion": 0.05, "basket": 3000},
        }
        BaselineCompareNode().execute({"user_input": json.dumps(payload), "node_history": [], "error_log": []})
        assert "baseline_compared" in calls
