"""Structured model outputs. No data loading or execution logic."""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class Verdict(BaseModel):
    model_config = ConfigDict(extra="forbid")
    account_id: str
    label: Literal["takeover", "not_takeover", "uncertain"]
    reason: str
    evidence_ids: list[str]


class Assessment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    verdicts: list[Verdict]


class Investigation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    summary: str
    entry: str
    takeover: str
    abuse: str
    policy_gaps: list[str]
    uncertainties: list[str]
