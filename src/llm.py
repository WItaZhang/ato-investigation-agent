"""Bounded real-model calls; no tools, generated code, or database access."""

import json
import os

from openai import OpenAI


class BudgetExceeded(RuntimeError):
    pass


class Analyst:
    def __init__(self, config, run_dir, client=None):
        self.config = config
        self.run_dir = run_dir
        self.reserved = 0.0
        self.actual = 0.0
        self.calls = 0
        if client is None:
            key = os.environ.get(config["api_key_env"])
            if not key:
                raise RuntimeError(f"Set {config['api_key_env']} before a live investigation")
            client = OpenAI(api_key=key, base_url=config["base_url"],
                            timeout=config["timeout_seconds"], max_retries=0)
        self.client = client

    def ask(self, instructions, payload, schema):
        content = json.dumps(payload, ensure_ascii=True, sort_keys=True)
        # Conservative byte-based input allowance, including schema and framing.
        # Reservations are never released, even after timeouts or refusals.
        input_bound = len((instructions + content + json.dumps(schema.model_json_schema())).encode())
        input_bound += self.config["framing_token_allowance"]
        reserve = (input_bound * self.config["input_usd_per_million"]
                   + self.config["max_output_tokens"] * self.config["output_usd_per_million"]) / 1e6
        if input_bound > self.config["max_input_token_bound"]:
            raise BudgetExceeded("Input exceeds the configured bound")
        if self.reserved + reserve > self.config["budget_usd"]:
            raise BudgetExceeded("Run budget would be exceeded; no request sent")
        self.reserved += reserve
        self.calls += 1
        audit = {"call": self.calls, "model": self.config["model"],
                 "reserved_usd": self.reserved, "status": "pending"}
        path = self.run_dir / f"llm-{self.calls:03d}.json"
        path.write_text(json.dumps(audit, indent=2), encoding="utf-8")
        response = self.client.responses.parse(
            model=self.config["model"], instructions=instructions,
            input=content, text_format=schema, store=False,
            reasoning={"effort": self.config["reasoning_effort"]},
            max_output_tokens=self.config["max_output_tokens"],
        )
        if response.usage:
            self.actual += (response.usage.input_tokens * self.config["input_usd_per_million"]
                            + response.usage.output_tokens * self.config["output_usd_per_million"]) / 1e6
        audit.update(status=response.status, actual_usd=self.actual,
                     response_id=response.id, response=response.model_dump(mode="json"))
        path.write_text(json.dumps(audit, indent=2), encoding="utf-8")
        if response.status != "completed" or response.output_parsed is None:
            raise RuntimeError("Model returned incomplete output or refused; stage remains unresolved")
        return response.output_parsed
