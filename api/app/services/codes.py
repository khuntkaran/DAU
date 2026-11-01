"""Readable codes such as SR-2026-000123, numbered per year."""

from sqlalchemy import func, select
from sqlalchemy.orm import InstrumentedAttribute, Session

from api.app.db import utcnow

# A clash on the unique code means another insert took the number first; callers retry.
CODE_RETRIES = 3


def next_code(db: Session, column: InstrumentedAttribute[str], kind: str) -> str:
    prefix = f"{kind}-{utcnow().year}-"
    last = db.scalar(select(func.max(column)).where(column.like(f"{prefix}%")))
    return f"{prefix}{int(last[-6:]) + 1 if last else 1:06d}"
