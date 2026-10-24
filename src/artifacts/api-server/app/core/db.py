"""Database engine, session factory and the declarative base for all tables."""

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import config

engine = create_engine(config.database_url, echo=config.log_sql, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Iterator[Session]:
    """FastAPI dependency: one session per request, always closed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


DB = Annotated[Session, Depends(get_db)]


def create_tables() -> None:
    from app.modules import load_models

    load_models()
    Base.metadata.create_all(engine)
