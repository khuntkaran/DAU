from uuid import UUID

from fastapi import APIRouter

from api.app.deps import Household, PageParams, Vendor
from api.app.errors import error_responses, not_implemented
from api.app.schemas import AcceptResult, Page, VendorQuoteSummary

router = APIRouter(prefix="/quotes", tags=["quotes"])


@router.get("/mine", response_model=Page[VendorQuoteSummary], responses=error_responses(401, 403))
async def my_quotes(user: Vendor, page: PageParams) -> Page[VendorQuoteSummary]:
    raise not_implemented()


@router.post(
    "/{quote_id}/accept",
    response_model=AcceptResult,
    responses=error_responses(401, 403, 404, 409),
)
async def accept_quote(quote_id: UUID, user: Household) -> AcceptResult:
    """One transaction: this quote ACCEPTED, the others REJECTED, the request ACCEPTED.

    409 when the request is no longer QUOTED, including the loser of two simultaneous accepts.
    """
    raise not_implemented()
