"""AgentCore Platform v1.0"""

# Inner subgraph for RET-C2-068 (Cat 2). Instantiated by
# TrafficAnomalyGraphNode.get_subgraph() in src/graph/graph.py.
#
# Pipeline (linear):
#   START -> baseline_compare -> anomaly_classify -> cause_pattern_search
#         -> recommend_generate -> END
#
# The inner graph only receives state["user_input"] (JSON string set by the
# outer pre_process / GraphNode.extract_input) — it does NOT see the outer state.

from typing import Any
from langgraph.graph import END, START

from framework.graph.base_graph import BaseGraph
from framework.schemas.agent_state import AgentState
from framework.schemas.agent_status import AgentStatus
from src.nodes.anomaly_classify_node import AnomalyClassifyNode
from src.nodes.baseline_compare_node import BaselineCompareNode
from src.nodes.cause_pattern_search_node import CausePatternSearchNode
from src.nodes.recommend_generate_node import RecommendGenerateNode
from src.schemas.state import State


class TrafficAnomalyWorkflowGraph(BaseGraph):
    """Inner graph: baseline compare -> anomaly classify -> cause search -> recommend."""

    @property
    def name(self) -> str:
        return "ret_c2_068_traffic_anomaly_workflow"

    @property
    def state_schema(self) -> type:
        return State

    def _validate_config(self) -> None:
        # No mandatory config keys — `llm` is optional (nodes fall back to a
        # deterministic message when absent).
        pass

    def register_nodes(self) -> None:
        # No super() call — BaseGraph.register_nodes() is abstract.
        # Do NOT register initialize/finalize — outer backbone concern.
        llm = self.config.get("llm") if hasattr(self, "config") else None
        self._nodes["baseline_compare"] = BaselineCompareNode()
        self._nodes["anomaly_classify"] = AnomalyClassifyNode()
        self._nodes["cause_pattern_search"] = CausePatternSearchNode(llm=llm)
        self._nodes["recommend_generate"] = RecommendGenerateNode(llm=llm)

    def add_edges(self) -> None:
        self._sg.add_edge(START, "baseline_compare")
        self._sg.add_edge("baseline_compare", "anomaly_classify")
        self._sg.add_edge("anomaly_classify", "cause_pattern_search")
        self._sg.add_edge("cause_pattern_search", "recommend_generate")
        self._sg.add_edge("recommend_generate", END)

    def route(self, state: AgentState) -> str:
        # Required by BaseGraph ABC; this topology is linear so it is never called
        # unless add_conditional_edges() is added later.
        return END if state.get("status") == AgentStatus.ERROR.value else "recommend_generate"

    def get_output(self, state: AgentState) -> dict[str, Any]:
        return {
            "traffic_metrics": state.get("traffic_metrics", {}),
            "baseline_metrics": state.get("baseline_metrics", {}),
            "metric_variance": state.get("metric_variance", {}),
            "severity": state.get("severity", "normal"),
            "cause_hypotheses": state.get("cause_hypotheses", []),
            "recommendation": state.get("recommendation", ""),
            "status": state.get("status"),
            "trace_id": state.get("trace_id"),
            "correlation_id": state.get("correlation_id"),
            "node_history": state.get("node_history", []),
        }
