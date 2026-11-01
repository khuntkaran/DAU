"""The rule set in the database, kept in step with the rule file, and its citations."""

import uuid
from collections.abc import Callable
from typing import Any, Literal, cast

from sqlalchemy import select
from sqlalchemy.orm import Session

from api.app import models
from api.app.schemas import CitationOut, RulesOut
from rules.loader import RuleSet, load_rules

SCHEME = "pm_surya_ghar"

RuleRow = tuple[str, str, Callable[[RuleSet], dict[str, Any]]]
Status = Literal["confirmed", "verify", "assumption"]

# rule_key -> (rule_type, applies_to, parameters read from the rule file)
RULE_ITEMS: dict[str, RuleRow] = {
    "CFA_SLAB_1": (
        "subsidy",
        "general",
        lambda r: {
            "inr_per_kw": r.subsidy.general.first_slab_inr_per_kw,
            "up_to_kw": str(r.subsidy.first_slab_kw),
        },
    ),
    "CFA_SLAB_2": (
        "subsidy",
        "general",
        lambda r: {
            "inr_per_kw": r.subsidy.general.second_slab_inr_per_kw,
            "next_kw": str(r.subsidy.second_slab_kw),
        },
    ),
    "CFA_CAP": (
        "subsidy",
        "all",
        lambda r: {"no_cfa_above_kw": str(r.subsidy.first_slab_kw + r.subsidy.second_slab_kw)},
    ),
    "CFA_PRO_RATA": ("subsidy", "all", lambda _: {}),
    "CFA_SPECIAL": (
        "subsidy",
        "special",
        lambda r: {
            "first_inr_per_kw": r.subsidy.special.first_slab_inr_per_kw,
            "second_inr_per_kw": r.subsidy.special.second_slab_inr_per_kw,
        },
    ),
    "SIZE_BANDS": ("sizing", "all", lambda r: {"step_kw": str(r.sizing.step_kw)}),
    "GENERATION": (
        "generation",
        "all",
        lambda r: {"kwh_per_kw_month": str(r.sizing.generation_kwh_per_kw_month)},
    ),
    "ROOF_AREA": ("area", "all", lambda r: {"sqm_per_kw": str(r.sizing.roof_m2_per_kw)}),
    "USABLE_FRACTION": (
        "area",
        "all",
        lambda r: {"default_fraction": str(r.sizing.default_usable_fraction)},
    ),
    "TARIFF_DEFAULT": (
        "cost_benchmark",
        "all",
        lambda r: {"inr_per_kwh": str(r.payback.default_tariff_inr_per_kwh)},
    ),
    "SCORE_MODEL": ("scoring", "all", lambda r: r.scoring.model_dump(mode="json")),
}


def ensure_rule_set(db: Session) -> models.RuleSet:
    """The database row for the rule file's version, created on first use."""
    rules = load_rules()
    existing = db.scalars(
        select(models.RuleSet).where(models.RuleSet.version == rules.version)
    ).first()
    if existing is not None:
        return existing

    missing = set(rules.citations) - set(RULE_ITEMS)
    if missing:
        raise RuntimeError(f"rule file: no rule_items mapping for {sorted(missing)}")
    # A new rule file version replaces the active one; old calculations keep their version.
    for old in db.scalars(select(models.RuleSet).where(models.RuleSet.is_active)):
        old.is_active = False
    db.flush()
    rule_set = models.RuleSet(
        scheme=SCHEME,
        version=rules.version,
        effective_from=rules.effective_from,
        is_active=True,
        source_checked_on=rules.checked_on,
    )
    db.add(rule_set)
    db.flush()
    for key, citation in rules.citations.items():
        rule_type, applies_to, params = RULE_ITEMS[key]
        db.add(
            models.RuleItem(
                rule_set_id=rule_set.id,
                rule_key=key,
                rule_type=rule_type,
                applies_to=applies_to,
                params=params(rules),
                description=citation.title,
                source_title=citation.source,
                source_url=citation.url,
                status=citation.status,
            )
        )
    db.flush()
    return rule_set


def citations_for(db: Session, rule_set_id: uuid.UUID) -> dict[str, CitationOut]:
    items = db.scalars(select(models.RuleItem).where(models.RuleItem.rule_set_id == rule_set_id))
    return {
        item.rule_key: CitationOut(
            key=item.rule_key,
            title=item.description,
            source=item.source_title,
            url=item.source_url,
            status=cast(Status, item.status),
        )
        for item in items
    }


def current_rules() -> RulesOut:
    rules = load_rules()
    return RulesOut(
        version=rules.version,
        effective_from=rules.effective_from,
        checked_on=rules.checked_on,
        subsidy=rules.subsidy,
        sizing=rules.sizing,
        payback=rules.payback,
        scoring=rules.scoring,
        citations=[
            CitationOut(key=key, **citation.model_dump())
            for key, citation in rules.citations.items()
        ],
    )
