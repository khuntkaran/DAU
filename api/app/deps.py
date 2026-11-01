"""Shared route dependencies: authentication, roles, pagination and the map bounding box."""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Query
from fastapi.exceptions import RequestValidationError
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.app.enums import Role
from api.app.errors import ApiError
from api.app.schemas import BBox

_bearer = HTTPBearer(auto_error=False)


def require_role(*roles: Role) -> Callable[[HTTPAuthorizationCredentials | None], str]:
    """Declares who may call a route.

    Only the token's presence is checked for now. JWT decoding and the role check replace the
    body of `_check` when OTP auth is built, without changing any route signature.
    """

    def _check(
        credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    ) -> str:
        if credentials is None:
            raise ApiError(401, "unauthenticated", "Sign in first.")
        return credentials.credentials

    _check.__name__ = f"require_{'_or_'.join(roles)}"
    return _check


Household = Annotated[str, Depends(require_role("household"))]
Vendor = Annotated[str, Depends(require_role("vendor"))]
HouseholdOrVendor = Annotated[str, Depends(require_role("household", "vendor"))]
AnyUser = Annotated[str, Depends(require_role("household", "vendor", "admin"))]


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
