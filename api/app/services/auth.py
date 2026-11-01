"""Phone OTP login and JWTs. No FastAPI imports: routers and dependencies call these."""

import hashlib
import hmac
import secrets
import uuid
from datetime import timedelta

import jwt
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.app import models
from api.app.config import Settings
from api.app.db import utcnow
from api.app.enums import OtpPurpose, Role, VerificationStatus
from api.app.errors import ApiError
from api.app.schemas import VerifyRequest

OTP_TTL = timedelta(minutes=5)
MAX_ATTEMPTS = 5
MAX_SENDS = 5
SEND_WINDOW = timedelta(minutes=15)
_ALGORITHM = "HS256"


def _secret(settings: Settings) -> str:
    if not settings.jwt_secret:
        raise ApiError(503, "auth_not_configured", "Login is not configured on this server.")
    return settings.jwt_secret


def _hash(phone: str, code: str, settings: Settings) -> str:
    # Keyed, so a leaked table of six-digit codes cannot be reversed by trying all million.
    message = f"{phone}:{code}".encode()
    return hmac.new(_secret(settings).encode(), message, hashlib.sha256).hexdigest()


def send_otp(db: Session, settings: Settings, phone: str) -> int:
    """Stores a hashed code and returns its lifetime in seconds."""
    if not settings.demo_otp:
        # A real SMS provider replaces this branch; until then nobody could receive a code.
        raise ApiError(503, "sms_unavailable", "Login codes cannot be sent right now.")
    _secret(settings)

    now = utcnow()
    recent = db.scalar(
        select(func.count())
        .select_from(models.AuthOtp)
        .where(models.AuthOtp.phone == phone, models.AuthOtp.created_at > now - SEND_WINDOW)
    )
    if (recent or 0) >= MAX_SENDS:
        raise ApiError(429, "too_many_codes", "Too many codes requested. Try again later.")

    db.add(
        models.AuthOtp(
            phone=phone,
            code_hash=_hash(phone, settings.demo_otp, settings),
            purpose=OtpPurpose.LOGIN,
            expires_at=now + OTP_TTL,
            created_at=now,
        )
    )
    db.commit()
    return int(OTP_TTL.total_seconds())


def verify_otp(db: Session, settings: Settings, body: VerifyRequest) -> tuple[models.User, str]:
    """Checks the latest unused code, then signs the user in, creating them on first login."""
    now = utcnow()
    otp = db.scalars(
        select(models.AuthOtp)
        .where(models.AuthOtp.phone == body.phone, models.AuthOtp.consumed_at.is_(None))
        .order_by(models.AuthOtp.created_at.desc())
        .limit(1)
    ).first()
    if otp is None or otp.expires_at <= now:
        raise ApiError(401, "code_expired", "This code has expired. Request a new one.")
    if otp.attempts >= MAX_ATTEMPTS:
        raise ApiError(429, "too_many_attempts", "Too many wrong codes. Request a new one.")
    if not hmac.compare_digest(otp.code_hash, _hash(body.phone, body.code, settings)):
        otp.attempts += 1
        db.commit()
        raise ApiError(401, "invalid_code", "That code is not right.")

    user = db.scalars(select(models.User).where(models.User.phone == body.phone)).first()
    if user is None:
        if body.role is None:
            raise ApiError(422, "role_required", "Choose household or vendor to sign up.")
        user = models.User(
            role=body.role,
            phone=body.phone,
            full_name=body.full_name,
            preferred_lang=body.preferred_lang,
            # Column defaults apply only on insert, and the check below runs before that.
            is_active=True,
        )
        db.add(user)
        if body.role == Role.VENDOR:
            # The vendor completes the profile later; it stays pending until an admin verifies it.
            db.add(
                models.Vendor(
                    user=user,
                    company_name=body.full_name or body.phone,
                    contact_person=body.full_name,
                    contact_phone=body.phone,
                    verification_status=VerificationStatus.PENDING,
                )
            )
    if not user.is_active:
        raise ApiError(403, "account_suspended", "This account is suspended.")

    otp.consumed_at = now
    user.last_login_at = now
    db.commit()
    return user, issue_token(user, settings)


def issue_token(user: models.User, settings: Settings) -> str:
    now = utcnow()
    claims = {
        "sub": str(user.id),
        "role": str(user.role),
        "iat": now,
        "exp": now + timedelta(seconds=settings.jwt_ttl_s),
        "jti": secrets.token_hex(8),
    }
    return jwt.encode(claims, _secret(settings), algorithm=_ALGORITHM)


def current_user(
    db: Session, settings: Settings, token: str, roles: tuple[Role, ...]
) -> models.User:
    """The signed-in user, if their role is allowed. The role is read from the database."""
    try:
        claims = jwt.decode(token, _secret(settings), algorithms=[_ALGORITHM])
        user_id = uuid.UUID(claims["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise ApiError(401, "invalid_token", "Your session has expired. Sign in again.") from None

    user = db.get(models.User, user_id)
    if user is None:
        raise ApiError(401, "invalid_token", "Your session has expired. Sign in again.")
    if not user.is_active:
        raise ApiError(403, "account_suspended", "This account is suspended.")
    if user.role not in roles:
        raise ApiError(403, "forbidden", "Your account cannot do this.")
    return user
