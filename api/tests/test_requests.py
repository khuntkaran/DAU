"""Creating and reading solar requests (work plan 3.3)."""

import uuid
from collections.abc import Callable
from datetime import timedelta
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.app import models
from api.app.config import Settings
from api.app.enums import QuoteSource, QuoteStatus, RequestStatus, Role, StateCategory
from api.app.services.geo import haversine_km
from api.tests.conftest import MakeUser

Auth = Callable[[models.User], dict[str, str]]
GOLDEN: dict[str, Any] = {
    "lat": 23.0225,
    "lng": 72.5714,
    "location_source": "map_pin",
    "address_text": "12 Demo Society",
    "monthly_units": 330,
    "budget_inr": 200000,
    "roof_area_sqm": "40",
    "roof_type": "rcc_flat",
}


@pytest.fixture(autouse=True)
def _uploads_in_tmp(settings: Settings, tmp_path: Path) -> None:
    settings.upload_dir = tmp_path / "uploads"


def _create(client: TestClient, headers: dict[str, str], **changes: object) -> Any:
    return client.post("/requests", json={**GOLDEN, **changes}, headers=headers)


def _photo(client: TestClient, headers: dict[str, str], purpose: str = "terrace_photo") -> str:
    out = BytesIO()
    Image.new("RGB", (8, 8), (uuid.uuid4().int % 255, 0, 0)).save(out, "JPEG")
    response = client.post(
        "/uploads",
        data={"purpose": purpose},
        files={"file": ("p.jpg", out.getvalue(), "image/jpeg")},
        headers=headers,
    )
    assert response.status_code == 201, response.json()
    return str(response.json()["id"])


def _code(response: Any) -> str:
    return str(response.json()["error"]["code"])


# --- Create ---------------------------------------------------------------------------------


def test_creating_a_request_returns_the_calculated_estimate(
    client: TestClient, make_user: MakeUser, auth: Auth
) -> None:
    response = _create(client, auth(make_user()))

    assert response.status_code == 201
    body = response.json()
    assert body["view"] == "owner"
    assert body["status"] == "open"
    assert body["request_code"].startswith("SR-")
    estimate = body["estimate"]
    assert (estimate["system_kw"], estimate["subsidy_inr"]) == ("3.00", 78000)
    assert estimate["annual_savings_inr"] == 25740
    assert estimate["rule_version"] == "pm_surya_ghar_v2024_03"
    assert [s["key"] for s in estimate["steps"]][:2] == ["raw_kw", "wanted_kw"]
    cited = {c["key"]: c for c in estimate["citations"]}
    assert cited["CFA_SLAB_1"]["url"].startswith("https://")
    assert cited["GENERATION"]["status"] == "assumption"
    assert {s["rule_key"] for s in estimate["steps"] if s["rule_key"]} <= set(cited)


def test_the_request_is_stored_with_its_history_and_expiry(
    client: TestClient, db: Session, make_user: MakeUser, auth: Auth
) -> None:
    user = make_user()
    _create(client, auth(user))

    request = db.scalars(select(models.SolarRequest)).one()
    assert request.household_id == user.id
    assert request.expires_at is not None
    assert request.submitted_at is not None
    assert request.expires_at - request.submitted_at == timedelta(days=30)
    history = db.scalars(select(models.RequestStatusHistory)).one()
    assert (history.from_status, history.to_status, history.changed_by) == (
        None,
        RequestStatus.OPEN,
        user.id,
    )


def test_request_codes_count_up(client: TestClient, make_user: MakeUser, auth: Auth) -> None:
    headers = auth(make_user())
    first = _create(client, headers).json()["request_code"]
    second = _create(client, headers).json()["request_code"]

    assert int(second[-6:]) == int(first[-6:]) + 1


def test_rules_are_loaded_into_an_empty_database_on_first_use(
    client: TestClient, db: Session, make_user: MakeUser, auth: Auth
) -> None:
    _create(client, auth(make_user()))
    _create(client, auth(make_user()))

    assert len(db.scalars(select(models.RuleSet)).all()) == 1
    assert len(db.scalars(select(models.RuleItem)).all()) == 11


def test_a_special_category_discom_gets_the_special_subsidy(
    client: TestClient, db: Session, make_user: MakeUser, auth: Auth
) -> None:
    discom = models.Discom(
        code="HILL", name="Hill DISCOM", state="Hill State", state_category=StateCategory.SPECIAL
    )
    db.add(discom)
    db.commit()

    body = _create(client, auth(make_user()), discom_id=str(discom.id)).json()

    assert body["state_category"] == "special"
    assert body["estimate"]["subsidy_inr"] == 85800


def test_an_unknown_discom_is_rejected(client: TestClient, make_user: MakeUser, auth: Auth) -> None:
    response = _create(client, auth(make_user()), discom_id=str(uuid.uuid4()))
    assert (response.status_code, _code(response)) == (422, "unknown_discom")


def test_photos_are_attached_in_order(client: TestClient, make_user: MakeUser, auth: Auth) -> None:
    headers = auth(make_user())
    first, second = _photo(client, headers), _photo(client, headers)

    body = _create(client, headers, photo_file_ids=[first, second]).json()

    attachments = body["attachments"]
    assert [a["file_id"] for a in attachments] == [first, second]
    assert [a["is_primary"] for a in attachments] == [True, False]
    assert attachments[0]["url"] == f"/files/{first}"


@pytest.mark.parametrize("problem", ["someone_elses", "a_bill", "missing", "repeated"])
def test_bad_photo_ids_are_rejected(
    client: TestClient, make_user: MakeUser, auth: Auth, problem: str
) -> None:
    headers = auth(make_user())
    ids = {
        "someone_elses": [_photo(client, auth(make_user()))],
        "a_bill": [_photo(client, headers, "electricity_bill")],
        "missing": [str(uuid.uuid4())],
        "repeated": [_photo(client, headers)] * 2,
    }[problem]

    response = _create(client, headers, photo_file_ids=ids)
    assert (response.status_code, _code(response)) == (422, "invalid_attachment")


def test_a_bill_can_be_attached_as_a_bill(
    client: TestClient, make_user: MakeUser, auth: Auth
) -> None:
    headers = auth(make_user())
    bill = _photo(client, headers, "electricity_bill")

    body = _create(client, headers, bill_file_id=bill).json()
    assert [(a["file_id"], a["kind"]) for a in body["attachments"]] == [(bill, "electricity_bill")]


def test_a_vendor_cannot_create_a_request(
    client: TestClient, make_user: MakeUser, auth: Auth
) -> None:
    response = _create(client, auth(make_user(Role.VENDOR)))
    assert (response.status_code, _code(response)) == (403, "forbidden")


# --- My requests ----------------------------------------------------------------------------


def test_my_requests_lists_only_mine_newest_first(
    client: TestClient, make_user: MakeUser, auth: Auth
) -> None:
    me, other = auth(make_user()), auth(make_user())
    older = _create(client, me, monthly_units=150).json()["id"]
    newer = _create(client, me).json()["id"]
    _create(client, other)

    page = client.get("/requests/mine", headers=me).json()

    assert [r["id"] for r in page["items"]] == [newer, older]
    assert page["items"][0]["system_kw"] == "3.00"
    assert page["next_cursor"] is None


def test_my_requests_pages_with_a_cursor(
    client: TestClient, make_user: MakeUser, auth: Auth
) -> None:
    me = auth(make_user())
    ids = [_create(client, me).json()["id"] for _ in range(3)]

    first = client.get("/requests/mine", params={"limit": 2}, headers=me).json()
    second = client.get(
        "/requests/mine", params={"limit": 2, "cursor": first["next_cursor"]}, headers=me
    ).json()

    assert [r["id"] for r in first["items"] + second["items"]] == ids[::-1]
    assert second["next_cursor"] is None


def test_a_bad_cursor_is_rejected(client: TestClient, make_user: MakeUser, auth: Auth) -> None:
    response = client.get("/requests/mine", params={"cursor": "nope"}, headers=auth(make_user()))
    assert (response.status_code, _code(response)) == (422, "invalid_cursor")


# --- One request ----------------------------------------------------------------------------


def test_the_owner_sees_the_exact_location(
    client: TestClient, make_user: MakeUser, auth: Auth
) -> None:
    headers = auth(make_user())
    created = _create(client, headers).json()

    body = client.get(f"/requests/{created['id']}", headers=headers).json()

    assert body["view"] == "owner"
    assert (body["lat"], body["lng"], body["address_text"]) == (23.0225, 72.5714, "12 Demo Society")


def test_another_household_gets_not_found(
    client: TestClient, make_user: MakeUser, auth: Auth
) -> None:
    created = _create(client, auth(make_user())).json()

    response = client.get(f"/requests/{created['id']}", headers=auth(make_user()))
    assert response.status_code == 404


def _vendor_with_base(db: Session, make_user: MakeUser) -> models.User:
    user = make_user(Role.VENDOR)
    assert user.vendor is not None
    user.vendor.base_lat, user.vendor.base_lng = 23.0365, 72.5611
    db.commit()
    return user


def test_a_vendor_sees_an_open_request_without_household_details(
    client: TestClient, db: Session, make_user: MakeUser, auth: Auth
) -> None:
    headers = auth(make_user())
    bill = _photo(client, headers, "electricity_bill")
    photo = _photo(client, headers)
    created = _create(client, headers, photo_file_ids=[photo], bill_file_id=bill).json()

    body = client.get(f"/requests/{created['id']}", headers=auth(_vendor_with_base(db, make_user)))

    assert body.status_code == 200
    view = body.json()
    assert view["view"] == "vendor"
    assert not {"lat", "lng", "address_text", "pincode", "notes"} & set(view)
    moved = haversine_km(23.0225, 72.5714, view["approx_lat"], view["approx_lng"])
    assert Decimal("0.05") < moved < Decimal("0.6")
    assert Decimal(view["distance_km"]) > 0
    assert [a["file_id"] for a in view["attachments"]] == [photo]
    assert (view["my_quote_id"], view["contact"]) == (None, None)


def test_nearby_requests_round_to_the_same_point(
    client: TestClient, db: Session, make_user: MakeUser, auth: Auth
) -> None:
    headers = auth(make_user())
    a = _create(client, headers, lat=23.02251, lng=72.57141).json()["id"]
    b = _create(client, headers, lat=23.02249, lng=72.57139).json()["id"]
    vendor = auth(_vendor_with_base(db, make_user))

    views = [client.get(f"/requests/{i}", headers=vendor).json() for i in (a, b)]
    assert {(v["approx_lat"], v["approx_lng"]) for v in views} == {
        (views[0]["approx_lat"], views[0]["approx_lng"])
    }


def _quote(db: Session, request_id: str, vendor: models.User, status: QuoteStatus) -> None:
    assert vendor.vendor is not None
    db.add(
        models.Quote(
            quote_code=f"Q-2026-{uuid.uuid4().int % 1_000_000:06d}",
            request_id=uuid.UUID(request_id),
            vendor_id=vendor.vendor.id,
            status=status,
            system_kw=Decimal(3),
            price_total_inr=180000,
            gst_included=True,
            panel_brand="P",
            dcr_compliant=True,
            inverter_brand="I",
            timeline_days=20,
            source=QuoteSource.FORM,
        )
    )


def test_a_closed_request_is_hidden_from_vendors_who_did_not_quote(
    client: TestClient, db: Session, make_user: MakeUser, auth: Auth
) -> None:
    created = _create(client, auth(make_user())).json()
    request = db.get(models.SolarRequest, uuid.UUID(created["id"]))
    assert request is not None
    request.status = RequestStatus.ACCEPTED
    db.commit()

    response = client.get(f"/requests/{created['id']}", headers=auth(make_user(Role.VENDOR)))
    assert response.status_code == 404


def test_the_accepted_vendor_gets_the_household_contact(
    client: TestClient, db: Session, make_user: MakeUser, auth: Auth
) -> None:
    household = make_user()
    created = _create(client, auth(household)).json()
    winner, loser = make_user(Role.VENDOR), make_user(Role.VENDOR)
    _quote(db, created["id"], winner, QuoteStatus.ACCEPTED)
    _quote(db, created["id"], loser, QuoteStatus.REJECTED)
    request = db.get(models.SolarRequest, uuid.UUID(created["id"]))
    assert request is not None
    request.status = RequestStatus.ACCEPTED
    db.commit()

    won = client.get(f"/requests/{created['id']}", headers=auth(winner)).json()
    lost = client.get(f"/requests/{created['id']}", headers=auth(loser)).json()

    assert won["contact"] == {
        "full_name": household.full_name,
        "phone": household.phone,
        "lat": 23.0225,
        "lng": 72.5714,
        "address_text": "12 Demo Society",
    }
    assert won["my_quote_id"] is not None
    assert lost["contact"] is None


def test_an_unknown_request_is_not_found(
    client: TestClient, make_user: MakeUser, auth: Auth
) -> None:
    response = client.get(f"/requests/{uuid.uuid4()}", headers=auth(make_user()))
    assert (response.status_code, _code(response)) == (404, "not_found")
