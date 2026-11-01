"""Accepting a quote (work plan 3.6): one transaction, one winner, even under a race."""

import threading
import uuid
from collections.abc import Callable
from datetime import timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from api.app import models
from api.app.db import utcnow
from api.app.enums import QuoteStatus, RequestStatus, Role
from api.app.errors import ApiError
from api.app.services.quotes import accept_quote
from api.tests.conftest import MakeUser

Auth = Callable[[models.User], dict[str, str]]
QUOTE: dict[str, Any] = {
    "system_kw": "3",
    "price_total_inr": 185000,
    "gst_included": True,
    "panel_brand": "P",
    "dcr_compliant": True,
    "inverter_brand": "I",
    "timeline_days": 21,
}


@pytest.fixture
def household(make_user: MakeUser) -> models.User:
    return make_user()


@pytest.fixture
def vendors(db: Session, make_user: MakeUser) -> list[models.User]:
    users = [make_user(Role.VENDOR) for _ in range(3)]
    for n, user in enumerate(users):
        assert user.vendor is not None
        user.vendor.contact_phone = f"+9198000000{n:02d}"
        user.vendor.contact_email = f"v{n}@example.test"
    db.commit()
    return users


@pytest.fixture
def quote_ids(
    client: TestClient, household: models.User, vendors: list[models.User], auth: Auth
) -> list[str]:
    body = {
        "lat": 23.0225,
        "lng": 72.5714,
        "location_source": "map_pin",
        "monthly_units": 330,
        "budget_inr": 200000,
        "roof_area_sqm": "40",
    }
    request_id = client.post("/requests", json=body, headers=auth(household)).json()["id"]
    ids = []
    for vendor in vendors:
        response = client.post(f"/requests/{request_id}/quotes", json=QUOTE, headers=auth(vendor))
        assert response.status_code == 201
        ids.append(str(response.json()["quote"]["id"]))
    return ids


def _accept(client: TestClient, quote_id: str, headers: dict[str, str]) -> Any:
    return client.post(f"/quotes/{quote_id}/accept", headers=headers)


def _code(response: Any) -> str:
    return str(response.json()["error"]["code"])


def test_accepting_settles_every_quote_in_one_go(
    client: TestClient,
    db: Session,
    household: models.User,
    vendors: list[models.User],
    quote_ids: list[str],
    auth: Auth,
) -> None:
    response = _accept(client, quote_ids[1], auth(household))

    assert response.status_code == 200
    body = response.json()
    assert body["accepted_quote_id"] == quote_ids[1]
    assert sorted(body["rejected_quote_ids"]) == sorted([quote_ids[0], quote_ids[2]])
    assert body["request_status"] == "accepted"
    winner = vendors[1].vendor
    assert winner is not None
    assert body["vendor_contact"] == {
        "company_name": winner.company_name,
        "contact_person": winner.contact_person,
        "contact_phone": winner.contact_phone,
        "contact_email": winner.contact_email,
    }

    db.expire_all()
    statuses = {str(q.id): q.status for q in db.scalars(select(models.Quote))}
    assert statuses == {
        quote_ids[0]: QuoteStatus.REJECTED,
        quote_ids[1]: QuoteStatus.ACCEPTED,
        quote_ids[2]: QuoteStatus.REJECTED,
    }
    request = db.scalars(select(models.SolarRequest)).one()
    assert request.status == RequestStatus.ACCEPTED
    assert str(request.accepted_quote_id) == quote_ids[1]
    assert request.closed_at is not None
    last = db.scalars(
        select(models.RequestStatusHistory).order_by(models.RequestStatusHistory.created_at.desc())
    ).first()
    assert last is not None
    assert (last.from_status, last.to_status, last.changed_by) == (
        RequestStatus.QUOTED,
        RequestStatus.ACCEPTED,
        household.id,
    )
    decided = db.get(models.Quote, uuid.UUID(quote_ids[1]))
    assert decided is not None
    assert decided.decided_at is not None


def test_only_the_winning_vendor_gets_the_household_contact(
    client: TestClient,
    household: models.User,
    vendors: list[models.User],
    quote_ids: list[str],
    auth: Auth,
) -> None:
    _accept(client, quote_ids[0], auth(household))

    mine = [client.get("/quotes/mine", headers=auth(v)).json()["items"][0] for v in vendors]
    assert mine[0]["contact"]["phone"] == household.phone
    assert [m["contact"] for m in mine[1:]] == [None, None]
    assert [m["status"] for m in mine] == ["accepted", "rejected", "rejected"]


def test_a_decided_request_cannot_be_accepted_again(
    client: TestClient, household: models.User, quote_ids: list[str], auth: Auth
) -> None:
    headers = auth(household)
    _accept(client, quote_ids[0], headers)

    for quote_id in quote_ids:
        response = _accept(client, quote_id, headers)
        assert (response.status_code, _code(response)) == (409, "request_not_open")


def test_a_withdrawn_quote_cannot_be_accepted(
    client: TestClient, db: Session, household: models.User, quote_ids: list[str], auth: Auth
) -> None:
    quote = db.get(models.Quote, uuid.UUID(quote_ids[0]))
    assert quote is not None
    quote.status = QuoteStatus.WITHDRAWN
    db.commit()

    response = _accept(client, quote_ids[0], auth(household))
    assert (response.status_code, _code(response)) == (409, "quote_not_available")


def test_an_expired_request_cannot_be_accepted(
    client: TestClient, db: Session, household: models.User, quote_ids: list[str], auth: Auth
) -> None:
    request = db.scalars(select(models.SolarRequest)).one()
    request.expires_at = utcnow() - timedelta(minutes=1)
    db.commit()

    response = _accept(client, quote_ids[0], auth(household))
    assert (response.status_code, _code(response)) == (409, "request_not_open")


def test_only_the_owner_can_accept(
    client: TestClient,
    make_user: MakeUser,
    vendors: list[models.User],
    quote_ids: list[str],
    auth: Auth,
) -> None:
    assert _accept(client, quote_ids[0], auth(make_user())).status_code == 404
    assert _accept(client, quote_ids[0], auth(vendors[0])).status_code == 403


def test_an_unknown_quote_is_not_found(
    client: TestClient, household: models.User, auth: Auth
) -> None:
    response = _accept(client, str(uuid.uuid4()), auth(household))
    assert (response.status_code, _code(response)) == (404, "not_found")


def test_two_accepts_at_once_have_exactly_one_winner(
    engine: Engine, household: models.User, quote_ids: list[str]
) -> None:
    """Two browser tabs accept different quotes at the same moment."""
    start = threading.Barrier(2)
    outcomes: list[str] = []
    lock = threading.Lock()

    def accept(quote_id: str) -> None:
        with Session(engine, expire_on_commit=False) as db:
            owner = db.get(models.User, household.id)
            assert owner is not None
            start.wait()
            try:
                accept_quote(db, owner, uuid.UUID(quote_id))
                result = "accepted"
            except ApiError as exc:
                result = exc.code
        with lock:
            outcomes.append(result)

    threads = [threading.Thread(target=accept, args=(q,)) for q in quote_ids[:2]]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    assert sorted(outcomes) == ["accepted", "request_not_open"]
    with Session(engine) as db:
        accepted = db.scalars(
            select(models.Quote).where(models.Quote.status == QuoteStatus.ACCEPTED)
        ).all()
        assert len(accepted) == 1
