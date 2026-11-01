"""Loads and validates the versioned rule file."""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, model_validator

RULE_FILE = Path(__file__).with_name("pm_surya_ghar_v2024_03.yaml")

StateCategory = Literal["general", "special"]


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Slabs(_Frozen):
    first_slab_inr_per_kw: int
    second_slab_inr_per_kw: int


class SubsidyRules(_Frozen):
    general: Slabs
    special: Slabs
    first_slab_kw: Decimal
    second_slab_kw: Decimal


class SizingRules(_Frozen):
    generation_kwh_per_kw_month: Decimal
    roof_m2_per_kw: Decimal
    default_usable_fraction: Decimal
    step_kw: Decimal


class PaybackRules(_Frozen):
    default_tariff_inr_per_kwh: Decimal


class ScoreWeights(_Frozen):
    net_cost_per_kw: int
    warranty: int
    component_quality: int
    completeness: int
    timeline: int
    vendor_rating: int

    @model_validator(mode="after")
    def weights_total_100(self) -> "ScoreWeights":
        if sum(self.model_dump().values()) != 100:
            raise ValueError("score weights must total 100")
        return self


class WarrantyTargets(_Frozen):
    panel: int
    inverter: int
    workmanship: int


class ScoringRules(_Frozen):
    weights: ScoreWeights
    warranty_targets_years: WarrantyTargets
    max_vendor_rating: Decimal


class Citation(_Frozen):
    title: str
    source: str
    url: str | None
    status: Literal["confirmed", "verify", "assumption"]


class RuleSet(_Frozen):
    version: str
    effective_from: date
    checked_on: date
    subsidy: SubsidyRules
    sizing: SizingRules
    payback: PaybackRules
    scoring: ScoringRules
    citations: dict[str, Citation]


def parse_rules(text: str) -> RuleSet:
    return RuleSet.model_validate(yaml.safe_load(text))


@lru_cache
def load_rules() -> RuleSet:
    return parse_rules(RULE_FILE.read_text(encoding="utf-8"))


def to_inr(amount: Decimal) -> int:
    """Rounds once, at the end of a calculation, to whole rupees."""
    return int(amount.quantize(Decimal(1), rounding=ROUND_HALF_UP))
