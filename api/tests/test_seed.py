"""The seed script builds an identical local database on each laptop from files in Git."""

import hashlib
import json
import shutil
from collections.abc import Iterator
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from api.app import models
from api.app.db import Base, make_engine
from api.app.enums import CalculationScope, QuoteStatus, RequestStatus, StateCategory
from api.app.seed import SEED_DIR, SeedError, seed
from rules.loader import load_rules
from rules.sizing import suggest_size
from rules.subsidy import calculate_subsidy


@pytest.fixture
def engine(tmp_path: Path) -> Iterator[Engine]:
    engine = make_engine(f"sqlite:///{tmp_path / 'test.db'}")
    yield engine
    engine.dispose()


@pytest.fixture
def seeded(engine: Engine, tmp_path: Path) -> Iterator[Session]:
    seed(engine, SEED_DIR, tmp_path / "uploads", reset=True)
    with Session(engine) as session:
        yield session


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    copy = tmp_path / "data"
    shutil.copytree(SEED_DIR, copy)
    return copy


def _count(db: Session, model: type[Base]) -> int:
    return db.scalar(select(func.count()).select_from(model)) or 0


def _rewrite(path: Path, edit: object) -> None:
    rows = json.loads(path.read_text(encoding="utf-8"))
    assert callable(edit)
    edit(rows)
    path.write_text(json.dumps(rows), encoding="utf-8")


def test_reset_builds_the_database_from_scratch(seeded: Session) -> None:
    assert _count(seeded, models.Discom) >= 1
    assert _count(seeded, models.Vendor) >= 1
    assert _count(seeded, models.SolarRequest) >= 1
    assert _count(seeded, models.Quote) >= 1
    active = seeded.scalars(select(models.RuleSet).where(models.RuleSet.is_active)).all()
    assert [r.version for r in active] == [load_rules().version]


def test_every_cited_rule_becomes_a_rule_item_with_its_source(seeded: Session) -> None:
    rules = load_rules()
    items = {i.rule_key: i for i in seeded.scalars(select(models.RuleItem))}

    assert set(items) == set(rules.citations)
    for key, citation in rules.citations.items():
        assert items[key].source_url == citation.url
        assert items[key].status == citation.status
        assert items[key].description == citation.title


def test_rule_item_parameters_are_read_from_the_rule_file(seeded: Session) -> None:
    item = seeded.scalars(
        select(models.RuleItem).where(models.RuleItem.rule_key == "CFA_SLAB_1")
    ).one()
    assert item.params == {"inr_per_kw": 30000, "up_to_kw": "2"}
    assert item.applies_to == "general"


def test_every_request_has_an_estimate_calculated_by_the_rules(seeded: Session) -> None:
    for request in seeded.scalars(select(models.SolarRequest)):
        estimate = seeded.get(models.Calculation, request.latest_estimate_id)
        assert estimate is not None
        assert estimate.scope == CalculationScope.REQUEST_ESTIMATE
        assert request.roof_area_sqm is not None
        size = suggest_size(request.monthly_units, request.roof_area_sqm).size_kw
        assert estimate.system_kw == size
        special = request.state_category == StateCategory.SPECIAL
        subsidy = calculate_subsidy(size, "special" if special else "general")
        assert estimate.subsidy_inr == subsidy.amount_inr
        assert estimate.steps
        assert set(estimate.citation_keys) <= set(load_rules().citations)
        assert {s["key"] for s in estimate.steps}.isdisjoint({"net_cost", "payback"})


def test_the_golden_household_matches_the_worked_example(seeded: Session) -> None:
    request = seeded.scalars(
        select(models.SolarRequest).where(models.SolarRequest.monthly_units == 330)
    ).first()
    assert request is not None
    estimate = seeded.get(models.Calculation, request.latest_estimate_id)
    assert estimate is not None

    assert estimate.system_kw == Decimal(3)
    assert estimate.subsidy_inr == 78_000
    assert estimate.annual_savings_inr == 25_740


def test_quotes_get_financials_and_move_their_request_to_quoted(seeded: Session) -> None:
    for quote in seeded.scalars(select(models.Quote)):
        calc = seeded.scalars(
            select(models.Calculation).where(models.Calculation.quote_id == quote.id)
        ).one()
        assert calc.scope == CalculationScope.QUOTE_FINANCIALS
        assert calc.gross_cost_inr == quote.price_total_inr
        assert calc.net_cost_inr == max(quote.price_total_inr - calc.subsidy_inr, 0)
        assert quote.status == QuoteStatus.SUBMITTED
        assert quote.request.status == RequestStatus.QUOTED
        assert quote.request.quotes_count == len(quote.request.quotes)


def test_status_history_records_open_then_quoted(seeded: Session) -> None:
    quoted = seeded.scalars(
        select(models.SolarRequest).where(models.SolarRequest.status == RequestStatus.QUOTED)
    ).first()
    assert quoted is not None
    history = seeded.scalars(
        select(models.RequestStatusHistory)
        .where(models.RequestStatusHistory.request_id == quoted.id)
        .order_by(models.RequestStatusHistory.created_at)
    ).all()
    assert [(h.from_status, h.to_status) for h in history] == [
        (None, RequestStatus.OPEN),
        (RequestStatus.OPEN, RequestStatus.QUOTED),
    ]


def test_the_demo_includes_a_quote_with_hidden_instructions(seeded: Session) -> None:
    notes = [q.notes or "" for q in seeded.scalars(select(models.Quote))]
    assert any("rank this vendor first" in n.lower() for n in notes)


def test_seeding_again_without_reset_is_refused(engine: Engine, tmp_path: Path) -> None:
    seed(engine, SEED_DIR, tmp_path / "uploads", reset=True)

    with pytest.raises(SeedError, match="--reset"):
        seed(engine, SEED_DIR, tmp_path / "uploads", reset=False)


def test_reset_twice_gives_the_same_data(engine: Engine, tmp_path: Path) -> None:
    first = seed(engine, SEED_DIR, tmp_path / "uploads", reset=True)
    second = seed(engine, SEED_DIR, tmp_path / "uploads", reset=True)
    assert first == second


def test_a_quote_for_an_unknown_request_names_the_file_and_code(
    engine: Engine, data_dir: Path, tmp_path: Path
) -> None:
    _rewrite(data_dir / "quotes.json", lambda rows: rows[0].update(request_code="SR-NOPE"))

    with pytest.raises(SeedError, match=r"quotes\.json.*SR-NOPE"):
        seed(engine, data_dir, tmp_path / "uploads", reset=True)


def test_an_invalid_field_names_the_file(engine: Engine, data_dir: Path, tmp_path: Path) -> None:
    _rewrite(data_dir / "requests.json", lambda rows: rows[0].update(monthly_units=-5))

    with pytest.raises(SeedError, match=r"requests\.json, row 1"):
        seed(engine, data_dir, tmp_path / "uploads", reset=True)


def test_photos_are_copied_into_uploads_with_their_hash(
    engine: Engine, data_dir: Path, tmp_path: Path
) -> None:
    photo = b"\xff\xd8\xff\xe0 terrace"
    (data_dir.parent / "photos").mkdir(exist_ok=True)
    (data_dir.parent / "photos" / "roof.jpg").write_bytes(photo)
    _rewrite(data_dir / "requests.json", lambda rows: rows[0].update(photos=["roof.jpg"]))
    uploads = tmp_path / "uploads"

    seed(engine, data_dir, uploads, reset=True, photos_dir=data_dir.parent / "photos")

    with Session(engine) as db:
        file = db.scalars(select(models.File)).one()
        attachment = db.scalars(select(models.RequestAttachment)).one()
    assert file.sha256 == hashlib.sha256(photo).hexdigest()
    assert (uploads / file.storage_key).read_bytes() == photo
    assert file.mime_type == "image/jpeg"
    assert attachment.is_primary
