from fastapi import APIRouter

from api.app.deps import AppSettings, DbSession
from api.app.errors import error_responses
from api.app.schemas import OtpRequest, OtpSent, TokenResponse, UserOut, VerifyRequest
from api.app.services import auth

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/otp", response_model=OtpSent, responses=error_responses(422, 429, 503))
def send_otp(body: OtpRequest, db: DbSession, settings: AppSettings) -> OtpSent:
    """Public. Sends a login code. In local mode the code is `DEMO_OTP`."""
    return OtpSent(expires_in_s=auth.send_otp(db, settings, body.phone))


@router.post(
    "/verify", response_model=TokenResponse, responses=error_responses(401, 403, 422, 429, 503)
)
def verify_otp(body: VerifyRequest, db: DbSession, settings: AppSettings) -> TokenResponse:
    """Public. Exchanges the code for a JWT. A new phone must choose `household` or `vendor`."""
    user, token = auth.verify_otp(db, settings, body)
    return TokenResponse(
        access_token=token,
        expires_in_s=settings.jwt_ttl_s,
        user=UserOut.model_validate(user),
    )
