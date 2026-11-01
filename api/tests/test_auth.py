"""Phone OTP login (work plan 3.1). The demo code comes from DEMO_OTP; no SMS is sent."""

from collections.abc import Callable
from datetime import timedelta

import jwt
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.app import models
from api.app.config import Settings
from api.app.db import utcnow
from api.app.enums import Role, VerificationStatus
from api.app.services.auth import MAX_ATTEMPTS, MAX_SENDS, OTP_TTL
from api.tests.conftest import MakeUser

PHONE = "+919812345678"
Auth = Callable[[models.User], dict[str, str]]


def _send(client: TestClient, phone: str = PHONE) -> None:
    assert client.post("/auth/otp", json={"phone": phone}).status_code == 200


def _verify(client: TestClient, code: str = "123456", **extra: object) -> dict[str, object]:
    response = client.post("/auth/verify", json={"phone": PHONE, "code": code, **extra})
    return {"status": response.status_code, **response.json()}


def _error(result: dict[str, object]) -> object:
    body = result["error"]
    assert isinstance(body, dict)
    return body["code"]


def test_sending_a_code_stores_only_its_hash(client: TestClient, db: Session) -> None:
    response = client.post("/auth/otp", json={"phone": PHONE})

    assert response.status_code == 200
    assert response.json() == {"expires_in_s": int(OTP_TTL.total_seconds())}
    otp = db.scalars(select(models.AuthOtp)).one()
    assert otp.phone == PHONE
    assert "123456" not in otp.code_hash


def test_first_login_creates_a_household(client: TestClient, db: Session) -> None:
    _send(client)
    result = _verify(client, role="household", full_name="Asha", preferred_lang="gu")

    assert result["status"] == 200
    user = result["user"]
    assert isinstance(user, dict)
    assert (user["role"], user["full_name"], user["preferred_lang"]) == ("household", "Asha", "gu")
    assert result["token_type"] == "bearer"
    stored = db.scalars(select(models.User)).one()
    assert stored.last_login_at is not None


def test_first_login_as_vendor_creates_a_pending_vendor_profile(
    client: TestClient, db: Session
) -> None:
    _send(client)
    assert _verify(client, role="vendor", full_name="Ravi Solar")["status"] == 200

    vendor = db.scalars(select(models.Vendor)).one()
    assert vendor.company_name == "Ravi Solar"
    assert vendor.verification_status == VerificationStatus.PENDING


def test_first_login_without_a_role_is_rejected(client: TestClient) -> None:
    _send(client)
    result = _verify(client)

    assert result["status"] == 422
    assert _error(result) == "role_required"


def test_a_returning_user_keeps_their_role(client: TestClient, db: Session) -> None:
    db.add(models.User(role=Role.VENDOR, phone=PHONE, full_name="V"))
    db.commit()
    _send(client)

    result = _verify(client, role="household")

    user = result["user"]
    assert isinstance(user, dict)
    assert user["role"] == "vendor"


def test_the_token_carries_the_user_and_role(client: TestClient, settings: Settings) -> None:
    _send(client)
    result = _verify(client, role="household")

    token = result["access_token"]
    assert isinstance(token, str)
    claims = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    user = result["user"]
    assert isinstance(user, dict)
    assert (claims["sub"], claims["role"]) == (user["id"], "household")
    assert result["expires_in_s"] == settings.jwt_ttl_s


def test_a_wrong_code_is_rejected_and_counted(client: TestClient, db: Session) -> None:
    _send(client)
    result = _verify(client, code="000000", role="household")

    assert result["status"] == 401
    assert _error(result) == "invalid_code"
    assert db.scalars(select(models.AuthOtp)).one().attempts == 1


def test_too_many_wrong_codes_lock_the_code(client: TestClient) -> None:
    _send(client)
    for _ in range(MAX_ATTEMPTS):
        _verify(client, code="000000", role="household")

    result = _verify(client, role="household")
    assert result["status"] == 429
    assert _error(result) == "too_many_attempts"


def test_a_code_works_only_once(client: TestClient) -> None:
    _send(client)
    assert _verify(client, role="household")["status"] == 200

    result = _verify(client, role="household")
    assert result["status"] == 401
    assert _error(result) == "code_expired"


def test_an_expired_code_is_rejected(client: TestClient, db: Session) -> None:
    _send(client)
    otp = db.scalars(select(models.AuthOtp)).one()
    otp.expires_at = utcnow() - timedelta(seconds=1)
    db.commit()

    result = _verify(client, role="household")
    assert result["status"] == 401
    assert _error(result) == "code_expired"


def test_verifying_without_requesting_a_code_fails(client: TestClient) -> None:
    result = _verify(client, role="household")
    assert result["status"] == 401
    assert _error(result) == "code_expired"


def test_sending_too_many_codes_is_rate_limited(client: TestClient) -> None:
    for _ in range(MAX_SENDS):
        _send(client)

    response = client.post("/auth/otp", json={"phone": PHONE})
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "too_many_codes"


def test_without_a_demo_code_or_sms_provider_login_is_unavailable(
    client: TestClient, settings: Settings
) -> None:
    settings.demo_otp = None

    response = client.post("/auth/otp", json={"phone": PHONE})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "sms_unavailable"


def test_without_a_jwt_secret_login_is_unavailable(client: TestClient, settings: Settings) -> None:
    settings.jwt_secret = ""

    response = client.post("/auth/otp", json={"phone": PHONE})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "auth_not_configured"


# --- Roles on protected routes --------------------------------------------------------------


def test_the_right_role_reaches_the_route(
    client: TestClient, make_user: MakeUser, auth: Auth
) -> None:
    response = client.get("/requests/mine", headers=auth(make_user(Role.HOUSEHOLD)))
    assert response.status_code == 200


def test_the_wrong_role_is_forbidden(client: TestClient, make_user: MakeUser, auth: Auth) -> None:
    response = client.get("/requests/mine", headers=auth(make_user(Role.VENDOR)))

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


def test_a_tampered_token_is_rejected(client: TestClient, make_user: MakeUser, auth: Auth) -> None:
    headers = auth(make_user(Role.HOUSEHOLD))
    headers["Authorization"] += "x"

    response = client.get("/requests/mine", headers=headers)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_token"


def test_an_expired_token_is_rejected(
    client: TestClient, make_user: MakeUser, settings: Settings
) -> None:
    user = make_user(Role.HOUSEHOLD)
    token = jwt.encode(
        {"sub": str(user.id), "role": "household", "exp": utcnow() - timedelta(seconds=1)},
        settings.jwt_secret,
        algorithm="HS256",
    )

    response = client.get("/requests/mine", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_token"


def test_a_suspended_user_is_forbidden(client: TestClient, make_user: MakeUser, auth: Auth) -> None:
    response = client.get("/requests/mine", headers=auth(make_user(is_active=False)))

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "account_suspended"


def test_the_role_comes_from_the_database_not_the_token(
    client: TestClient, db: Session, make_user: MakeUser, auth: Auth
) -> None:
    user = make_user(Role.HOUSEHOLD)
    headers = auth(user)
    user.role = Role.VENDOR
    db.commit()

    assert client.get("/requests/mine", headers=headers).status_code == 403
