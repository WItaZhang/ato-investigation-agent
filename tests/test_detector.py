from pathlib import Path

import yaml

from src.detector import scan
from src.feature import baseline_dates, overlap


def config():
    return yaml.safe_load(Path("configs/investigation.yaml").read_text())["scan"]


def rows(day, count, value="tool", client="web"):
    return [dict(date=day, account_id=f"a{i}", client=client, new_environment=True,
                 features={"app": value}) for i in range(count)]


def test_scan_excludes_recent_contamination_and_deduplicates_accounts():
    cfg = config()
    events = [row for day in baseline_dates("2026-09-24", cfg["baseline_offsets"])
              for row in rows(day, 10)]
    events += rows("2026-09-23", 5000)
    events += rows("2026-09-24", 110) * 2
    result = scan(events, "2026-09-24", cfg)
    assert len(result) == 1
    assert result[0]["baseline"] == 10
    assert result[0]["count"] == 110
    assert result[0]["increment"] == 100


def test_large_ratio_without_absolute_increment_is_rejected():
    cfg = config()
    events = [row for day in baseline_dates("2026-09-24", cfg["baseline_offsets"])
              for row in rows(day, 10)]
    assert scan(events + rows("2026-09-24", 99), "2026-09-24", cfg) == []


def test_insufficient_value_history_is_not_scanned():
    events = rows("2026-09-15", 10) + rows("2026-09-16", 10) + rows("2026-09-24", 500)
    assert scan(events, "2026-09-24", config()) == []


def test_clients_do_not_share_baselines():
    cfg = config()
    events = [row for day in baseline_dates("2026-09-24", cfg["baseline_offsets"])
              for row in rows(day, 10, client="mobile")]
    assert scan(events + rows("2026-09-24", 500), "2026-09-24", cfg) == []


def test_overlap_uses_smaller_cohort():
    assert overlap({1, 2}, {1, 2, 3, 4}) == 1
    assert overlap(set(), {1}) == 0
