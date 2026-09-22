"""Run offline protection scenarios or replay a saved trace."""

import argparse
import asyncio
import json
import tomllib
import uuid
from pathlib import Path

from .contracts import LoginEvent, make_call
from .harness import Harness, replay
from .policy import decide
from .tools import MockProtectionTool


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    demo = commands.add_parser("demo")
    demo.add_argument("--config", type=Path, default=Path("configs/demo.toml"))
    playback = commands.add_parser("replay")
    playback.add_argument("trace", type=Path)
    args = parser.parse_args()
    if args.command == "replay":
        print(json.dumps(replay(args.trace), indent=2))
        return
    config = tomllib.loads(args.config.read_text(encoding="utf-8"))
    output = Path(config["output_dir"])
    output.mkdir(parents=True, exist_ok=True)
    summaries = []
    for scenario in config["scenarios"]:
        event = LoginEvent(**scenario["event"])
        action, reason = decide(event, config["policy"])
        if action is None:
            summaries.append({"scenario": scenario["name"], "state": "no_action", "reason": reason})
            continue
        call = make_call(event, action)
        run_id = uuid.uuid4().hex
        trace = output / f"{run_id}.jsonl"
        tool = MockProtectionTool(output / "mock-actions.db", fault=scenario["fault"])
        harness = Harness(tool, trace, run_id, **config["execution"])
        result = asyncio.run(harness.run(call))
        summaries.append({"scenario": scenario["name"], **result, "trace": str(trace), "reason": reason})
    print(json.dumps(summaries, indent=2))


if __name__ == "__main__":
    main()
