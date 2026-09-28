"""AgentCore Platform v1.0"""

# RET-C2-068 — Retail AI-Driven Customer Traffic Anomaly & Conversion Alert Agent
#
# Cat 2 outer graph: AgentBaseGraph backbone with domain complexity encapsulated
# in the `main` slot via TrafficAnomalyGraphNode (GraphNode wrapping the inner
# subgraph). Do NOT override add_edges() on the outer graph.
#
# Backbone (fixed): initialize -> pre_process -> main -> {route} -> post_process
#                    -> finalize
#   pre_process  = DataValidateNode        (validate traffic/conversion/basket vs baseline)
#   main         = TrafficAnomalyGraphNode (GraphNode -> inner subgraph)
#   post_process = AlertGateNode           (assemble alert; non-suppressible CRITICAL/EMERGENCY)
#
# The GraphNode subclass lives HERE (not under src/nodes/) — GraphNode.__call__()
# intentionally does not run the standard S-1..S-4 node lifecycle (it delegates
# gating to the inner subgraph), and tests/proof_of_boundary/test_pb_invoke_order.py
# discovers every BaseNode subclass under src/nodes/ and asserts that lifecycle.

from typing import Any, ClassVar, cast

from framework.graph.agent_base_graph import AgentBaseGraph
from framework.nodes.graph_node import GraphNode
from framework.schemas.agent_state import AgentState
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event
from src.nodes.alert_gate_node import AlertGateNode
from src.nodes.data_validate_node import DataValidateNode
from src.schemas.state import State


class TrafficAnomalyGraphNode(GraphNode):
    """Wraps the inner traffic-anomaly workflow subgraph; assigned to the `main` slot."""

    # S-1 (outer main-slot GraphNode receives the caller's input first —
    # matches config/agent.yaml required_trust_level; NOT covered by
    # gate-trust-level-check, which only scans direct FunctionNode subclasses).
    required_trust_level: ClassVar[TrustLevel] = TrustLevel.VERIFIED_EXTERNAL

    # "propagate": re-raise inner graph exceptions as SubgraphError (fail fast).
    error_strategy: ClassVar[str] = "propagate"
    propagate_hitl: ClassVar[bool] = False

    def __init__(self, llm: Any = None) -> None:
        super().__init__()
        self._llm = llm

    def get_subgraph(self) -> Any:
        from src.graph.domain_workflow_graph import TrafficAnomalyWorkflowGraph

        sg = TrafficAnomalyWorkflowGraph(config=self._parent_config())
        sg.compile()
        return sg

    def extract_input(self, state: AgentState) -> str:
        # S-4: runs inside GraphNode.execute() — audit the dispatch into the inner subgraph.
        emit_trace_event("traffic_anomaly_dispatched", {"correlation_id": state.get("correlation_id")}, state)
        return cast(str, state.get("validated_input", state.get("user_input", "")))

    def merge_output(self, state: AgentState, sub_result: dict[str, Any]) -> dict[str, Any]:
        # S-4: runs inside GraphNode.execute() — audit the subgraph outcome merged back out.
        emit_trace_event(
            "traffic_anomaly_completed",
            {"correlation_id": state.get("correlation_id"), "severity": sub_result.get("severity")},
            state,
        )
        return {
            "traffic_metrics": sub_result.get("traffic_metrics", {}),
            "baseline_metrics": sub_result.get("baseline_metrics", {}),
            "metric_variance": sub_result.get("metric_variance", {}),
            "severity": sub_result.get("severity", "normal"),
            "cause_hypotheses": sub_result.get("cause_hypotheses", []),
            "recommendation": sub_result.get("recommendation", ""),
            "status": sub_result.get("status"),
        }

    def _parent_config(self) -> dict[str, Any]:
        return {"llm": self._llm}


class TrafficAnomalyAlertGraph(AgentBaseGraph):
    """Outer graph = the agent itself. Cat 2, L1-direct (AgentBaseGraph)."""

    @property
    def name(self) -> str:
        return "ret-c2-068"

    @property
    def state_schema(self) -> type:
        return State

    def register_nodes(self) -> None:
        super().register_nodes()  # injects InitializeNode + FinalizeNode
        llm = self.config.get("llm") if hasattr(self, "config") else None
        self._nodes["pre_process"] = DataValidateNode()
        self._nodes["main"] = TrafficAnomalyGraphNode(llm=llm)
        self._nodes["post_process"] = AlertGateNode()

    # add_edges() is NOT overridden — backbone wiring belongs to the framework.


Graph = TrafficAnomalyAlertGraph  # alias for agent.yaml module:"src.graph"
