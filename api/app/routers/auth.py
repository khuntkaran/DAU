from fastapi import APIRouter

from api.app.errors import error_responses, not_implemented
from api.app.schemas import OtpRequest, OtpSent, TokenResponse, VerifyRequest

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/otp", response_model=OtpSent, responses=error_responses(422, 429))
async def send_otp(body: OtpRequest) -> OtpSent:
    """Public. Sends a login code. The demo code is 123456."""
    raise not_implemented()


@router.post("/verify", response_model=TokenResponse, responses=error_responses(401, 422))
async def verify_otp(body: VerifyRequest) -> TokenResponse:
    """Public. Exchanges the code for a JWT that carries the user's role."""
    raise not_implemented()
