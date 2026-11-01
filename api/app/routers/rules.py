from fastapi import APIRouter

from api.app.schemas import RulesOut
from api.app.services.rules import current_rules

router = APIRouter(prefix="/rules", tags=["rules"])


@router.get("/current", response_model=RulesOut)
async def get_current_rules() -> RulesOut:
    """Public. The rule set and its sources, for the "where does this number come from" panel."""
    return current_rules()
