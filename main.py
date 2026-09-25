"""Load configuration and wire the investigation experiment."""

import argparse
from pathlib import Path

import yaml

from src.trainer import run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--prepare-only", action="store_true",
                        help="Generate fixtures and evidence only; no LLM or verdicts")
    args = parser.parse_args()
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    print(run(Path(__file__).resolve().parent, config, args.prepare_only))


if __name__ == "__main__":
    main()
