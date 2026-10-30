from typing import TypeVar, Generic, Type, Optional, List, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, func

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """
    Generic Base Repository implementing standard CRUD operations via SQLAlchemy.
    Adheres to the Repository Pattern to decouple data persistence from business logic.
    """
    def __init__(self, db: Session, model_cls: Type[T]):
        self.db = db
        self.model_cls = model_cls

    def get_by_id(self, entity_id: Any) -> Optional[T]:
        """Fetch an entity by primary key."""
        return self.db.get(self.model_cls, entity_id)

    def list(self, skip: int = 0, limit: int = 100) -> List[T]:
        """List entities with pagination."""
        stmt = select(self.model_cls).offset(skip).limit(limit)
        return list(self.db.scalars(stmt).all())

    def count(self) -> int:
        """Count total entities of this type."""
        stmt = select(func.count()).select_from(self.model_cls)
        return self.db.scalar(stmt) or 0

    def create(self, entity: T) -> T:
        """Persist a new entity instance."""
        self.db.add(entity)
        self.db.flush()
        self.db.refresh(entity)
        return entity

    def update(self, entity: T) -> T:
        """Update and flush changes on an entity instance."""
        self.db.add(entity)
        self.db.flush()
        self.db.refresh(entity)
        return entity

    def delete(self, entity: T) -> None:
        """Remove an entity instance from database."""
        self.db.delete(entity)
        self.db.flush()
