from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.db.base import Base
from app.db.seed import ensure_initial_admin
from sqlalchemy.orm import Session


_url = settings.DATABASE_URL or ""
if _url.startswith("sqlite"):
    # sqlite (used only for tests/smoke): a single shared connection (StaticPool)
    # avoids cross-connection "database is locked" contention. Production uses
    # PostgreSQL, so this branch never runs there.
    from sqlalchemy.pool import StaticPool

    engine = create_engine(
        _url,
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_conn, _record):  # noqa: ANN001
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA busy_timeout=5000")
        cur.close()

else:
    engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, future=True)

SessionLocal = sessionmaker(
    bind=engine, autocommit=False, autoflush=False, expire_on_commit=False
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Seed initial data into the database.
    Note: Schema creation is handled by Alembic migrations.
    """
    # Seed initial data
    with Session(engine) as db:
        ensure_initial_admin(db)
        db.commit()
    
    print("Database seeded successfully")
