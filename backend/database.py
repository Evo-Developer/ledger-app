from sqlalchemy import create_engine, text
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
            conn.execute(text("SELECT 1"))
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


def ensure_transaction_recurring_column():
    """Ensure recurring column exists on transactions table for both SQLite and MySQL/PostgreSQL."""
    from sqlalchemy import text

    with engine.connect() as conn:
        try:
            if engine.dialect.name == 'sqlite':
                columns = [row[1] for row in conn.execute(text('PRAGMA table_info(transactions)')).fetchall()]
                if 'recurring' not in columns:
                    conn.execute(text('ALTER TABLE transactions ADD COLUMN recurring BOOLEAN DEFAULT 0'))
            elif engine.dialect.name in ('mysql', 'mariadb'):
                exists = conn.execute(text("SHOW COLUMNS FROM transactions LIKE 'recurring' ")).fetchone()
                if not exists:
                    conn.execute(text('ALTER TABLE transactions ADD COLUMN recurring BOOLEAN DEFAULT FALSE'))
            elif engine.dialect.name == 'postgresql':
                exists = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='transactions' AND column_name='recurring' ")).fetchone()
                if not exists:
                    conn.execute(text('ALTER TABLE transactions ADD COLUMN recurring BOOLEAN DEFAULT FALSE'))
        except Exception as e:
            print(f"[database] Warning: could not ensure recurring column in transactions: {e}")


def init_db():
    """Initialize database tables"""
    from models import Base
    Base.metadata.create_all(bind=engine)
    ensure_transaction_recurring_column()
