"""Experiment artifact and logging helpers."""

import json
import logging
from datetime import datetime

import yaml


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def start_run(root, config):
    name = config["experiment_name"]
    if not name.replace("_", "").replace("-", "").isalnum():
        raise ValueError("Experiment name must contain only letters, digits, _ or -")
    run = root / config["logging"]["path"] / f"{datetime.now():%Y%m%d_%H%M%S_%f}_{name}"
    run.mkdir(parents=True, exist_ok=False)
    (run / "config.yaml").write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    logger = logging.getLogger(str(run))
    logger.setLevel(logging.INFO)
    logger.propagate = False
    handler = logging.FileHandler(run / "run.log", encoding="utf-8")
    logger.addHandler(handler)
    return run, logger
