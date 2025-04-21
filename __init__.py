from .database import engine, SessionLocal, get_db
from .models import Base, MemorySnapshotModel
from .repository import MemorySnapshotRepository


def init_db():
    """
    Initializes the database by creating all tables.
    This should be called at application startup if the schema hasn't been created yet.
    """
    Base.metadata.create_all(bind=engine)


__all__ = [
    "engine",
    "SessionLocal",
    "get_db",
    "Base",
    "MemorySnapshotModel",
    "MemorySnapshotRepository",
    "init_db",
]
