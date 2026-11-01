from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from api.app.deps import AnyUser
from api.app.errors import error_responses, not_implemented
from api.app.schemas import Event

router = APIRouter(tags=["events"])


class EventStream(StreamingResponse):
    media_type = "text/event-stream"


@router.get(
    "/events",
    response_class=EventStream,
    responses={
        200: {"model": Event, "description": "A stream of `Event` messages."},
        # Errors are JSON even though success is a stream, so the media type is stated here.
        **{
            status: {
                "description": "Error",
                "content": {
                    "application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}
                },
            }
            for status in error_responses(401)
        },
    },
)
async def events(user: AnyUser) -> EventStream:
    """Server-Sent Events for the signed-in user."""
    raise not_implemented()
