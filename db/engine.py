import os
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def get_database_url() -> str:
    """
    Uses DATABASE_URL from .env or environment.
    Defaults to SQLite for local development if not set.
    """
    return os.getenv("DATABASE_URL", "sqlite:///./local.db")

def get_engine() -> Engine:
    """
    Returns a SQLAlchemy engine using the database URL.
    """
    db_url = get_database_url()
    return create_engine(
        db_url,
        pool_pre_ping=True,
        future=True,
    )
