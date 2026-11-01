"""The vendor map: open requests in the viewport and the service radius (work plan 3.4)."""

import uuid
from collections.abc import Callable
from datetime import timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.app import models
from api.app.db import utcnow
from api.app.enums import RequestStatus, Role
from api.app.services.geo import approx_point
from api.tests.conftest import MakeUser

Auth = Callable[[models.User], dict[str, str]]
GUJARAT = "68,20,75,25"
PLACES = {
    "ahmedabad": (23.0225, 72.5714),
    "gandhinagar": (23.2156, 72.6369),
    "vadodara": (22.3072, 73.1812),
    "mumbai": (19.0760, 72.8777),
}


@pytest.fixture
def household(client: TestClient, make_user: MakeUser, auth: Auth) -> dict[str, str]:
    return auth(make_user())


@pytest.fixture
def vendor(db: Session, make_user: MakeUser) -> models.User:
    user = make_user(Role.VENDOR)
    assert user.vendor is not None
    user.vendor.base_lat, user.vendor.base_lng = 23.0365, 72.5611
    user.vendor.service_radius_km = 50
    db.commit()
    return user


def _post(client: TestClient, headers: dict[str, str], place: str, **extra: object) -> str:
    lat, lng = PLACES[place]
    body = {
        "lat": lat,
        "lng": lng,
        "location_source": "map_pin",
        "monthly_units": 330,
        "budget_inr": 200000,
        "roof_area_sqm": "40",
        **extra,
    }
    response = client.post("/requests", json=body, headers=headers)
    assert response.status_code == 201, response.json()
    return str(response.json()["id"])


def _pins(client: TestClient, headers: dict[str, str], **params: object) -> Any:
    response = client.get("/requests/open", params={"bbox": GUJARAT, **params}, headers=headers)
    assert response.status_code == 200, response.json()
    return response.json()


def _set_status(db: Session, request_id: str, status: RequestStatus) -> None:
    request = db.get(models.SolarRequest, uuid.UUID(request_id))
    assert request is not None
    request.status = status
    db.commit()


def test_pins_inside_the_view_and_radius_are_shown_newest_first(
    client: TestClient, household: dict[str, str], vendor: models.User, auth: Auth
) -> None:
    ahmedabad = _post(client, household, "ahmedabad")
    gandhinagar = _post(client, household, "gandhinagar")

    page = _pins(client, auth(vendor))

    assert [p["id"] for p in page["items"]] == [gandhinagar, ahmedabad]
    assert page["next_cursor"] is None


def test_requests_beyond_the_service_radius_are_hidden(
    client: TestClient, household: dict[str, str], vendor: models.User, auth: Auth
) -> None:
    near = _post(client, household, "ahmedabad")
    _post(client, household, "vadodara")

    assert [p["id"] for p in _pins(client, auth(vendor))["items"]] == [near]


def test_requests_outside_the_view_are_hidden(
    client: TestClient, household: dict[str, str], vendor: models.User, auth: Auth
) -> None:
    near = _post(client, household, "ahmedabad")
    _post(client, household, "gandhinagar")

    only_ahmedabad = "72.5,22.9,72.6,23.1"
    page = _pins(client, auth(vendor), bbox=only_ahmedabad)
    assert [p["id"] for p in page["items"]] == [near]


def test_pins_carry_the_rounded_location_and_the_estimate(
    client: TestClient, household: dict[str, str], vendor: models.User, auth: Auth
) -> None:
    _post(client, household, "ahmedabad", district="Ahmedabad")

    pin = _pins(client, auth(vendor))["items"][0]

    assert (pin["approx_lat"], pin["approx_lng"]) == approx_point(*PLACES["ahmedabad"])
    assert not {"lat", "lng", "address_text"} & set(pin)
    assert pin["recommended_kw"] == "3.00"
    assert pin["district"] == "Ahmedabad"
    assert 1 < float(pin["distance_km"]) < 3
    assert pin["request_code"].startswith("SR-")


@pytest.mark.parametrize(
    "status", [RequestStatus.ACCEPTED, RequestStatus.CANCELLED, RequestStatus.EXPIRED]
)
def test_closed_requests_are_not_on_the_map(
    client: TestClient,
    db: Session,
    household: dict[str, str],
    vendor: models.User,
    auth: Auth,
    status: RequestStatus,
) -> None:
    request_id = _post(client, household, "ahmedabad")
    _set_status(db, request_id, status)

    assert _pins(client, auth(vendor))["items"] == []


def test_quoted_requests_stay_on_the_map(
    client: TestClient, db: Session, household: dict[str, str], vendor: models.User, auth: Auth
) -> None:
    request_id = _post(client, household, "ahmedabad")
    _set_status(db, request_id, RequestStatus.QUOTED)

    assert [p["id"] for p in _pins(client, auth(vendor))["items"]] == [request_id]


def test_requests_past_their_expiry_date_are_hidden(
    client: TestClient, db: Session, household: dict[str, str], vendor: models.User, auth: Auth
) -> None:
    request_id = _post(client, household, "ahmedabad")
    request = db.get(models.SolarRequest, uuid.UUID(request_id))
    assert request is not None
    request.expires_at = utcnow() - timedelta(minutes=1)
    db.commit()

    assert _pins(client, auth(vendor))["items"] == []


def test_a_vendor_without_a_base_sees_the_whole_view(
    client: TestClient, household: dict[str, str], make_user: MakeUser, auth: Auth
) -> None:
    _post(client, household, "ahmedabad")
    _post(client, household, "vadodara")

    page = _pins(client, auth(make_user(Role.VENDOR)))

    assert len(page["items"]) == 2
    assert {p["distance_km"] for p in page["items"]} == {None}


def test_the_map_pages_with_a_cursor(
    client: TestClient, household: dict[str, str], vendor: models.User, auth: Auth
) -> None:
    ids = [_post(client, household, "ahmedabad") for _ in range(3)]

    first = _pins(client, auth(vendor), limit=2)
    second = _pins(client, auth(vendor), limit=2, cursor=first["next_cursor"])

    assert [p["id"] for p in first["items"] + second["items"]] == ids[::-1]
    assert second["next_cursor"] is None


def test_paging_skips_far_requests_without_short_pages(
    client: TestClient, household: dict[str, str], vendor: models.User, auth: Auth
) -> None:
    near = [_post(client, household, "ahmedabad") for _ in range(2)]
    for _ in range(3):
        _post(client, household, "vadodara")

    page = _pins(client, auth(vendor), limit=2)
    assert [p["id"] for p in page["items"]] == near[::-1]


def test_households_cannot_browse_the_map(client: TestClient, household: dict[str, str]) -> None:
    response = client.get("/requests/open", params={"bbox": GUJARAT}, headers=household)
    assert response.status_code == 403
