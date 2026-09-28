# RET-C2-068 — Unit Tests: DataValidateNode

import json

from framework.schemas.agent_status import AgentStatus
from src.nodes.data_validate_node import DataValidateNode


class TestDataValidateNode:
    def setup_method(self):
        self.node = DataValidateNode()

    def test_success_path(self):
        payload = {
            "traffic_metrics": {"traffic": 120, "conversion": 0.05, "basket": 3200},
            "baseline_metrics": {"traffic": 100, "conversion": 0.06, "basket": 3000},
        }
        state = {"user_input": json.dumps(payload), "node_history": [], "error_log": []}
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS
        assert result["traffic_metrics"] == payload["traffic_metrics"]
        assert result["baseline_metrics"] == payload["baseline_metrics"]
        assert "validated_input" in result

    def test_malformed_input_returns_error(self):
        state = {"user_input": "not json", "node_history": [], "error_log": []}
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.ERROR
        assert result["error_log"]

    def test_missing_metric_key_returns_error(self):
        payload = {
            "traffic_metrics": {"traffic": 120, "conversion": 0.05},  # basket missing
            "baseline_metrics": {"traffic": 100, "conversion": 0.06, "basket": 3000},
        }
        state = {"user_input": json.dumps(payload), "node_history": [], "error_log": []}
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.ERROR


# S-4 emit_trace_event coverage: assert a domain event fires on both the reject
# and success paths. Symbol is monkeypatched in the node module's own namespace
# (patching shared.utils.audit_logger does not intercept the already-imported ref).
class TestS4EmitTraceEventCoverage:
    def test_emits_on_reject_and_success(self, monkeypatch):
        import src.nodes.data_validate_node as mod

        calls = []
        monkeypatch.setattr(mod, "emit_trace_event", lambda *a, **k: calls.append(a[0]))

        DataValidateNode().execute({"user_input": "not json", "node_history": [], "error_log": []})
        assert "traffic_data_validation_failed" in calls

        calls.clear()
        payload = {
            "traffic_metrics": {"traffic": 120, "conversion": 0.05, "basket": 3200},
            "baseline_metrics": {"traffic": 100, "conversion": 0.06, "basket": 3000},
        }
        DataValidateNode().execute({"user_input": json.dumps(payload), "node_history": [], "error_log": []})
        assert "traffic_data_validated" in calls
