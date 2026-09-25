"""Pure evidence preparation and deterministic gates."""

from collections import defaultdict

from .feature import overlap


def merge_candidates(candidates, cutoff):
    # Complete-link grouping avoids merging disjoint cohorts through a bridge.
    groups = []
    for candidate in candidates:
        ids = set(candidate["account_ids"])
        group = next((g for g in groups if all(
            overlap(ids, set(other["account_ids"])) >= cutoff for other in g)), None)
        if group is None:
            groups.append([candidate])
        else:
            group.append(candidate)
    return [{"id": f"g{i:03d}", "candidates": group,
             "account_ids": sorted(set.union(*(set(c["account_ids"]) for c in group)))}
            for i, group in enumerate(groups)]


def cards_for(data, account_ids, target_date):
    indexed = defaultdict(list)
    for event in data["events"]:
        if event["date"] == target_date:
            indexed[event["account_id"]].append(event)
    cards = []
    for aid in sorted(account_ids):
        profile = data["accounts"][aid]
        history = set(profile["historical_devices"]) | {profile["registration_device"]}
        evidence = []
        for event in sorted(indexed[aid], key=lambda e: (e["timestamp"], e["event_id"])):
            evidence.append({"id": event["event_id"], "timestamp": event["timestamp"],
                             "device_seen_before": event["device"] in history,
                             "sensitive_actions": event["sensitive_actions"],
                             "owner_confirmed": event["owner_confirmed"],
                             "risk": event["risk"]})
        cards.append({"account_id": aid, "evidence": evidence})
    return cards


def validate_verdicts(cards, verdicts):
    lookup = {c["account_id"]: {e["id"] for e in c["evidence"]} for c in cards}
    ids = [v.account_id for v in verdicts]
    if len(ids) != len(set(ids)) or set(ids) != set(lookup):
        raise ValueError("Model account IDs do not reconcile with supplied cards")
    for verdict in verdicts:
        if not verdict.reason.strip() or not verdict.evidence_ids:
            raise ValueError("Every verdict needs a reason and evidence")
        if not set(verdict.evidence_ids) <= lookup[verdict.account_id]:
            raise ValueError("Model cited evidence not belonging to this account")


def census_gate(cards, verdicts, threshold):
    # Initial implementation judges the full cohort, avoiding invalid sequential
    # confidence intervals. Uncertain labels create an explicit prevalence range.
    validate_verdicts(cards, verdicts)
    if not cards:
        return {"status": "unresolved", "lower": 0.0, "upper": 1.0}
    lookup = {c["account_id"]: c for c in cards}
    positive = uncertain = 0
    for v in verdicts:
        unblocked = any(e["risk"]["final_action"] == "allow"
                        for e in lookup[v.account_id]["evidence"])
        positive += v.label == "takeover" and unblocked
        uncertain += v.label == "uncertain" and unblocked
    lower, upper = positive / len(cards), (positive + uncertain) / len(cards)
    status = "pass" if lower > threshold else "reject" if upper < threshold else "unresolved"
    return {"status": status, "lower": lower, "upper": upper,
            "method": "full_cohort_label_bounds", "accounts": len(cards),
            "warning": "Bounds reflect unresolved model labels, not classification accuracy"}


def diagnose(cards):
    result = []
    for card in cards:
        for evidence in card["evidence"]:
            risk = evidence["risk"]
            status = "not_hit"
            if risk["hit"]:
                if risk["final_action"] in {"block", "challenge"}:
                    status = "protected"
                elif risk["configured_action"] == "observe":
                    status = "observation_only"
                elif risk["configured_action"] == "block" and risk["final_action"] == "allow":
                    status = "overridden"
                else:
                    status = "unresolved"
            result.append({"account_id": card["account_id"], "event_id": evidence["id"],
                           "rule_id": risk["rule_id"], "status": status})
    return result
