"""
database.py
------------
Sets up the SQLAlchemy "engine" (connection to our SQLite file) and a
session factory that the rest of the app uses to talk to the database.

Why this pattern:
SQLAlchemy recommends creating ONE engine per application, then opening
a new lightweight "session" per unit of work (e.g. one per API check,
one per FastAPI request). This file provides that shared engine + a
helper to get sessions safely.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from backend.config import DATABASE_URL

# ---------------------------------------------------------------------------
# The engine is the low-level object that manages the actual connection
# to monitoring.db. `connect_args` is SQLite-specific: by default SQLite
# only allows the connection to be used by the thread that created it,
# but APScheduler + FastAPI will access it from different threads, so we
# disable that check (safe here since we only do simple, short writes/reads).
# ---------------------------------------------------------------------------
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

# ---------------------------------------------------------------------------
# SessionLocal is a factory: calling SessionLocal() gives you a new
# database session (like opening a "conversation" with the DB that you
# commit/close when done).
# ---------------------------------------------------------------------------
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ---------------------------------------------------------------------------
# Base is the parent class that all ORM models (tables) inherit from.
# SQLAlchemy uses it to keep track of table metadata.
# ---------------------------------------------------------------------------
Base = declarative_base()


def get_db():
    """
    Dependency function used by FastAPI routes to get a database session.

    Using 'yield' here means: give the route a session to use, and once
    the route is done (success or error), automatically close it. This
    prevents connections from leaking.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Creates all tables defined in models.py if they don't already exist.
    Safe to call every time the app starts — it won't wipe existing data.
    """
    # Import here (not at top) to avoid circular imports between
    # database.py and models.py.
    from backend import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
