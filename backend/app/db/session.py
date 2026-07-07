from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.db.base import Base
from app.db.seed import ensure_initial_admin
from sqlalchemy.orm import Session


engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


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
