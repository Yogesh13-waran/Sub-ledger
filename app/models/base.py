from datetime import datetime, timezone
from sqlalchemy import Column, DateTime


def utc_now() -> datetime:
    """Helper to return current UTC datetime."""
    return datetime.now(timezone.utc)


class TimestampMixin:
    """Mixin that adds created_at and updated_at timestamp columns."""
    created_at = Column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )
