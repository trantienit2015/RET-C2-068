"""AgentCore Platform v1.0"""

# Service layer: deterministic domain calculations for traffic-anomaly detection.
# Must NOT contain routing, security gating, or credentials.
# Called by BaselineCompareNode / AnomalyClassifyNode.

from __future__ import annotations

from typing import Any

# Severity thresholds on the worst-metric relative variance (fraction, e.g. -0.30 = -30%).
_WATCH_THRESHOLD = 0.15
_CRITICAL_THRESHOLD = 0.30
_EMERGENCY_THRESHOLD = 0.50

_METRIC_KEYS = ("traffic", "conversion", "basket")


def compute_variance(traffic_metrics: dict[str, Any], baseline_metrics: dict[str, Any]) -> dict[str, float]:
    """Relative variance per metric: (current - baseline) / baseline.

    Missing/zero baseline for a metric is skipped (returns no entry for it).
    """
    variance: dict[str, float] = {}
    for key in _METRIC_KEYS:
        current = traffic_metrics.get(key)
        baseline = baseline_metrics.get(key)
        if not isinstance(current, (int, float)) or not isinstance(baseline, (int, float)) or baseline == 0:
            continue
        variance[key] = (current - baseline) / baseline
    return variance


def classify_severity(variance: dict[str, float]) -> str:
    """Classify anomaly severity from the worst (largest-magnitude) metric variance."""
    if not variance:
        return "normal"
    worst = max(variance.values(), key=abs)
    magnitude = abs(worst)
    if magnitude >= _EMERGENCY_THRESHOLD:
        return "emergency"
    if magnitude >= _CRITICAL_THRESHOLD:
        return "critical"
    if magnitude >= _WATCH_THRESHOLD:
        return "watch"
    return "normal"
