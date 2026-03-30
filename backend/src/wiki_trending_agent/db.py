from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from wiki_trending_agent.config import settings
from wiki_trending_agent.models import Base

engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_session() -> Iterator[Session]:
    # Ensures tables exist even when lifespan startup hooks are not executed by a client.
    init_db()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
