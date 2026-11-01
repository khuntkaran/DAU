"""The API contract: every route in section 08 of the architecture, its auth, and its schemas.

These tests need no database. Behaviour tests against Postgres arrive with each endpoint.
"""

from decimal import Decimal
from typing import Any, get_args

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from api.app import schemas
from api.app.export_openapi import DEFAULT_PATH, render
from api.app.main import app
from rules.checklist import REQUIRED_INCLUSIONS
from rules.loader import load_rules

client = TestClient(app)

ROUTES = {
    ("post", "/auth/otp"),
    ("post", "/auth/verify"),
    ("post", "/uploads/presign"),
    ("post", "/voice/transcribe"),
    ("post", "/requests"),
    ("get", "/requests/mine"),
    ("get", "/requests/open"),
    ("get", "/requests/{request_id}"),
    ("post", "/requests/{request_id}/quotes"),
    ("get", "/requests/{request_id}/quotes"),
    ("post", "/requests/{request_id}/recommendation"),
    ("get", "/requests/{request_id}/recommendation"),
    ("get", "/quotes/mine"),
    ("post", "/quotes/{quote_id}/accept"),
    ("get", "/jobs/{job_id}"),
    ("get", "/events"),
    ("get", "/rules/current"),
    ("get", "/health"),
}
PUBLIC = {"/auth/otp", "/auth/verify", "/rules/current", "/health"}

REQUEST_ID = "00000000-0000-4000-8000-000000000001"
VALID_REQUEST: dict[str, Any] = {
    "location": {"lat": 23.0225, "lng": 72.5714},
    "state_category": "general",
    "monthly_units": 330,
    "budget_inr": 200000,
    "roof_area_m2": "40",
    "roof_type": "rcc_flat",
}
VALID_QUOTE: dict[str, Any] = {
    "system_kw": "3",
    "price_inr": 185000,
    "panel_brand": "Waaree",
    "panel_watt": 545,
    "dcr": True,
    "inverter_brand": "Growatt",
    "inverter_kw": "3",
    "warranty_panel_yrs": 25,
    "warranty_inverter_yrs": 10,
    "warranty_work_yrs": 5,
    "timeline_days": 21,
    "inclusions": ["net_metering_fee", "mounting_structure"],
}


def _operations() -> dict[tuple[str, str], dict[str, Any]]:
    paths: dict[str, dict[str, Any]] = app.openapi()["paths"]
    return {(m, p): op for p, ops in paths.items() for m, op in ops.items()}


def test_every_contract_route_is_published() -> None:
    assert set(_operations()) == ROUTES


@pytest.mark.parametrize(("method", "path"), sorted(ROUTES))
def test_auth_is_declared_on_every_route(method: str, path: str) -> None:
    op = _operations()[(method, path)]
    if path in PUBLIC:
        assert "security" not in op
    else:
        assert op["security"] == [{"HTTPBearer": []}]


def test_openapi_advertises_only_our_error_shape() -> None:
    schema = app.openapi()
    assert "HTTPValidationError" not in schema["components"]["schemas"]
    for (_, path), op in _operations().items():
        for status, response in op["responses"].items():
            if status.startswith(("4", "5")):
                ref = response["content"]["application/json"]["schema"]["$ref"]
                assert ref.endswith("/ErrorResponse"), (path, status)


def test_missing_token_gets_401_in_the_error_shape() -> None:
    response = client.post("/requests", json=VALID_REQUEST)

    assert response.status_code == 401
    assert response.json() == {
        "error": {"code": "unauthenticated", "message": "Sign in first.", "details": None}
    }


def test_stub_routes_answer_501_until_built() -> None:
    response = client.get(f"/jobs/{REQUEST_ID}", headers={"Authorization": "Bearer x"})

    assert response.status_code == 501
    assert response.json()["error"]["code"] == "not_implemented"


def test_invalid_body_gets_422_in_the_error_shape() -> None:
    response = client.post("/auth/otp", json={"phone": "12345"})

    assert response.status_code == 422
    body = response.json()["error"]
    assert body["code"] == "validation_error"
    assert body["details"][0]["loc"] == ["body", "phone"]


def test_rules_current_returns_the_rule_set_with_citations() -> None:
    response = client.get("/rules/current")

    assert response.status_code == 200
    body = response.json()
    rules = load_rules()
    assert body["version"] == rules.version
    assert body["subsidy"]["general"]["first_slab_inr_per_kw"] == 30000
    assert {c["key"] for c in body["citations"]} == set(rules.citations)
    for citation in body["citations"]:
        assert citation["status"] in {"confirmed", "verify", "assumption"}


def test_committed_openapi_file_matches_the_code() -> None:
    committed = DEFAULT_PATH.read_text(encoding="utf-8")
    assert committed == render(), "Run: npm run api:openapi"


def test_health() -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_request_create_accepts_a_valid_body() -> None:
    body = schemas.RequestCreate.model_validate(VALID_REQUEST)
    assert body.roof_area_m2 == Decimal(40)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("monthly_units", 0),
        ("budget_inr", -1),
        ("roof_area_m2", "0"),
        ("location", {"lat": 100, "lng": 72}),
        ("state_category", "north"),
        ("photo_keys", ["a", "b", "c", "d"]),
    ],
)
def test_request_create_rejects_bad_input(field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        schemas.RequestCreate.model_validate({**VALID_REQUEST, field: value})


def test_quote_create_accepts_a_valid_body() -> None:
    quote = schemas.QuoteCreate.model_validate(VALID_QUOTE)
    assert quote.inclusions == {"net_metering_fee", "mounting_structure"}


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("price_inr", 0),
        ("price_inr", 1.5),
        ("system_kw", "0"),
        ("timeline_days", 0),
        ("inclusions", ["free_lunch"]),
        ("notes", "x" * 2001),
    ],
)
def test_quote_create_rejects_bad_input(field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        schemas.QuoteCreate.model_validate({**VALID_QUOTE, field: value})


def test_every_checklist_item_can_be_ticked_on_the_quote_form() -> None:
    assert set(REQUIRED_INCLUSIONS) <= set(get_args(schemas.Inclusion))


def test_vendor_cannot_send_its_own_score() -> None:
    with pytest.raises(ValidationError):
        schemas.QuoteCreate.model_validate({**VALID_QUOTE, "score": 100})


def test_vendor_view_of_a_request_hides_household_details() -> None:
    fields = set(schemas.VendorRequestView.model_fields)

    assert "approx_location" in fields
    assert not fields & {"location", "phone", "address_text", "household_id"}
    assert set(schemas.HouseholdContact.model_fields) >= {"name", "phone", "location"}


def test_map_pins_carry_only_the_approximate_location() -> None:
    fields = set(schemas.OpenRequestPin.model_fields)
    assert "approx_location" in fields
    assert not fields & {"location", "phone", "address_text"}


@pytest.mark.parametrize(
    ("kind", "content_type", "size"),
    [
        ("photo", "audio/webm", 1000),
        ("audio", "image/jpeg", 1000),
        ("photo", "image/jpeg", schemas.MAX_UPLOAD_BYTES["photo"] + 1),
        ("photo", "text/html", 1000),
    ],
)
def test_presign_rejects_wrong_type_or_size(kind: str, content_type: str, size: int) -> None:
    with pytest.raises(ValidationError):
        schemas.PresignRequest(kind=kind, content_type=content_type, size_bytes=size)  # type: ignore[arg-type]


def test_presign_accepts_a_photo() -> None:
    body = schemas.PresignRequest(kind="photo", content_type="image/jpeg", size_bytes=900_000)
    assert body.kind == "photo"


def test_bbox_parses_west_south_east_north() -> None:
    box = schemas.BBox.parse("72.4,22.9,72.7,23.1")
    assert (box.west, box.south, box.east, box.north) == (72.4, 22.9, 72.7, 23.1)


@pytest.mark.parametrize("raw", ["72.4,22.9,72.7", "a,b,c,d", "72.7,22.9,72.4,23.1", "0,0,0,95"])
def test_bbox_rejects_malformed_boxes(raw: str) -> None:
    with pytest.raises(ValueError, match="bbox"):
        schemas.BBox.parse(raw)


def test_open_requests_rejects_a_bad_bbox_with_422() -> None:
    response = client.get(
        "/requests/open", params={"bbox": "1,2,3"}, headers={"Authorization": "Bearer x"}
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
