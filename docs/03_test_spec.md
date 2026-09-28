# Test Specification

## Test Strategy
- Coverage target: every node ≥1 success + ≥1 error/edge unit test; ≥1 full-graph integration test
- Test types: Unit (per node) / Integration (full outer+inner graph) / Proof-of-Boundary

## Framework Compliance Tests (Mandatory)

| TC-ID | Test | Expected Result | Result |
|-------|------|----------------|--------|
| TC-01 | State contract: flat TypedDict | Type check pass, no Pydantic/dataclass | |
| TC-02 | SecurityViolationError fires on invalid input | Error raised | |
| TC-03 | No JWT/Credential in State | CI `gate-credential-scan`: 0 violations (S-5 enforcement runs in CI) | |
| TC-04 | InvocationContext via configurable only | Direct access raises error | |
| TC-05 | S-4: no duplicate lifecycle events in `execute()` | `node_start` / `node_complete` / `node_error` absent from `execute()` body | 0 duplicates |
| TC-06 | S-2: `_security_gate_input()` not overridden (`FunctionNode` subclass) | `TypeError` raised at class definition if overridden (`@final` enforced by framework) | 0 overrides |
| TC-07 | S-3: `_security_gate_output()` not overridden (`FunctionNode` subclass) | `TypeError` raised at class definition if overridden (`@final` enforced by framework) | 0 overrides |
| TC-08 | `required_trust_level` enforced | Insufficient trust → refused | |
| TC-09 | S-2: `_extra_security_gate_input()` non-trivial when domain checks needed | Domain-specific input checks execute correctly (e.g. PII scan on additional fields, consent validation, business rules) | Hook body non-trivial |
| TC-10 | S-3: `_extra_security_gate_output()` non-trivial when domain checks needed | Domain-specific output checks execute correctly (e.g. nested credential scan, PII re-check, content filtering, preservation verification) | Hook body non-trivial |
| TC-11 | S-4: at least one domain `emit_trace_event()` inside each `execute()` | Domain event emitted on every invocation path | ≥1 per node |

## Proof-of-Boundary Tests (Mandatory)

| PB-ID | Boundary | Test | Expected Result | Result |
|-------|----------|------|----------------|--------|
| PB-1 | BaseNode → EventEmitter | `emit_trace_event()` fires on every invocation path | No silent failures | |
| PB-2 | State serialization | Post-invoke State is primitives only | No Pydantic/dataclass | |
| PB-3 | Level 2 → External service | Real external service connection | Data retrieved | |
| PB-4 | Import isolation | No Level 0 imports | AST scan: 0 violations | |
| PB-5 | Checkpoint safety | No JWT/Pydantic in checkpoint | Inspection pass | |
| PB-6 | Invoke execution order | `__call__()`: S-1 trust gate → S-4 `node_start` → S-2 `_security_gate_input` → `execute()` → S-3 `_security_gate_output` → S-4 `node_complete` | Order verified | |

## Business Logic Tests

| TC-ID | Test | Input | Expected Result | Result |
|-------|------|-------|----------------|--------|
| BL-01 | DataValidateNode rejects malformed/missing metrics | non-JSON or missing traffic/baseline metric keys | `status=ERROR` | |
| BL-02 | BaselineCompareNode computes variance | traffic 130 vs baseline 100 | `metric_variance["traffic"] == 0.30` | |
| BL-03 | AnomalyClassifyNode severity thresholds | variance -0.60 / -0.35 / -0.18 / 0.0 | emergency / critical / watch / normal | |
| BL-04 | CausePatternSearchNode fallback without LLM | severity=watch, no llm configured | non-empty fallback hypotheses list | |
| BL-05 | AlertGateNode non-suppressible CRITICAL | severity=critical, recommendation set | `alert_payload["suppressible"] == False` | |
| BL-06 | AlertGateNode S-3 preservation hook rejects suppressed critical alert | severity=critical, recommendation empty | `_extra_security_gate_output` returns `status=ERROR` | |
| BL-07 | Full graph: normal-day metrics | traffic==baseline | pipeline `status=SUCCESS`, severity=normal | |
| BL-08 | Full graph: anomalous-day metrics | traffic/conversion far below baseline | pipeline `status=SUCCESS`, severity critical/emergency, alert non-suppressible | |

## Test Execution Summary
- Execution date: 2026-07-10
- Total tests: 6 unit files (DataValidate, BaselineCompare, AnomalyClassify, CausePatternSearch,
  RecommendGenerate, AlertGate) + 1 integration (full outer+inner graph) + 3 proof-of-boundary
  (import isolation, state safety, invoke order)
- Pass: TBD at CI / Fail: 0 expected / Skip: 0 expected
- Coverage: every node has ≥1 success-path + ≥1 error/edge unit test; full-graph integration
  covers both the normal path and the CRITICAL non-suppressible alert path
