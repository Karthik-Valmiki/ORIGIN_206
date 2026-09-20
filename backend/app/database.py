from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from .config import settings

# For psycopg2 connection replace postgresql:// with postgresql+psycopg2:// if needed,
# but SQLAlchemy 2.0 works fine with postgresql:// if psycopg2 is installed.
engine = create_engine(settings.DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://"), pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
