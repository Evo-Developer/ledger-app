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


def ensure_document_folder_columns():
    """Ensure folder and subfolder columns exist on documents table."""
    from sqlalchemy import text

    with engine.connect() as conn:
        try:
            if engine.dialect.name == 'sqlite':
                columns = [row[1] for row in conn.execute(text('PRAGMA table_info(documents)')).fetchall()]
                if 'folder' not in columns:
                    conn.execute(text("ALTER TABLE documents ADD COLUMN folder VARCHAR(255) DEFAULT 'General'"))
                if 'subfolder' not in columns:
                    conn.execute(text('ALTER TABLE documents ADD COLUMN subfolder VARCHAR(255)'))
            elif engine.dialect.name in ('mysql', 'mariadb'):
                folder_exists = conn.execute(text("SHOW COLUMNS FROM documents LIKE 'folder'")).fetchone()
                if not folder_exists:
                    conn.execute(text("ALTER TABLE documents ADD COLUMN folder VARCHAR(255) NOT NULL DEFAULT 'General'"))
                subfolder_exists = conn.execute(text("SHOW COLUMNS FROM documents LIKE 'subfolder'")).fetchone()
                if not subfolder_exists:
                    conn.execute(text("ALTER TABLE documents ADD COLUMN subfolder VARCHAR(255) NULL"))
            elif engine.dialect.name == 'postgresql':
                folder_exists = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='documents' AND column_name='folder'")).fetchone()
                if not folder_exists:
                    conn.execute(text("ALTER TABLE documents ADD COLUMN folder VARCHAR(255) NOT NULL DEFAULT 'General'"))
                subfolder_exists = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='documents' AND column_name='subfolder'")).fetchone()
                if not subfolder_exists:
                    conn.execute(text("ALTER TABLE documents ADD COLUMN subfolder VARCHAR(255)"))
        except Exception as e:
            print(f"[database] Warning: could not ensure folder/subfolder columns in documents: {e}")


def ensure_user_role_column():
    """Ensure role column exists on users table."""
    from sqlalchemy import text

    with engine.connect() as conn:
        try:
            if engine.dialect.name == 'sqlite':
                columns = [row[1] for row in conn.execute(text('PRAGMA table_info(users)')).fetchall()]
                if 'role' not in columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(32) DEFAULT 'user'"))
            elif engine.dialect.name in ('mysql', 'mariadb'):
                exists = conn.execute(text("SHOW COLUMNS FROM users LIKE 'role'")).fetchone()
                if not exists:
                    conn.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(32) NOT NULL DEFAULT 'user'"))
            elif engine.dialect.name == 'postgresql':
                exists = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='role'")).fetchone()
                if not exists:
                    conn.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(32) NOT NULL DEFAULT 'user'"))
        except Exception as e:
            print(f"[database] Warning: could not ensure role column in users: {e}")


def ensure_bootstrap_admin():
    """Ensure there is at least one admin user by promoting the oldest account if needed."""
    from sqlalchemy import text

    with engine.begin() as conn:
        try:
            admin_exists = conn.execute(
                text("SELECT id FROM users WHERE role = 'admin' ORDER BY id LIMIT 1")
            ).fetchone()
            if admin_exists:
                return

            first_user = conn.execute(
                text("SELECT id FROM users ORDER BY created_at ASC, id ASC LIMIT 1")
            ).fetchone()
            if first_user:
                conn.execute(
                    text("UPDATE users SET role = 'admin' WHERE id = :user_id"),
                    {"user_id": first_user[0]}
                )
        except Exception as e:
            print(f"[database] Warning: could not ensure bootstrap admin user: {e}")


def ensure_asset_balance_column():
    """Ensure include_in_balance column exists on assets table."""
    from sqlalchemy import text

    with engine.connect() as conn:
        try:
            if engine.dialect.name == 'sqlite':
                columns = [row[1] for row in conn.execute(text('PRAGMA table_info(assets)')).fetchall()]
                if 'include_in_balance' not in columns:
                    conn.execute(text('ALTER TABLE assets ADD COLUMN include_in_balance BOOLEAN DEFAULT 1'))
            elif engine.dialect.name in ('mysql', 'mariadb'):
                exists = conn.execute(text("SHOW COLUMNS FROM assets LIKE 'include_in_balance'")).fetchone()
                if not exists:
                    conn.execute(text('ALTER TABLE assets ADD COLUMN include_in_balance BOOLEAN NOT NULL DEFAULT TRUE'))
            elif engine.dialect.name == 'postgresql':
                exists = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='assets' AND column_name='include_in_balance'")).fetchone()
                if not exists:
                    conn.execute(text('ALTER TABLE assets ADD COLUMN include_in_balance BOOLEAN NOT NULL DEFAULT TRUE'))
        except Exception as e:
            print(f"[database] Warning: could not ensure include_in_balance column in assets: {e}")


def init_db():
    """Initialize database tables"""
    from models import Base
    Base.metadata.create_all(bind=engine)
    ensure_user_role_column()
    ensure_bootstrap_admin()
    ensure_asset_balance_column()
    ensure_transaction_recurring_column()
    ensure_document_folder_columns()
