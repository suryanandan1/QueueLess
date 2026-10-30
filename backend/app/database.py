from collections.abc import Generator
from typing import Any

from sqlalchemy import Engine, MetaData, create_engine, event, inspect
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

# Explicit constraint names keep migrations deterministic across SQLite and PostgreSQL.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def create_db_engine(database_url: str, **engine_kwargs: Any) -> Engine:
    """Create an engine; SQLite gets thread-safety relaxed and foreign keys enforced."""
    is_sqlite = database_url.startswith("sqlite")
    connect_args = {"check_same_thread": False} if is_sqlite else {}
    db_engine = create_engine(
        database_url, connect_args=connect_args, pool_pre_ping=True, **engine_kwargs
    )

    if is_sqlite:

        @event.listens_for(db_engine, "connect")
        def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return db_engine


engine = create_db_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db(db_engine: Engine = engine) -> None:
    """Create tables that do not exist yet. Use a migration tool for schema changes."""
    import app.models  # noqa: F401  (registers all models on Base.metadata)

    Base.metadata.create_all(bind=db_engine)
    _check_schema_is_current(db_engine)


def _check_schema_is_current(db_engine: Engine) -> None:
    """create_all never alters existing tables, so fail fast if columns are missing."""
    inspector = inspect(db_engine)
    missing = [
        f"{table.name}.{column.name}"
        for table in Base.metadata.sorted_tables
        for column in table.columns
        if column.name not in {c["name"] for c in inspector.get_columns(table.name)}
    ]
    if missing:
        raise RuntimeError(
            "The database schema is older than the application (missing columns: "
            + ", ".join(missing)
            + "). For a local SQLite database, delete the .db file and restart; "
            "otherwise apply a migration."
        )
