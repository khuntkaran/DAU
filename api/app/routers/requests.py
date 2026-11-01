from uuid import UUID

from fastapi import APIRouter, BackgroundTasks

from api.app.deps import (
    Ai,
    AppSettings,
    DbSession,
    Household,
    HouseholdOrVendor,
    MapBox,
    PageParams,
    Sessions,
    Vendor,
)
from api.app.errors import error_responses
from api.app.jobs import photo_assess, recommend
from api.app.jobs.runner import run_job
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
from api.app.services import quotes, requests

router = APIRouter(prefix="/requests", tags=["requests"])

# Fixed paths are declared before /{request_id} so "open" and "mine" are never read as an id.


@router.post(
    "", status_code=201, response_model=RequestOut, responses=error_responses(401, 403, 422)
)
def create_request(
    body: RequestCreate,
    user: Household,
    db: DbSession,
    background: BackgroundTasks,
    sessions: Sessions,
    ai: Ai,
    settings: AppSettings,
) -> RequestOut:
    """Opens a request. Sizing and subsidy are calculated in code and returned at once.

    With a photo, the roof assessment starts in the background and shows as `pending`; when it
    finishes, the estimate is recalculated from the usable roof area.
    """
    request = requests.create_request(db, user, body)
    job = photo_assess.queue_assessment(db, request, user)
    if job is not None:
        background.add_task(run_job, job.id, sessions, ai, settings)
    return requests.owner_view(db, request)


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
def submit_quote(
    request_id: UUID,
    body: QuoteCreate,
    user: Vendor,
    db: DbSession,
    background: BackgroundTasks,
    sessions: Sessions,
    ai: Ai,
    settings: AppSettings,
) -> QuoteCreated:
    """Saves the quote with net cost and payback from code, then queues `quote_review`.

    Missing items and warnings are checked in code at once; the AI notes follow later.
    409 when the request is not open or quoted, or this vendor has already quoted it.
    """
    quote, job, needs_run = quotes.submit_quote(db, user, request_id, body)
    if needs_run:
        background.add_task(run_job, job.id, sessions, ai, settings)
    return QuoteCreated(quote=quotes.quote_out(db, quote), review_job_id=job.id)


@router.get(
    "/{request_id}/quotes",
    response_model=QuoteComparison,
    responses=error_responses(401, 403, 404),
)
def compare_quotes(request_id: UUID, user: Household, db: DbSession) -> QuoteComparison:
    """Every quote on the household's request, best score first, with each score explained."""
    return quotes.compare_quotes(db, user, request_id)


@router.post(
    "/{request_id}/recommendation",
    status_code=202,
    response_model=JobAccepted,
    responses=error_responses(401, 403, 404, 409),
)
def request_recommendation(
    request_id: UUID,
    user: Household,
    db: DbSession,
    background: BackgroundTasks,
    sessions: Sessions,
    ai: Ai,
    settings: AppSettings,
) -> JobAccepted:
    """Queues `recommend`, or returns the existing job while the quotes are unchanged.

    Code ranks the quotes; the AI only explains the ranking, and a template takes over if the
    AI is down. 409 when there are no quotes yet.
    """
    job, needs_run = recommend.request_recommendation(db, user, request_id)
    if needs_run:
        background.add_task(run_job, job.id, sessions, ai, settings)
    return JobAccepted(
        job_id=job.id, job_type=job.job_type, status=job.status, entity_id=job.entity_id
    )


@router.get(
    "/{request_id}/recommendation",
    response_model=RecommendationOut,
    responses=error_responses(401, 403, 404),
)
def get_recommendation(request_id: UUID, user: Household, db: DbSession) -> RecommendationOut:
    """The latest recommendation. `stale` is true once a quote has changed since."""
    return recommend.latest_recommendation(db, user, request_id)
