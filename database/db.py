import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import inspect, text
from sqlmodel import Session, SQLModel, create_engine

# Automatically load environment variables from backend/.env or root .env
_here = Path(__file__).resolve().parent
_candidates = [
    _here.parent / "backend" / ".env",
    _here.parent / ".env",
    Path(".env"),
]
for _candidate in _candidates:
    if _candidate.exists():
        load_dotenv(_candidate)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:121726@localhost:5432/placed_db",
)

# Normalize postgres:// to postgresql+psycopg2:// if needed
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = "postgresql+psycopg2://" + DATABASE_URL[len("postgres://") :]
elif DATABASE_URL.startswith("postgresql://") and not DATABASE_URL.startswith("postgresql+"):
    DATABASE_URL = "postgresql+psycopg2://" + DATABASE_URL[len("postgresql://") :]

_is_sqlite = DATABASE_URL.startswith("sqlite")
_connect_args = {"check_same_thread": False} if _is_sqlite else {}
_engine_kwargs = {"echo": False, "connect_args": _connect_args}
if not _is_sqlite:
    _engine_kwargs["pool_pre_ping"] = True

engine = create_engine(DATABASE_URL, **_engine_kwargs)

_ADDED_COLUMNS: dict[str, dict[str, str]] = {
    "users": {
        "target_company": "VARCHAR",
    },
    "interview_sessions": {
        "mode": "VARCHAR",
        "context_json": "VARCHAR",
    },
}


def init_db() -> None:
    from database import models

    SQLModel.metadata.create_all(engine)
    _add_missing_columns()


def _add_missing_columns() -> None:
    inspector = inspect(engine)
    try:
        table_names = inspector.get_table_names()
    except Exception:
        table_names = []

    with engine.connect() as connection:
        for table, columns in _ADDED_COLUMNS.items():
            if table not in table_names:
                continue
            existing = {col["name"] for col in inspector.get_columns(table)}
            for name, column_type in columns.items():
                if name not in existing:
                    connection.execute(
                        text(f'ALTER TABLE "{table}" ADD COLUMN {name} {column_type}')
                    )
        connection.commit()


def get_session():
    with Session(engine) as session:
        yield session
