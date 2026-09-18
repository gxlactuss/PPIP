from sqlmodel import SQLModel, Session, create_engine

from app.core.config import settings
import os
from dotenv import load_dotenv

load_dotenv()

# Create the engine pointing to PostgreSQL (via your settings/env file)
engine = create_engine(
    str(settings.database_url),
    echo=False,
)


def init_db() -> None:
    """Create all tables. Called once on application startup."""
    SQLModel.metadata.create_all(engine)


def get_session():
    """FastAPI dependency that yields a DB session per-request."""
    with Session(engine) as session:
        yield session
