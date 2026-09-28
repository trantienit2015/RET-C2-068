# RET-C2-068 — Retail AI-Driven Customer Traffic Anomaly & Conversion Alert Agent

> **Category**: Cat 2 (orchestrates multiple steps to accomplish a specific use case)
> **Industry**: RET

## Overview

A retail analyst sends one day's store metrics — `traffic`, `conversion` and `basket` —
together with a pre-computed baseline for the same three metrics. The agent compares the
two, classifies how serious the deviation is, and returns an alert payload.

Input is a JSON string:

```json
{"traffic_metrics": {"traffic": 62, "conversion": 0.031, "basket": 2100},
 "baseline_metrics": {"traffic": 100, "conversion": 0.06, "basket": 3000}}
```

How it works today:

- **Validation** (outer `pre_process`): rejects input that is not this JSON shape or lacks
  any of the three metric keys.
- **Inner workflow** (a `GraphNode` in the `main` slot):
  1. computes the relative variance `(current - baseline) / baseline` per metric;
  2. classifies severity from the largest absolute variance: below 15 % `normal`, from 15 %
     `watch`, from 30 % `critical`, from 50 % `emergency` (fixed thresholds in
     `src/services/service.py`);
  3. for a non-normal severity, asks an LLM for likely causes and for a recommendation.
     **When no LLM client is configured, these two steps return fixed placeholder text**
     saying that manual review is needed — they do not invent causes.
- **Alert gate** (outer `post_process`): builds the alert payload (severity, causes,
  recommendation, per-metric variance, `suppressible`). `critical` and `emergency` alerts are
  marked non-suppressible, and an output-gate re-check returns an error if such an alert
  has lost its recommendation or been marked suppressible.

The severity classification is fully deterministic. The only optional external dependency is
an LLM client for the cause and recommendation text; nothing is sent anywhere else.

This is an agent template built with the **AGENTIC STAR** development platform and the
**AgentCore Framework**. It is intended to be taken as a starting point: fork it, adapt it to
your own data and policies, and run it inside your own AGENTIC STAR deployment.

## Requirements

**This template does not run standalone.** It requires:

| Requirement | Notes |
|---|---|
| **AGENTIC STAR platform** | The agent connects to the platform at start-up. Without it, start-up fails immediately (see *Behaviour without the platform* below). Deployment guides and API documentation: [AGENTIC STAR Developers](https://developers.fd.agenticstar.tm.softbank.jp/) |
| **AgentCore Framework** (`agenticstar-agentcore`) | Installed from PyPI as a dependency. |
| Python | 3.11 or later |

```bash
pip install -e .
```

### Behaviour without the platform

The framework is designed to run **only** on AGENTIC STAR. There is no fallback or degraded
mode. If the platform is unreachable or the SDK version does not match, the agent raises
`PlatformRequired` during graph compile / start-up preflight rather than starting in a partially
working state. This is intentional — a half-running agent is worse than one that refuses to start.

## Quick Start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m pytest tests/ -v
```

Tests run without a platform connection. Running the agent itself does not.

## Project Structure

```
src/          agent implementation (nodes, services, schemas)
tests/        unit, integration and boundary tests
config/       agent configuration
docs/         design and test specification
```

See `docs/02_design.md` for the design and `docs/03_test_spec.md` for the test specification.

## Customising

1. Adjust `config/` for your own environment and policies.
2. Replace the knowledge sources and sample data with your own.
3. Review the node implementations under `src/nodes/` for domain-specific logic.
4. Re-run the test suite.

## License

MIT — see [LICENSE](LICENSE).

## Status of this repository

This template is published **as is**, by its individual author, under the MIT license. It carries
**no warranty and no support commitment**, and no organisation stands behind its behaviour or
fitness for any purpose. Issues and pull requests may or may not receive a response; that is at
the sole discretion of the repository owner.
