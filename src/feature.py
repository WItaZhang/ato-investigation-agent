"""Stateless account-level aggregations; no file or model access."""

from collections import defaultdict
from datetime import date, timedelta


def daily_accounts(events, dimensions):
    counts = defaultdict(set)
    for event in events:
        if not event["new_environment"]:
            continue
        for dimension in dimensions.get(event["client"], []):
            value = event["features"].get(dimension)
            if value is not None:
                key = (event["date"], event["client"], dimension, str(value))
                counts[key].add(event["account_id"])
    return counts


def baseline_dates(target_date, offsets):
    target = date.fromisoformat(target_date)
    return [(target + timedelta(days=offset)).isoformat() for offset in offsets]


def overlap(left, right):
    return len(left & right) / min(len(left), len(right)) if left and right else 0.0
