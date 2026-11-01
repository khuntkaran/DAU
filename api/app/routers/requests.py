from uuid import UUID

from fastapi import APIRouter

from api.app.deps import Household, HouseholdOrVendor, MapBox, PageParams, Vendor
from api.app.errors import error_responses, not_implemented
from api.app.schemas import (
    JobAccepted,
    OpenRequestPin,
    Page,
    QuoteComparison,
    QuoteCreate,
    QuoteCreated,
    Recommendation,
    RequestCreate,
    RequestOut,
    RequestSummary,
    VendorRequestView,
)

router = APIRouter(prefix="/requests", tags=["requests"])

# Fixed paths are declared before /{request_id} so "open" and "mine" are never read as an id.


@router.post(
    "", status_code=201, response_model=RequestOut, responses=error_responses(401, 403, 422)
)
async def create_request(body: RequestCreate, user: Household) -> RequestOut:
    """Opens a request. Sizing and subsidy are calculated in code and returned at once."""
    raise not_implemented()


@router.get("/mine", response_model=Page[RequestSummary], responses=error_responses(401, 403))
async def my_requests(user: Household, page: PageParams) -> Page[RequestSummary]:
    raise not_implemented()


@router.get("/open", response_model=Page[OpenRequestPin], responses=error_responses(401, 403, 422))
async def open_requests(user: Vendor, bbox: MapBox, page: PageParams) -> Page[OpenRequestPin]:
    """Open and quoted requests inside the viewport and the vendor's service radius."""
    raise not_implemented()


@router.get(
    "/{request_id}",
    response_model=RequestOut | VendorRequestView,
    responses=error_responses(401, 403, 404),
)
async def get_request(request_id: UUID, user: HouseholdOrVendor) -> RequestOut | VendorRequestView:
    """The owner gets `RequestOut`; a vendor gets `VendorRequestView`. Check `view`."""
    raise not_implemented()


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
    response_model=Recommendation,
    responses=error_responses(401, 403, 404),
)
async def get_recommendation(request_id: UUID, user: Household) -> Recommendation:
    raise not_implemented()
