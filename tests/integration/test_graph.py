# RET-C2-068 — Integration Test: full outer + inner graph

import json

from framework.schemas.invocation_context import InvocationContext
from framework.schemas.trust_level import TrustLevel
from src.graph.graph import Graph


class TestTrafficAnomalyAlertGraph:
    def setup_method(self):
        self.agent = Graph(config={"max_retry": 1})
        self.agent.compile()

    def _invoke(self, payload: dict):
        ctx = InvocationContext(
            session_id="test-session",
            caller_trust_level=TrustLevel.VERIFIED_EXTERNAL,
            caller_id="test-caller",
        )
        return self.agent.invoke(json.dumps(payload), ctx=ctx)

    def test_full_pipeline_success_normal(self):
        payload = {
            "traffic_metrics": {"traffic": 100, "conversion": 0.05, "basket": 3000},
            "baseline_metrics": {"traffic": 100, "conversion": 0.05, "basket": 3000},
        }
        result = self._invoke(payload)
        assert result["status"] in ("success", "SUCCESS")
        assert result.get("output") or result.get("formatted_output")

    def test_full_pipeline_critical_alert_non_suppressible(self):
        payload = {
            "traffic_metrics": {"traffic": 60, "conversion": 0.02, "basket": 3000},
            "baseline_metrics": {"traffic": 100, "conversion": 0.05, "basket": 3000},
        }
        result = self._invoke(payload)
        assert result["status"] in ("success", "SUCCESS")
        output = result.get("output") or result.get("formatted_output") or {}
        assert output.get("severity") in ("critical", "emergency")
        assert output.get("suppressible") is False

    def test_empty_input_errors(self):
        ctx = InvocationContext(
            session_id="test-session-empty",
            caller_trust_level=TrustLevel.VERIFIED_EXTERNAL,
            caller_id="test-caller",
        )
        result = self.agent.invoke("", ctx=ctx)
        assert result["status"] in ("error", "ERROR", "cancelled", "CANCELLED")
