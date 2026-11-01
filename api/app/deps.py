"""Shared route dependencies: database, settings, signed-in user, pagination and map box."""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Query
from fastapi.exceptions import RequestValidationError
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from api.app import models
from api.app.config import Settings, get_settings
from api.app.db import SessionFactory, get_db, get_session_factory
from api.app.enums import Role
from api.app.errors import ApiError
from api.app.llm.gateway import Gateway, get_gateway
from api.app.schemas import BBox
from api.app.services.auth import current_user

DbSession = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]
Sessions = Annotated[SessionFactory, Depends(get_session_factory)]
Ai = Annotated[Gateway, Depends(get_gateway)]

_bearer = HTTPBearer(auto_error=False)


def require_role(*roles: Role) -> Callable[..., models.User]:
    """Declares who may call a route, and hands the route the signed-in user."""

    def _check(
        credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
        db: DbSession,
        settings: AppSettings,
    ) -> models.User:
        if credentials is None:
            raise ApiError(401, "unauthenticated", "Sign in first.")
        return current_user(db, settings, credentials.credentials, roles)

    _check.__name__ = f"require_{'_or_'.join(roles)}"
    return _check


Household = Annotated[models.User, Depends(require_role(Role.HOUSEHOLD))]
Vendor = Annotated[models.User, Depends(require_role(Role.VENDOR))]
HouseholdOrVendor = Annotated[models.User, Depends(require_role(Role.HOUSEHOLD, Role.VENDOR))]
AnyUser = Annotated[models.User, Depends(require_role(Role.HOUSEHOLD, Role.VENDOR, Role.ADMIN))]


def page_params(
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: Annotated[str | None, Query(max_length=200)] = None,
) -> tuple[int, str | None]:
    return limit, cursor


PageParams = Annotated[tuple[int, str | None], Depends(page_params)]


def bbox_param(
    bbox: Annotated[str, Query(description="Map viewport as west,south,east,north in degrees.")],
) -> BBox:
    try:
        return BBox.parse(bbox)
    except ValueError as exc:
        raise RequestValidationError(
            [{"loc": ("query", "bbox"), "msg": str(exc), "type": "value_error"}]
        ) from None


MapBox = Annotated[BBox, Depends(bbox_param)]
