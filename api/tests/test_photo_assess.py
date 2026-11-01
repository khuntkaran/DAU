"""Terrace photo assessment (work plan 4.2). Gemini sees the roof; code does the arithmetic."""

import uuid
from collections.abc import Callable
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from PIL import Image as PILImage
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.app import models
from api.app.config import Settings
from api.app.enums import JobType
from api.app.llm.base import Image, Part, Text
from api.app.llm.providers.fake import FakeProvider
from api.tests.conftest import MakeUser

Auth = Callable[[models.User], dict[str, str]]
ROOF: dict[str, Any] = {
    "is_roof": True,
    "usable_fraction": 0.65,
    "shade_risk": "low",
    "summary": "Flat RCC roof with a water tank in one corner and a staircase room.",
    "obstructions": [
        {
            "type": "water_tank",
            "x": 0.1,
            "y": 0.1,
            "w": 0.2,
            "h": 0.2,
            "severity": "medium",
            "confidence": 0.9,
        },
        {
            "type": "staircase_room",
            "x": 0.6,
            "y": 0.5,
            "w": 0.3,
            "h": 0.4,
            "severity": "high",
            "confidence": 0.8,
        },
    ],
}


@pytest.fixture(autouse=True)
def _setup(settings: Settings, tmp_path: Path, fake_ai: FakeProvider) -> None:
    settings.upload_dir = tmp_path / "uploads"
    fake_ai.scripts = {"photo_assess": lambda parts: ROOF}


@pytest.fixture
def household(make_user: MakeUser, auth: Auth) -> dict[str, str]:
    return auth(make_user())


def _photo(client: TestClient, headers: dict[str, str], size: tuple[int, int] = (64, 48)) -> str:
    out = BytesIO()
    PILImage.new("RGB", size, (uuid.uuid4().int % 255, 90, 40)).save(out, "JPEG")
    response = client.post(
        "/uploads",
        data={"purpose": "terrace_photo"},
        files={"file": ("roof.jpg", out.getvalue(), "image/jpeg")},
        headers=headers,
    )
    assert response.status_code == 201
    return str(response.json()["id"])


def _create(client: TestClient, headers: dict[str, str], photos: list[str]) -> Any:
    body = {
        "lat": 23.0225,
        "lng": 72.5714,
        "location_source": "map_pin",
        "address_text": "12 Private Lane",
        "monthly_units": 330,
        "budget_inr": 200000,
        "roof_area_sqm": "40",
        "photo_file_ids": photos,
    }
    response = client.post("/requests", json=body, headers=headers)
    assert response.status_code == 201, response.json()
    return response.json()


def _view(client: TestClient, request_id: str, headers: dict[str, str]) -> Any:
    return client.get(f"/requests/{request_id}", headers=headers).json()


def test_the_new_request_shows_the_assessment_as_pending(
    client: TestClient, household: dict[str, str]
) -> None:
    created = _create(client, household, [_photo(client, household)])

    assessment = created["roof_assessment"]
    assert assessment["status"] == "pending"
    assert assessment["obstructions"] == []


def test_the_assessment_finds_obstructions_and_resizes_the_estimate(
    client: TestClient, household: dict[str, str]
) -> None:
    created = _create(client, household, [_photo(client, household)])
    assert created["estimate"]["system_kw"] == "3.00"

    view = _view(client, created["id"], household)

    assessment = view["roof_assessment"]
    assert assessment["status"] == "done"
    assert [o["obstruction_type"] for o in assessment["obstructions"]] == [
        "water_tank",
        "staircase_room",
    ]
    assert assessment["obstructions"][0]["bbox_w"] == "0.200"
    assert (assessment["usable_fraction"], assessment["usable_area_sqm"]) == ("0.65", "26.00")
    assert assessment["max_kw_by_area"] == "2.50"
    assert assessment["shade_risk"] == "low"
    assert "water tank" in assessment["summary"]

    estimate = view["estimate"]
    assert (estimate["system_kw"], estimate["roof_cap_kw"]) == ("2.50", "2.50")
    assert estimate["subsidy_inr"] == 69000
    usable = next(s for s in estimate["steps"] if s["key"] == "usable_area")
    assert (usable["formula"], usable["rule_key"]) == ("40 m² × 0.65 usable", None)
    assert "USABLE_FRACTION" not in {c["key"] for c in estimate["citations"]}


def test_the_household_can_poll_the_job(
    client: TestClient, db: Session, household: dict[str, str]
) -> None:
    _create(client, household, [_photo(client, household)])
    job = db.scalars(
        select(models.AiJob).where(models.AiJob.job_type == JobType.PHOTO_ASSESS)
    ).one()

    polled = client.get(f"/jobs/{job.id}", headers=household).json()

    assert polled["status"] == "succeeded"
    assert polled["output"]["kind"] == "photo_assess"
    assert polled["output"]["max_kw_by_area"] == "2.50"


def test_gemini_gets_a_small_image_and_no_personal_details(
    client: TestClient, household: dict[str, str], fake_ai: FakeProvider
) -> None:
    seen: list[list[Part]] = []

    def capture(parts: list[Part]) -> dict[str, Any]:
        seen.append(parts)
        return ROOF

    fake_ai.scripts = {"photo_assess": capture}
    _create(client, household, [_photo(client, household, size=(3000, 2000))])

    images = [p for p in seen[0] if isinstance(p, Image)]
    assert len(images) == 1
    with PILImage.open(BytesIO(images[0].data)) as sent:
        assert max(sent.size) == 1024
    text = " ".join(p.text for p in seen[0] if isinstance(p, Text))
    assert "40" in text
    assert "Private Lane" not in text


def test_a_request_without_photos_has_no_assessment(
    client: TestClient, db: Session, household: dict[str, str]
) -> None:
    created = _create(client, household, [])

    assert created["roof_assessment"] is None
    assert db.scalars(select(models.AiJob)).all() == []


def test_when_ai_is_down_the_estimate_stays_and_the_assessment_fails(
    client: TestClient, household: dict[str, str], fake_ai: FakeProvider
) -> None:
    fake_ai.scripts = {}
    created = _create(client, household, [_photo(client, household)])

    view = _view(client, created["id"], household)

    assert view["roof_assessment"]["status"] == "failed"
    assert view["estimate"]["system_kw"] == "3.00"
    assert view["status"] == "open"


def test_a_photo_that_is_not_a_roof_changes_nothing(
    client: TestClient, household: dict[str, str], fake_ai: FakeProvider
) -> None:
    fake_ai.scripts = {"photo_assess": lambda parts: {**ROOF, "is_roof": False, "obstructions": []}}
    created = _create(client, household, [_photo(client, household)])

    view = _view(client, created["id"], household)

    assessment = view["roof_assessment"]
    assert assessment["status"] == "failed"
    assert "roof" in assessment["summary"].lower()
    assert view["estimate"]["system_kw"] == "3.00"


def test_an_out_of_range_answer_is_rejected(
    client: TestClient, household: dict[str, str], fake_ai: FakeProvider
) -> None:
    fake_ai.scripts = {"photo_assess": lambda parts: {**ROOF, "usable_fraction": 1.4}}
    created = _create(client, household, [_photo(client, household)])

    assert _view(client, created["id"], household)["roof_assessment"]["status"] == "failed"


def test_the_same_photo_is_assessed_once(
    client: TestClient, db: Session, household: dict[str, str], fake_ai: FakeProvider
) -> None:
    calls: list[int] = []

    def counted(parts: list[Part]) -> dict[str, Any]:
        calls.append(1)
        return ROOF

    fake_ai.scripts = {"photo_assess": counted}
    photo = _photo(client, household)
    first = _create(client, household, [photo])
    second = _create(client, household, [photo])

    assert len(calls) == 1
    for created in (first, second):
        view = _view(client, created["id"], household)
        assert view["roof_assessment"]["status"] == "done"
        assert view["estimate"]["system_kw"] == "2.50"


def test_vendors_see_the_assessment_too(
    client: TestClient, db: Session, household: dict[str, str], make_user: MakeUser, auth: Auth
) -> None:
    from api.app.enums import Role

    created = _create(client, household, [_photo(client, household)])

    view = _view(client, created["id"], auth(make_user(Role.VENDOR)))
    assert view["roof_assessment"]["status"] == "done"
    assert Decimal(view["estimate"]["system_kw"]) == Decimal("2.5")
