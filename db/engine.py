import os
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

def get_database_url() -> str:
    """
    Uses DATABASE_URL if set.
    Defaults to SQLite for local development.
    """
    return os.getenv(
        "DATABASE_URL",
        "sqlite:///./local.db"
    )

def get_engine() -> Engine:
    return create_engine(
        get_database_url(),
        pool_pre_ping=True,
        future=True,
    )
