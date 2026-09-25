"""Deterministic first-stage scan, with all thresholds supplied by configuration."""

from .feature import baseline_dates, daily_accounts


def scan(events, target_date, config):
    counts = daily_accounts(events, config["dimensions"])
    days = baseline_dates(target_date, config["baseline_offsets"])
    if not days or len(days) != len(set(days)) or any(day >= target_date for day in days):
        raise ValueError("Baseline dates must be unique and precede the target")
    candidates = []
    for (day, client, dimension, value), accounts in sorted(counts.items()):
        if day != target_date or len(accounts) < config["min_accounts"]:
            continue
        history = [len(counts.get((d, client, dimension, value), set())) for d in days]
        if sum(n > 0 for n in history) < config["min_history_days"]:
            continue
        baseline = sum(history) / len(days)
        tier = next(t for t in config["tiers"] if t["upper"] is None or baseline < t["upper"])
        increment = len(accounts) - baseline
        if len(accounts) < baseline * tier["ratio"] or increment < tier["increment"]:
            continue
        candidates.append({
            "client": client, "dimension": dimension, "value": value,
            "account_ids": sorted(accounts), "count": len(accounts),
            "baseline": baseline, "increment": increment,
            "ratio": len(accounts) / baseline if baseline else None,
            "baseline_dates": days, "baseline_counts": history,
        })
    return candidates
