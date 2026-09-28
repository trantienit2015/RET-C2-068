# RET-C2-068 — Unit Tests: AlertGateNode (incl. S-3 non-suppressible preservation hook)

from framework.schemas.agent_status import AgentStatus
from src.nodes.alert_gate_node import AlertGateNode


class TestAlertGateNode:
    def setup_method(self):
        self.node = AlertGateNode()

    def test_success_path_normal_severity(self):
        state = {
            "severity": "normal",
            "cause_hypotheses": [],
            "recommendation": "No anomaly detected — no action required.",
            "metric_variance": {},
            "node_history": [],
            "error_log": [],
        }
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS
        assert result["alert_payload"]["suppressible"] is True

    def test_critical_alert_is_non_suppressible(self):
        state = {
            "severity": "critical",
            "cause_hypotheses": ["stockout"],
            "recommendation": "Restock immediately.",
            "metric_variance": {"traffic": -0.35},
            "node_history": [],
            "error_log": [],
        }
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS
        assert result["alert_payload"]["suppressible"] is False

    def test_extra_security_gate_output_passes_valid_critical_alert(self):
        state = {
            "severity": "critical",
            "alert_payload": {
                "severity": "critical",
                "recommendation": "Restock immediately.",
                "suppressible": False,
            },
        }
        result = self.node._extra_security_gate_output(state)
        assert result is state

    def test_extra_security_gate_output_rejects_suppressed_critical_alert(self):
        state = {
            "severity": "critical",
            "alert_payload": {
                "severity": "critical",
                "recommendation": "",
                "suppressible": True,
            },
        }
        result = self.node._extra_security_gate_output(state)
        assert result["status"] == AgentStatus.ERROR
        assert result["error_log"]


# S-4 emit_trace_event coverage: assert a domain event fires on execute()'s
# (single) path. Symbol is monkeypatched in the node module's own namespace
# (patching shared.utils.audit_logger does not intercept the already-imported ref).
class TestS4EmitTraceEventCoverage:
    def test_emits_on_execute(self, monkeypatch):
        import src.nodes.alert_gate_node as mod

        calls = []
        monkeypatch.setattr(mod, "emit_trace_event", lambda *a, **k: calls.append(a[0]))

        AlertGateNode().execute(
            {
                "severity": "normal",
                "cause_hypotheses": [],
                "recommendation": "No anomaly detected — no action required.",
                "metric_variance": {},
                "node_history": [],
                "error_log": [],
            }
        )
        assert "alert_gated" in calls
