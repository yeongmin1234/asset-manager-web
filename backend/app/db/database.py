from typing import Generator, Optional, Tuple

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


def create_database_engine() -> Engine:
    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 3},
    )


engine = create_database_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database_connection() -> Tuple[bool, Optional[str]]:
    engine: Optional[Engine] = None
    try:
        engine = create_database_engine()
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True, None
    except Exception as exc:
        return False, str(exc)
    finally:
        if engine is not None:
            engine.dispose()
