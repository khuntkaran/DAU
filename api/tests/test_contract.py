"""The API contract: every route in the work plan, its auth, and its schemas.

These tests need no database. Behaviour tests arrive with each endpoint.
"""

from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from api.app import schemas
from api.app.enums import FilePurpose
from api.app.export_openapi import DEFAULT_PATH, render
from api.app.main import app
from rules.loader import load_rules

client = TestClient(app)

ROUTES = {
    ("post", "/auth/otp"),
    ("post", "/auth/verify"),
    ("post", "/uploads"),
    ("get", "/files/{file_id}"),
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
    "lat": 23.0225,
    "lng": 72.5714,
    "location_source": "map_pin",
    "monthly_units": 330,
    "budget_inr": 200000,
    "roof_area_sqm": "40",
    "roof_type": "rcc_flat",
}
VALID_QUOTE: dict[str, Any] = {
    "system_kw": "3",
    "price_total_inr": 185000,
    "gst_included": True,
    "panel_brand": "Waaree",
    "panel_wattage": 545,
    "panel_count": 6,
    "dcr_compliant": True,
    "inverter_brand": "Growatt",
    "inverter_capacity_kw": "3",
    "panel_performance_warranty_yrs": 25,
    "inverter_warranty_yrs": 10,
    "workmanship_warranty_yrs": 5,
    "timeline_days": 21,
    "line_items": [
        {"item_type": "net_meter", "amount_inr": 5000},
        {"item_type": "amc", "included": False},
    ],
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


def test_statuses_use_the_lowercase_values_from_the_schema_doc() -> None:
    statuses = app.openapi()["components"]["schemas"]["RequestStatus"]["enum"]
    assert statuses == ["draft", "open", "quoted", "accepted", "completed", "cancelled", "expired"]


def test_request_create_accepts_a_valid_body() -> None:
    body = schemas.RequestCreate.model_validate(VALID_REQUEST)
    assert body.roof_area_sqm == Decimal(40)
    assert body.input_method == "form"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("monthly_units", 0),
        ("budget_inr", -1),
        ("roof_area_sqm", "0"),
        ("lat", 100),
        ("location_source", "guess"),
        ("pincode", "38001"),
        ("photo_file_ids", [REQUEST_ID] * 4),
        ("state_category", "special"),
    ],
)
def test_request_create_rejects_bad_input(field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        schemas.RequestCreate.model_validate({**VALID_REQUEST, field: value})


def test_quote_create_accepts_a_valid_body() -> None:
    quote = schemas.QuoteCreate.model_validate(VALID_QUOTE)
    assert [i.item_type for i in quote.line_items] == ["net_meter", "amc"]
    assert quote.line_items[1].included is False


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("price_total_inr", 0),
        ("price_total_inr", 1.5),
        ("system_kw", "0"),
        ("timeline_days", 0),
        ("line_items", [{"item_type": "free_lunch"}]),
        ("notes", "x" * 2001),
    ],
)
def test_quote_create_rejects_bad_input(field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        schemas.QuoteCreate.model_validate({**VALID_QUOTE, field: value})


@pytest.mark.parametrize("field", ["total_score", "injection_flag", "status"])
def test_vendor_cannot_send_its_own_score_flag_or_status(field: str) -> None:
    with pytest.raises(ValidationError):
        schemas.QuoteCreate.model_validate({**VALID_QUOTE, field: 100})


def test_vendor_view_of_a_request_hides_household_details() -> None:
    fields = set(schemas.VendorRequestView.model_fields)

    assert {"approx_lat", "approx_lng"} <= fields
    assert not fields & {"lat", "lng", "phone", "address_text", "pincode", "household_id"}
    assert set(schemas.HouseholdContact.model_fields) >= {"full_name", "phone", "lat", "lng"}


def test_map_pins_carry_only_the_approximate_location() -> None:
    fields = set(schemas.OpenRequestPin.model_fields)
    assert {"approx_lat", "approx_lng"} <= fields
    assert not fields & {"lat", "lng", "phone", "address_text", "pincode"}


@pytest.mark.parametrize(
    ("purpose", "content_type", "size"),
    [
        (FilePurpose.TERRACE_PHOTO, "audio/webm", 1000),
        (FilePurpose.VOICE_AUDIO, "image/jpeg", 1000),
        (FilePurpose.TERRACE_PHOTO, "image/jpeg", 0),
        (FilePurpose.TERRACE_PHOTO, "image/jpeg", 8 * 1024 * 1024 + 1),
        (FilePurpose.TERRACE_PHOTO, "text/html", 1000),
        (FilePurpose.LOGO, "image/png", 1000),
    ],
)
def test_uploads_reject_wrong_type_or_size(
    purpose: FilePurpose, content_type: str, size: int
) -> None:
    with pytest.raises(ValueError, match=str(purpose) + "|" + content_type):
        schemas.check_upload(purpose, content_type, size)


@pytest.mark.parametrize(
    ("purpose", "content_type"),
    [
        (FilePurpose.TERRACE_PHOTO, "image/jpeg"),
        (FilePurpose.ELECTRICITY_BILL, "application/pdf"),
        (FilePurpose.VOICE_AUDIO, "audio/webm"),
    ],
)
def test_uploads_accept_the_expected_types(purpose: FilePurpose, content_type: str) -> None:
    schemas.check_upload(purpose, content_type, 900_000)


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
