"""Deterministic belief-confidence simulator over collected video metrics.

This is the "agent learns" demo. Given the seed beliefs from `agent_beliefs`
and the per-video metrics snapshots, we compute a per-belief retention delta
relative to the baseline (videos NOT carrying that belief), and translate the
delta into a small confidence shift (clamped to ±0.15 per run).

The math is intentionally simple — pure Python over already-validated rows.
For the demo, the simulator runs over the mock-seed videos (is_demo_seed=true).
Production will swap the source to real videos, no schema change required.

Output is a list of "evolution cards", each with:
  - rule_key, rule_text, current_confidence (from agent_beliefs)
  - new_confidence (current + delta, clamped 0..1)
  - sample_size (videos carrying the belief)
  - retention_delta (avg retention belief vs baseline; e.g. +0.18 = +18%)
  - rationale (1-line plain English)
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from src.logger import log


@dataclass
class BeliefEvolution:
    rule_key: str
    rule_text: str
    current_confidence: float
    new_confidence: float
    sample_size: int
    retention_delta: float
    rationale: str
    is_demo: bool


def _avg(xs: list[float]) -> float | None:
    cleaned = [x for x in xs if isinstance(x, int | float)]
    return sum(cleaned) / len(cleaned) if cleaned else None


def _latest_per_video(snapshots: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """For each video_id, return the most recent snapshot (highest observed_at)."""
    latest: dict[str, dict[str, Any]] = {}
    for s in snapshots:
        vid = s.get("video_id")
        if not vid:
            continue
        prev = latest.get(vid)
        if prev is None or (s.get("observed_at") or "") > (prev.get("observed_at") or ""):
            latest[vid] = s
    return latest


def simulate_evolution(
    beliefs: list[dict[str, Any]],
    videos: list[dict[str, Any]],
    snapshots: list[dict[str, Any]],
) -> list[BeliefEvolution]:
    """beliefs: rows from agent_beliefs (rule_key, rule_text, confidence).
    videos: rows from videos with `agent_decision.beliefs_applied` populated.
    snapshots: rows from video_metrics_snapshot (need retention_50pct).

    Returns one BeliefEvolution per belief that has ≥3 sample videos. Beliefs
    below the threshold are dropped from the output (no signal yet)."""

    latest = _latest_per_video(snapshots)

    # Group retention by belief application: belief_key → list[retention]
    by_belief: dict[str, list[float]] = defaultdict(list)
    baseline_retention: list[float] = []
    is_demo = False

    for v in videos:
        snap = latest.get(v["id"])
        retention = snap.get("retention_50pct") if snap else None
        if retention is None:
            continue
        retention_f = float(retention)
        baseline_retention.append(retention_f)
        decision = v.get("agent_decision") or {}
        beliefs_applied = decision.get("beliefs_applied") or []
        if v.get("user_id") is None:
            is_demo = True  # at least one demo-seed video contributing
        for key in beliefs_applied:
            by_belief[key].append(retention_f)

    baseline_avg = _avg(baseline_retention) or 0.0
    output: list[BeliefEvolution] = []
    for belief in beliefs:
        rule_key = belief["rule_key"]
        samples = by_belief.get(rule_key, [])
        if len(samples) < 3:
            continue
        belief_avg = _avg(samples) or 0.0
        if baseline_avg <= 0:
            delta = 0.0
        else:
            delta = (belief_avg / baseline_avg) - 1.0
        # Map relative delta → confidence shift, clamped ±0.15 per run.
        confidence_delta = max(-0.15, min(0.15, delta * 0.3))
        current = float(belief.get("confidence", 0.5))
        new_conf = max(0.0, min(1.0, current + confidence_delta))
        rationale = (
            f"Based on {len(samples)} listings carrying this belief, retention is "
            f"{belief_avg * 100:.0f}% vs {baseline_avg * 100:.0f}% baseline "
            f"({'+' if delta >= 0 else ''}{delta * 100:.0f}%)."
        )
        output.append(
            BeliefEvolution(
                rule_key=rule_key,
                rule_text=belief.get("rule_text", ""),
                current_confidence=current,
                new_confidence=round(new_conf, 3),
                sample_size=len(samples),
                retention_delta=round(delta, 3),
                rationale=rationale,
                is_demo=is_demo,
            )
        )

    # Stable sort: largest absolute confidence shift first — surface the
    # beliefs the demo wants to highlight at the top of the page.
    output.sort(key=lambda b: abs(b.new_confidence - b.current_confidence), reverse=True)
    log.info(
        "belief_evolution: simulated %d/%d beliefs, baseline_retention=%.3f",
        len(output),
        len(beliefs),
        baseline_avg,
    )
    return output
