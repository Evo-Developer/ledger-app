from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import OperationalError
import os
from dotenv import load_dotenv

load_dotenv()

# Default to MySQL, but allow overriding via env and fall back to SQLite if unavailable.
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://ledger_user:ledger_pass@localhost:3306/ledger_db"
)

def _create_engine(url: str):
    """Create a SQLAlchemy engine and validate the connection."""
    engine = create_engine(
        url,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=True  # Set to False in production
    )

    # Validate connectivity early
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
    except Exception as e:
        raise OperationalError(f"Unable to connect to database: {e}", None, None)

    return engine

try:
    engine = _create_engine(DATABASE_URL)
except OperationalError as e:
    # Fallback to local SQLite for development/demo purposes
    print(f"[database] Warning: {e}")
    print("[database] Falling back to local SQLite database at ./ledger.db")
    SQLITE_URL = "sqlite:///./ledger.db"
    engine = create_engine(
        SQLITE_URL,
        connect_args={"check_same_thread": False},
        echo=True
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables"""
    from models import Base
    Base.metadata.create_all(bind=engine)
