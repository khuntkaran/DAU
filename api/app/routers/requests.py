from uuid import UUID

from fastapi import APIRouter

from api.app.deps import DbSession, Household, HouseholdOrVendor, MapBox, PageParams, Vendor
from api.app.errors import error_responses, not_implemented
from api.app.schemas import (
    JobAccepted,
    OpenRequestPin,
    Page,
    QuoteComparison,
    QuoteCreate,
    QuoteCreated,
    RecommendationOut,
    RequestCreate,
    RequestOut,
    RequestSummary,
    VendorRequestView,
)
from api.app.services import requests

router = APIRouter(prefix="/requests", tags=["requests"])

# Fixed paths are declared before /{request_id} so "open" and "mine" are never read as an id.


@router.post(
    "", status_code=201, response_model=RequestOut, responses=error_responses(401, 403, 422)
)
def create_request(body: RequestCreate, user: Household, db: DbSession) -> RequestOut:
    """Opens a request. Sizing and subsidy are calculated in code and returned at once."""
    return requests.owner_view(db, requests.create_request(db, user, body))


@router.get("/mine", response_model=Page[RequestSummary], responses=error_responses(401, 403, 422))
def my_requests(user: Household, page: PageParams, db: DbSession) -> Page[RequestSummary]:
    """The household's requests, newest first."""
    limit, cursor = page
    return requests.my_requests(db, user, limit, cursor)


@router.get("/open", response_model=Page[OpenRequestPin], responses=error_responses(401, 403, 422))
def open_requests(
    user: Vendor, bbox: MapBox, page: PageParams, db: DbSession
) -> Page[OpenRequestPin]:
    """Open and quoted requests inside the viewport and the vendor's service radius.

    Pins sit at the rounded location, newest first. Without a base location the radius
    is not applied and distances are empty.
    """
    limit, cursor = page
    return requests.open_requests(db, user, bbox, limit, cursor)


@router.get(
    "/{request_id}",
    response_model=RequestOut | VendorRequestView,
    responses=error_responses(401, 403, 404),
)
def get_request(
    request_id: UUID, user: HouseholdOrVendor, db: DbSession
) -> RequestOut | VendorRequestView:
    """The owner gets `RequestOut`; a vendor gets `VendorRequestView`. Check `view`.

    Vendors see open and quoted requests, and any request they have quoted.
    """
    return requests.get_request(db, user, request_id)


@router.post(
    "/{request_id}/quotes",
    status_code=201,
    response_model=QuoteCreated,
    responses=error_responses(401, 403, 404, 409, 422),
)
async def submit_quote(request_id: UUID, body: QuoteCreate, user: Vendor) -> QuoteCreated:
    """Saves the quote with net cost and payback from code, then queues `quote_review`.

    409 when the request is not OPEN or QUOTED, or this vendor has already quoted it.
    """
    raise not_implemented()


@router.get(
    "/{request_id}/quotes",
    response_model=QuoteComparison,
    responses=error_responses(401, 403, 404),
)
async def compare_quotes(request_id: UUID, user: Household) -> QuoteComparison:
    raise not_implemented()


@router.post(
    "/{request_id}/recommendation",
    status_code=202,
    response_model=JobAccepted,
    responses=error_responses(401, 403, 404, 409),
)
async def request_recommendation(request_id: UUID, user: Household) -> JobAccepted:
    """Queues `recommend`, or returns the existing job while the quotes are unchanged."""
    raise not_implemented()


@router.get(
    "/{request_id}/recommendation",
    response_model=RecommendationOut,
    responses=error_responses(401, 403, 404),
)
async def get_recommendation(request_id: UUID, user: Household) -> RecommendationOut:
    raise not_implemented()
