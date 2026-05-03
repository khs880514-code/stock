from __future__ import annotations

from collections import Counter
from statistics import mean
from typing import Any


def build_report(
    run_id: int,
    rule_version: str,
    since_date: str,
    until_date: str,
    verdicts: list[dict[str, Any]],
) -> dict[str, Any]:
    counts = Counter(item["verdict"] for item in verdicts)
    blocked_30d = [
        item["outcome_30d_usd_pct"]
        for item in verdicts
        if item["verdict"] == "block" and item["outcome_30d_usd_pct"] is not None
    ]
    passed_30d = [
        item["outcome_30d_usd_pct"]
        for item in verdicts
        if item["verdict"] == "pass" and item["outcome_30d_usd_pct"] is not None
    ]
    tp = sum(
        1
        for item in verdicts
        if item["verdict"] == "block"
        and item["outcome_30d_usd_pct"] is not None
        and item["outcome_30d_usd_pct"] <= 0
    )
    fp = sum(
        1
        for item in verdicts
        if item["verdict"] == "block"
        and item["outcome_30d_usd_pct"] is not None
        and item["outcome_30d_usd_pct"] > 0
    )
    tn = sum(
        1
        for item in verdicts
        if item["verdict"] == "pass"
        and item["outcome_30d_usd_pct"] is not None
        and item["outcome_30d_usd_pct"] > 0
    )
    fn = sum(
        1
        for item in verdicts
        if item["verdict"] == "pass"
        and item["outcome_30d_usd_pct"] is not None
        and item["outcome_30d_usd_pct"] <= 0
    )
    by_rule: dict[str, dict[str, int]] = {}
    for item in verdicts:
        for rule in item.get("triggered_rules", []):
            rule_stats = by_rule.setdefault(rule, {"triggers": 0, "blocked_loss_count": 0, "blocked_gain_count": 0})
            rule_stats["triggers"] += 1
            if item["verdict"] == "block" and item["outcome_30d_usd_pct"] is not None:
                if item["outcome_30d_usd_pct"] <= 0:
                    rule_stats["blocked_loss_count"] += 1
                else:
                    rule_stats["blocked_gain_count"] += 1

    return {
        "run_id": run_id,
        "rule_version": rule_version,
        "period": f"{since_date} ~ {until_date}",
        "totals": {
            "trades": len(verdicts),
            "blocked": counts["block"],
            "warned": counts["warn"],
            "passed": counts["pass"],
            "skipped": counts["skip"],
        },
        "rule_effectiveness": {
            "blocked_trades_outcome_30d_avg_usd_pct": mean(blocked_30d) if blocked_30d else None,
            "passed_trades_outcome_30d_avg_usd_pct": mean(passed_30d) if passed_30d else None,
            "true_positive_rate": tp / (tp + fn) if (tp + fn) else None,
            "false_positive_rate": fp / (fp + tn) if (fp + tn) else None,
        },
        "by_rule": by_rule,
        "verdicts": verdicts,
    }

