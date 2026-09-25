"""Deterministic fixture generation; labels are kept separate from evidence."""

import random
from datetime import date, timedelta


def generate(config):
    rng = random.Random(config["seed"])
    cfg = config["synthetic"]
    target = date.fromisoformat(cfg["target_date"])
    accounts, labels, events = {}, {}, []
    for case in cfg["cases"]:
        for i in range(case["target_accounts"]):
            aid = f"u{len(accounts):06d}"
            month = rng.randrange(1, 13)
            accounts[aid] = {
                "registered": f"2023-{month:02d}-01",
                "registration_country": rng.choice(cfg["countries"]),
                "historical_devices": [f"owner-{aid}"],
                "registration_device": f"owner-{aid}",
            }
            labels[aid] = case["label"]
            for offset in range(-cfg["history_days"], 1):
                if offset != 0 and i >= case["baseline_accounts"]:
                    continue
                day = (target + timedelta(days=offset)).isoformat()
                is_attack_day = offset == 0 and case["label"] == "takeover"
                known = case["known_device"]
                device = f"owner-{aid}" if known else f"new-{aid}"
                event = {
                    "event_id": f"e{len(events):07d}", "account_id": aid,
                    "date": day, "timestamp": day + "T10:00:00Z", "client": "web",
                    "new_environment": True, "device": device,
                    "features": {"app": case["app"], "tls_fingerprint": case["fingerprint"]},
                    "sensitive_actions": (["password_change", "email_change", "withdrawal"]
                                          if is_attack_day else []),
                    "owner_confirmed": case["owner_confirmed"] if offset == 0 else None,
                    "risk": {"rule_id": "new-device", "hit": not known,
                             "configured_action": "observe", "final_action": "allow"},
                }
                events.append(event)
    rng.shuffle(events)
    return {"events": events, "accounts": accounts}, labels
