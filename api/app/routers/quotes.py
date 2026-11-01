from uuid import UUID

from fastapi import APIRouter

from api.app.deps import DbSession, Household, PageParams, Vendor
from api.app.errors import error_responses
from api.app.schemas import AcceptResult, Page, VendorQuoteSummary
from api.app.services import quotes

router = APIRouter(prefix="/quotes", tags=["quotes"])


@router.get(
    "/mine", response_model=Page[VendorQuoteSummary], responses=error_responses(401, 403, 422)
)
def my_quotes(user: Vendor, page: PageParams, db: DbSession) -> Page[VendorQuoteSummary]:
    """The vendor's quotes, newest first. Household contact appears once a quote is accepted."""
    limit, cursor = page
    return quotes.my_quotes(db, user, limit, cursor)


@router.post(
    "/{quote_id}/accept",
    response_model=AcceptResult,
    responses=error_responses(401, 403, 404, 409),
)
def accept_quote(quote_id: UUID, user: Household, db: DbSession) -> AcceptResult:
    """One transaction: this quote accepted, the others rejected, the request accepted.

    Returns the vendor's contact. The vendor sees the household's contact from then on.
    409 when the request is no longer quoted, including the loser of two simultaneous accepts.
    """
    return quotes.accept_quote(db, user, quote_id)
