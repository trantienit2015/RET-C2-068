# Template Design Specification

## Position in AgentCore Architecture

- **Agent Class**: TrafficAnomalyAlertGraph
- **L1 Base**: AgentBaseGraph (outer) + GraphNode (`main` slot) + BaseGraph (inner) — Cat 2 pattern
- **Three-Layer Separation**:
  - State: flat TypedDict composition (no Pydantic — msgpack incompatible)
  - Node: L1 inheritance (Template Method: `execute(self, state: dict) -> dict` override only)
  - Graph: composition (`register_nodes()` for node substitution)

## Architecture Overview

Cat 2 outer graph wraps a multi-step inner subgraph (6 business steps > 3 fixed outer
slots), per the Cat 2 pattern (outer `AgentBaseGraph` + `GraphNode` in `main` + inner
`BaseGraph`).

### Outer Node Configuration

| Node | Responsibility | Input State | Output State | Inherits/Overrides |
|------|---------------|-------------|--------------|-------------------|
| initialize | schema_version, session_id, trust_level | — | — | InitializeNode (default) |
| pre_process | DataValidateNode: validate traffic/conversion/basket vs baseline | `user_input` (JSON) | `traffic_metrics`, `baseline_metrics`, `validated_input` | FunctionNode |
| main | TrafficAnomalyGraphNode: dispatch to inner subgraph | `validated_input` | `metric_variance`, `severity`, `cause_hypotheses`, `recommendation` | GraphNode |
| post_process | AlertGateNode: assemble alert; non-suppressible CRITICAL/EMERGENCY | `severity`, `cause_hypotheses`, `recommendation` | `alert_payload`, `formatted_output` | FunctionNode |
| finalize | response_metadata, total_time_ms | — | — | FinalizeNode (default) |

### Inner Subgraph Node Configuration (`src/graph/domain_workflow_graph.py`)

| Node | Responsibility |
|------|----------------|
| baseline_compare | Compute per-metric relative variance vs baseline (deterministic) |
| anomaly_classify | Classify severity tier normal/watch/critical/emergency from variance (deterministic, rule-based thresholds) |
| cause_pattern_search | LLM: generate cause-pattern hypotheses over multi-metric context |
| recommend_generate | LLM: generate actionable recommendation from severity + cause hypotheses |

### Data Flow

```
Outer:
START → initialize → pre_process(DataValidate) → main(GraphNode) → post_process(AlertGate)
      → finalize → END

Inner (invoked by main via GraphNode.get_subgraph().invoke(validated_input, ctx)):
START → baseline_compare → anomaly_classify → cause_pattern_search → recommend_generate → END
```

### State Definition

| Field | Type | Purpose | Required |
|-------|------|---------|----------|
| traffic_metrics | `NotRequired[dict]` | Current-day traffic/conversion/basket metrics | Yes (set by pre_process) |
| baseline_metrics | `NotRequired[dict]` | Operator-provided baseline for the same metrics | Yes (set by pre_process) |
| metric_variance | `NotRequired[dict]` | Per-metric relative variance vs baseline | Set by inner baseline_compare |
| severity | `NotRequired[str]` | normal / watch / critical / emergency | Set by inner anomaly_classify |
| cause_hypotheses | `NotRequired[list[str]]` | LLM cause-pattern hypotheses | Set by inner cause_pattern_search |
| recommendation | `NotRequired[str]` | LLM actionable recommendation | Set by inner recommend_generate |
| alert_payload | `NotRequired[dict]` | Final assembled alert | Set by outer post_process |

**State Constraints (mandatory):**
- Flat TypedDict only (primitives + JSON-serializable types); every agent-specific field
  wrapped in `NotRequired[...]` (state-safety standard).
- No JWT, API keys, credentials in State (checkpoint DB leakage)
- InvocationContext via `config["configurable"]` only (not in State)
- No Pydantic models, dataclass, arbitrary Python objects (msgpack incompatible)

## Framework Utilization

### Shared Components Used
- [x] InvocationContext (correlation_id, session_id, permissions, credential handle)
- [ ] ConnectionPolicy (retry/timeout strategy)
- [ ] SecurityViolationError
- [ ] S-2: `_extra_security_gate_input()` — not needed; default PII scan on `user_input`/
      `validated_input` is sufficient (traffic/conversion metrics are non-PII numeric data)
- [x] S-3: `_extra_security_gate_output()` on `AlertGateNode` — **preservation variant**:
      rejects output where a CRITICAL/EMERGENCY severity alert was silently suppressed or
      left without a recommendation (non-suppressible alert requirement from proposal).
- [x] S-4: `emit_trace_event()` — at least one domain-specific event inside each `execute()`
      on every node (DataValidate, BaselineCompare, AnomalyClassify, CausePatternSearch,
      RecommendGenerate, AlertGate) plus the GraphNode `extract_input`/`merge_output` hooks.

> **S-2/S-3 gate behaviour by node type (ADR-017):**
> - `FunctionNode` subclass → framework `@final` gate always runs automatically;
>   extend via `_extra_security_gate_input()` / `_extra_security_gate_output()` only
> - `GraphNode` / `RemoteAgentNode` → deliberate no-op (upstream or remote node's gate already applied)
> - Custom `BaseNode` subclass → must implement `_security_gate_input()` and
>   `_security_gate_output()` directly (`@abstractmethod` — omission raises `TypeError` at instantiation)

### Composition Pattern

- **Pattern**: GraphNode (subgraph) — Cat 2 outer `AgentBaseGraph` + `main` slot wraps an
  inner `BaseGraph` (`TrafficAnomalyWorkflowGraph`) via `TrafficAnomalyGraphNode`.
- **Composition target**: `src/graph/domain_workflow_graph.py::TrafficAnomalyWorkflowGraph`
- **Error propagation strategy**: `propagate` (fail fast — inner errors surface as
  `SubgraphError` to the outer graph; no graceful degradation needed for this use case)

## Import Isolation Confirmation
- [x] Template does not import agenticstar-platform SDK (Level 0)
- [x] Import targets: framework/ and shared/ only (no agents/base/ required)

## Design Decision Record

| Decision | Option A | Option B | Chosen | Rationale |
|----------|----------|----------|--------|-----------|
| L1 base type | AgentBaseGraph | AutonomousBaseGraph | AgentBaseGraph | Fixed 6-step pipeline, no autonomous loop needed |
| Composition pattern | Flat 3-slot (Cat 1 style) | GraphNode + inner subgraph (Cat 2) | GraphNode + inner subgraph | 6 business steps > 3 outer slots; `gate-composition` requires this for Cat 2 |
| Baseline dependency | Compute baseline in-template | Accept operator-provided baseline | Operator-provided | Baseline ingestion pipeline is out of scope per proposal (Sprint 2 dependency) |
