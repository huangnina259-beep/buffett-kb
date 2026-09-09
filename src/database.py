from sqlalchemy import create_engine, Column, String, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

from pathlib import Path

_storage_dir = Path(os.environ.get("RAILWAY_VOLUME_MOUNT_PATH") or Path(__file__).resolve().parents[1] / "database")
_storage_dir.mkdir(parents=True, exist_ok=True)
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{_storage_dir / 'coach.db'}")
# Railway's DATABASE_URL starts with postgres://, SQLAlchemy needs postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class CompanyArchive(Base):
    __tablename__ = "company_archives"

    company_id = Column(String, primary_key=True)
    company_name = Column(String, nullable=False)
    ticker = Column(String, default="")
    first_analysis = Column(String)
    last_updated = Column(String)
    sessions = Column(JSON, default=[])


class UserState(Base):
    __tablename__ = "user_state"

    id = Column(String, primary_key=True, default="default")
    onboarding_completed = Column(String, default="false")
    onboarding_skipped = Column(String, default="false")
    onboarding_current_module = Column(String, default="1.1")


def init_db():
    Base.metadata.create_all(engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
