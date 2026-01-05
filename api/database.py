### Description ###
# GlassTrax-Bridge - Python Interface for GlassTrax ERP
# - App Database Setup -
# Author: Bailey Dixon
# Date: 01/03/2026
# Python: 3.11
####################

"""
App Database Setup

SQLite database for storing:
- API Keys and tenants
- Access logs
- Portal users (future)

Uses synchronous SQLAlchemy (no greenlet dependency).
"""

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Database file location
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
DATABASE_PATH = DATA_DIR / "glasstrax_bridge.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# Create engine (synchronous)
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # Allow multi-threaded access
    echo=False,  # Set True for SQL debugging
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db():
    """
    Dependency that provides a database session.

    Usage:
        @app.get("/endpoint")
        def endpoint(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize the database - create all tables.

    Call this on application startup.
    """
    # Import models to register them with Base
    from api.models import access_log, api_key, tenant  # noqa: F401

    Base.metadata.create_all(bind=engine)
    print(f"Database initialized at: {DATABASE_PATH}")


def drop_db():
    """Drop all tables (use with caution!)"""
    Base.metadata.drop_all(bind=engine)
