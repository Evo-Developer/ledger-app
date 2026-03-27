from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import OperationalError
import os
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

load_dotenv()

# Import enterprise connection pool configuration
try:
    from concurrency import connection_pool as enterprise_pool
    ENTERPRISE_MODE = True
except ImportError:
    ENTERPRISE_MODE = False
    logger.warning("Enterprise mode disabled - concurrency module not available")

# Default to MySQL, but allow overriding via env and fall back to SQLite if unavailable.
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://ledger_user:ledger_pass@localhost:3306/ledger_db"
)

def _create_engine(url: str):
    """Create a SQLAlchemy engine with enterprise-grade configuration."""
    
    # Get connection pool config from enterprise module if available
    if ENTERPRISE_MODE:
        pool_config = enterprise_pool.get_connection_config()
        logger.info(f"Using enterprise connection pool: {pool_config}")
    else:
        pool_config = {
            'pool_size': 20,
            'max_overflow': 10,
            'pool_pre_ping': True,
            'pool_recycle': 3600,
            'echo': False,
        }
    
    engine = create_engine(url, **pool_config)

    # Validate connectivity early
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            logger.info("Database connection validated successfully")
    except Exception as e:
        raise OperationalError(f"Unable to connect to database: {e}", None, None)

    return engine

try:
    engine = _create_engine(DATABASE_URL)
except OperationalError as e:
    # Fallback to local SQLite for development/demo purposes
    logger.warning(f"[database] {e}")
    logger.info("[database] Falling back to local SQLite database at ./ledger.db")
    SQLITE_URL = "sqlite:///./ledger.db"
    engine = create_engine(
        SQLITE_URL,
        connect_args={"check_same_thread": False},
        echo=False
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency to get database session with proper resource cleanup."""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {str(e)[:100]}")
        db.rollback()
        raise
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


def ensure_transaction_spread_over_year_column():
    """Ensure spread_over_year column exists on transactions table."""
    from sqlalchemy import text

    with engine.connect() as conn:
        try:
            if engine.dialect.name == 'sqlite':
                columns = [row[1] for row in conn.execute(text('PRAGMA table_info(transactions)')).fetchall()]
                if 'spread_over_year' not in columns:
                    conn.execute(text('ALTER TABLE transactions ADD COLUMN spread_over_year BOOLEAN DEFAULT 0'))
            elif engine.dialect.name in ('mysql', 'mariadb'):
                exists = conn.execute(text("SHOW COLUMNS FROM transactions LIKE 'spread_over_year'")).fetchone()
                if not exists:
                    conn.execute(text('ALTER TABLE transactions ADD COLUMN spread_over_year BOOLEAN DEFAULT FALSE'))
            elif engine.dialect.name == 'postgresql':
                exists = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='transactions' AND column_name='spread_over_year'")).fetchone()
                if not exists:
                    conn.execute(text('ALTER TABLE transactions ADD COLUMN spread_over_year BOOLEAN DEFAULT FALSE'))
        except Exception as e:
            print(f"[database] Warning: could not ensure spread_over_year column in transactions: {e}")


def ensure_transaction_idempotency_key_column():
    """Ensure idempotency_key column exists on transactions table."""
    from sqlalchemy import text

    with engine.connect() as conn:
        try:
            if engine.dialect.name == 'sqlite':
                columns = [row[1] for row in conn.execute(text('PRAGMA table_info(transactions)')).fetchall()]
                if 'idempotency_key' not in columns:
                    conn.execute(text('ALTER TABLE transactions ADD COLUMN idempotency_key VARCHAR(128)'))
            elif engine.dialect.name in ('mysql', 'mariadb'):
                exists = conn.execute(text("SHOW COLUMNS FROM transactions LIKE 'idempotency_key' ")).fetchone()
                if not exists:
                    conn.execute(text('ALTER TABLE transactions ADD COLUMN idempotency_key VARCHAR(128) NULL'))
            elif engine.dialect.name == 'postgresql':
                exists = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='transactions' AND column_name='idempotency_key' ")).fetchone()
                if not exists:
                    conn.execute(text('ALTER TABLE transactions ADD COLUMN idempotency_key VARCHAR(128)'))
            conn.commit()
        except Exception as e:
            print(f"[database] Warning: could not ensure idempotency_key column in transactions: {e}")


def ensure_transaction_amount_decimal_column():
    """Ensure transactions.amount uses a fixed-point decimal type."""
    from sqlalchemy import text

    with engine.connect() as conn:
        try:
            if engine.dialect.name == 'sqlite':
                # SQLite uses dynamic typing and does not support ALTER COLUMN TYPE.
                return
            elif engine.dialect.name in ('mysql', 'mariadb'):
                conn.execute(text('ALTER TABLE transactions MODIFY COLUMN amount DECIMAL(18,2) NOT NULL'))
            elif engine.dialect.name == 'postgresql':
                conn.execute(text('ALTER TABLE transactions ALTER COLUMN amount TYPE NUMERIC(18,2) USING amount::NUMERIC(18,2)'))
            conn.commit()
        except Exception as e:
            print(f"[database] Warning: could not ensure decimal amount column in transactions: {e}")


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


def ensure_document_statement_columns():
    """Ensure statement import metadata columns exist on documents table."""
    from sqlalchemy import text

    with engine.connect() as conn:
        try:
            if engine.dialect.name == 'sqlite':
                columns = [row[1] for row in conn.execute(text('PRAGMA table_info(documents)')).fetchall()]
                if 'document_type' not in columns:
                    conn.execute(text("ALTER TABLE documents ADD COLUMN document_type VARCHAR(50) NOT NULL DEFAULT 'general'"))
                if 'frozen_import' not in columns:
                    conn.execute(text('ALTER TABLE documents ADD COLUMN frozen_import BOOLEAN NOT NULL DEFAULT 0'))
                if 'imported_transaction_count' not in columns:
                    conn.execute(text('ALTER TABLE documents ADD COLUMN imported_transaction_count INTEGER NOT NULL DEFAULT 0'))
            elif engine.dialect.name in ('mysql', 'mariadb'):
                statements = [
                    ('document_type', "ALTER TABLE documents ADD COLUMN document_type VARCHAR(50) NOT NULL DEFAULT 'general'"),
                    ('frozen_import', 'ALTER TABLE documents ADD COLUMN frozen_import BOOLEAN NOT NULL DEFAULT FALSE'),
                    ('imported_transaction_count', 'ALTER TABLE documents ADD COLUMN imported_transaction_count INTEGER NOT NULL DEFAULT 0'),
                ]
                for column_name, ddl in statements:
                    exists = conn.execute(text(f"SHOW COLUMNS FROM documents LIKE '{column_name}'")).fetchone()
                    if not exists:
                        conn.execute(text(ddl))
            elif engine.dialect.name == 'postgresql':
                statements = [
                    ('document_type', "ALTER TABLE documents ADD COLUMN document_type VARCHAR(50) NOT NULL DEFAULT 'general'"),
                    ('frozen_import', 'ALTER TABLE documents ADD COLUMN frozen_import BOOLEAN NOT NULL DEFAULT FALSE'),
                    ('imported_transaction_count', 'ALTER TABLE documents ADD COLUMN imported_transaction_count INTEGER NOT NULL DEFAULT 0'),
                ]
                for column_name, ddl in statements:
                    exists = conn.execute(text(f"SELECT column_name FROM information_schema.columns WHERE table_name='documents' AND column_name='{column_name}'")).fetchone()
                    if not exists:
                        conn.execute(text(ddl))
            conn.commit()
        except Exception as e:
            print(f"[database] Warning: could not ensure statement metadata columns in documents: {e}")


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


def ensure_user_permissions_column():
    """Ensure permissions_json column exists on users table."""
    from sqlalchemy import text

    with engine.connect() as conn:
        try:
            if engine.dialect.name == 'sqlite':
                columns = [row[1] for row in conn.execute(text('PRAGMA table_info(users)')).fetchall()]
                if 'permissions_json' not in columns:
                    conn.execute(text('ALTER TABLE users ADD COLUMN permissions_json TEXT'))
            elif engine.dialect.name in ('mysql', 'mariadb'):
                exists = conn.execute(text("SHOW COLUMNS FROM users LIKE 'permissions_json'")).fetchone()
                if not exists:
                    conn.execute(text('ALTER TABLE users ADD COLUMN permissions_json TEXT NULL'))
            elif engine.dialect.name == 'postgresql':
                exists = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='permissions_json' ")).fetchone()
                if not exists:
                    conn.execute(text('ALTER TABLE users ADD COLUMN permissions_json TEXT'))
            conn.commit()
        except Exception as e:
            print(f"[database] Warning: could not ensure permissions_json column in users: {e}")


def ensure_user_federation_columns():
    """Ensure identity_provider and external_subject columns exist on users table."""
    from sqlalchemy import text

    with engine.connect() as conn:
        try:
            if engine.dialect.name == 'sqlite':
                columns = [row[1] for row in conn.execute(text('PRAGMA table_info(users)')).fetchall()]
                if 'identity_provider' not in columns:
                    conn.execute(text('ALTER TABLE users ADD COLUMN identity_provider VARCHAR(64)'))
                if 'external_subject' not in columns:
                    conn.execute(text('ALTER TABLE users ADD COLUMN external_subject VARCHAR(255)'))
            elif engine.dialect.name in ('mysql', 'mariadb'):
                provider_exists = conn.execute(text("SHOW COLUMNS FROM users LIKE 'identity_provider' ")).fetchone()
                if not provider_exists:
                    conn.execute(text('ALTER TABLE users ADD COLUMN identity_provider VARCHAR(64) NULL'))
                subject_exists = conn.execute(text("SHOW COLUMNS FROM users LIKE 'external_subject' ")).fetchone()
                if not subject_exists:
                    conn.execute(text('ALTER TABLE users ADD COLUMN external_subject VARCHAR(255) NULL'))
            elif engine.dialect.name == 'postgresql':
                provider_exists = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='identity_provider' ")).fetchone()
                if not provider_exists:
                    conn.execute(text('ALTER TABLE users ADD COLUMN identity_provider VARCHAR(64)'))
                subject_exists = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='external_subject' ")).fetchone()
                if not subject_exists:
                    conn.execute(text('ALTER TABLE users ADD COLUMN external_subject VARCHAR(255)'))
            conn.commit()
        except Exception as e:
            print(f"[database] Warning: could not ensure federation columns in users: {e}")


def ensure_user_mfa_columns():
    """Ensure MFA columns exist on users table."""
    from sqlalchemy import text

    with engine.connect() as conn:
        try:
            if engine.dialect.name == 'sqlite':
                columns = [row[1] for row in conn.execute(text('PRAGMA table_info(users)')).fetchall()]
                if 'mfa_enabled' not in columns:
                    conn.execute(text('ALTER TABLE users ADD COLUMN mfa_enabled BOOLEAN NOT NULL DEFAULT 0'))
                if 'mfa_secret' not in columns:
                    conn.execute(text('ALTER TABLE users ADD COLUMN mfa_secret VARCHAR(64)'))
                if 'mfa_temp_secret' not in columns:
                    conn.execute(text('ALTER TABLE users ADD COLUMN mfa_temp_secret VARCHAR(64)'))
            elif engine.dialect.name in ('mysql', 'mariadb'):
                if not conn.execute(text("SHOW COLUMNS FROM users LIKE 'mfa_enabled' ")).fetchone():
                    conn.execute(text('ALTER TABLE users ADD COLUMN mfa_enabled BOOLEAN NOT NULL DEFAULT FALSE'))
                if not conn.execute(text("SHOW COLUMNS FROM users LIKE 'mfa_secret' ")).fetchone():
                    conn.execute(text('ALTER TABLE users ADD COLUMN mfa_secret VARCHAR(64) NULL'))
                if not conn.execute(text("SHOW COLUMNS FROM users LIKE 'mfa_temp_secret' ")).fetchone():
                    conn.execute(text('ALTER TABLE users ADD COLUMN mfa_temp_secret VARCHAR(64) NULL'))
            elif engine.dialect.name == 'postgresql':
                if not conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='mfa_enabled' ")).fetchone():
                    conn.execute(text('ALTER TABLE users ADD COLUMN mfa_enabled BOOLEAN NOT NULL DEFAULT FALSE'))
                if not conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='mfa_secret' ")).fetchone():
                    conn.execute(text('ALTER TABLE users ADD COLUMN mfa_secret VARCHAR(64)'))
                if not conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='mfa_temp_secret' ")).fetchone():
                    conn.execute(text('ALTER TABLE users ADD COLUMN mfa_temp_secret VARCHAR(64)'))
            conn.commit()
        except Exception as e:
            print(f"[database] Warning: could not ensure MFA columns in users: {e}")


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


def ensure_asset_income_column():
    """Ensure include_in_income column exists on assets table."""
    from sqlalchemy import text

    with engine.connect() as conn:
        try:
            if engine.dialect.name == 'sqlite':
                columns = [row[1] for row in conn.execute(text('PRAGMA table_info(assets)')).fetchall()]
                if 'include_in_income' not in columns:
                    conn.execute(text('ALTER TABLE assets ADD COLUMN include_in_income BOOLEAN DEFAULT 0'))
            elif engine.dialect.name in ('mysql', 'mariadb'):
                exists = conn.execute(text("SHOW COLUMNS FROM assets LIKE 'include_in_income'")).fetchone()
                if not exists:
                    conn.execute(text('ALTER TABLE assets ADD COLUMN include_in_income BOOLEAN NOT NULL DEFAULT FALSE'))
            elif engine.dialect.name == 'postgresql':
                exists = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='assets' AND column_name='include_in_income'")).fetchone()
                if not exists:
                    conn.execute(text('ALTER TABLE assets ADD COLUMN include_in_income BOOLEAN NOT NULL DEFAULT FALSE'))
        except Exception as e:
            print(f"[database] Warning: could not ensure include_in_income column in assets: {e}")


def ensure_asset_emergency_fund_column():
    """Ensure emergency_fund column exists on assets table."""
    from sqlalchemy import text

    with engine.connect() as conn:
        try:
            if engine.dialect.name == 'sqlite':
                columns = [row[1] for row in conn.execute(text('PRAGMA table_info(assets)')).fetchall()]
                if 'emergency_fund' not in columns:
                    conn.execute(text('ALTER TABLE assets ADD COLUMN emergency_fund BOOLEAN DEFAULT 0'))
            elif engine.dialect.name in ('mysql', 'mariadb'):
                exists = conn.execute(text("SHOW COLUMNS FROM assets LIKE 'emergency_fund'")).fetchone()
                if not exists:
                    conn.execute(text('ALTER TABLE assets ADD COLUMN emergency_fund BOOLEAN NOT NULL DEFAULT FALSE'))
            elif engine.dialect.name == 'postgresql':
                exists = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='assets' AND column_name='emergency_fund'")).fetchone()
                if not exists:
                    conn.execute(text('ALTER TABLE assets ADD COLUMN emergency_fund BOOLEAN NOT NULL DEFAULT FALSE'))
        except Exception as e:
            print(f"[database] Warning: could not ensure emergency_fund column in assets: {e}")


def ensure_asset_loan_emi_linked_column():
    """Ensure loan_emi_linked column exists on assets table."""
    from sqlalchemy import text

    with engine.connect() as conn:
        try:
            if engine.dialect.name == 'sqlite':
                columns = [row[1] for row in conn.execute(text('PRAGMA table_info(assets)')).fetchall()]
                if 'loan_emi_linked' not in columns:
                    conn.execute(text('ALTER TABLE assets ADD COLUMN loan_emi_linked BOOLEAN DEFAULT 0'))
            elif engine.dialect.name in ('mysql', 'mariadb'):
                exists = conn.execute(text("SHOW COLUMNS FROM assets LIKE 'loan_emi_linked'")).fetchone()
                if not exists:
                    conn.execute(text('ALTER TABLE assets ADD COLUMN loan_emi_linked BOOLEAN NOT NULL DEFAULT FALSE'))
            elif engine.dialect.name == 'postgresql':
                exists = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='assets' AND column_name='loan_emi_linked'")).fetchone()
                if not exists:
                    conn.execute(text('ALTER TABLE assets ADD COLUMN loan_emi_linked BOOLEAN NOT NULL DEFAULT FALSE'))
        except Exception as e:
            print(f"[database] Warning: could not ensure loan_emi_linked column in assets: {e}")


def ensure_liability_loan_columns():
    """Ensure loan metadata columns exist on liabilities table."""
    from sqlalchemy import text

    with engine.connect() as conn:
        try:
            if engine.dialect.name == 'sqlite':
                columns = [row[1] for row in conn.execute(text('PRAGMA table_info(liabilities)')).fetchall()]
                if 'is_loan' not in columns:
                    conn.execute(text('ALTER TABLE liabilities ADD COLUMN is_loan BOOLEAN DEFAULT 0'))
                if 'loan_start_date' not in columns:
                    conn.execute(text('ALTER TABLE liabilities ADD COLUMN loan_start_date DATETIME'))
                if 'loan_tenure_months' not in columns:
                    conn.execute(text('ALTER TABLE liabilities ADD COLUMN loan_tenure_months INTEGER'))
                if 'opportunity_cost_rate' not in columns:
                    conn.execute(text('ALTER TABLE liabilities ADD COLUMN opportunity_cost_rate FLOAT'))
                if 'linked_asset_id' not in columns:
                    conn.execute(text('ALTER TABLE liabilities ADD COLUMN linked_asset_id INTEGER'))
            elif engine.dialect.name in ('mysql', 'mariadb'):
                for column_name, ddl in [
                    ('is_loan', 'ALTER TABLE liabilities ADD COLUMN is_loan BOOLEAN NOT NULL DEFAULT FALSE'),
                    ('loan_start_date', 'ALTER TABLE liabilities ADD COLUMN loan_start_date DATETIME NULL'),
                    ('loan_tenure_months', 'ALTER TABLE liabilities ADD COLUMN loan_tenure_months INTEGER NULL'),
                    ('opportunity_cost_rate', 'ALTER TABLE liabilities ADD COLUMN opportunity_cost_rate DOUBLE NULL'),
                    ('linked_asset_id', 'ALTER TABLE liabilities ADD COLUMN linked_asset_id INTEGER NULL'),
                ]:
                    exists = conn.execute(text(f"SHOW COLUMNS FROM liabilities LIKE '{column_name}'")).fetchone()
                    if not exists:
                        conn.execute(text(ddl))
            elif engine.dialect.name == 'postgresql':
                for column_name, ddl in [
                    ('is_loan', 'ALTER TABLE liabilities ADD COLUMN is_loan BOOLEAN NOT NULL DEFAULT FALSE'),
                    ('loan_start_date', 'ALTER TABLE liabilities ADD COLUMN loan_start_date TIMESTAMP'),
                    ('loan_tenure_months', 'ALTER TABLE liabilities ADD COLUMN loan_tenure_months INTEGER'),
                    ('opportunity_cost_rate', 'ALTER TABLE liabilities ADD COLUMN opportunity_cost_rate DOUBLE PRECISION'),
                    ('linked_asset_id', 'ALTER TABLE liabilities ADD COLUMN linked_asset_id INTEGER'),
                ]:
                    exists = conn.execute(text(f"SELECT column_name FROM information_schema.columns WHERE table_name='liabilities' AND column_name='{column_name}'")).fetchone()
                    if not exists:
                        conn.execute(text(ddl))
            conn.commit()
        except Exception as e:
            print(f"[database] Warning: could not ensure loan columns in liabilities: {e}")


def ensure_liability_credit_card_columns():
    """Ensure credit card / tax tracking columns exist on liabilities table."""
    from sqlalchemy import text

    with engine.connect() as conn:
        try:
            if engine.dialect.name == 'sqlite':
                columns = [row[1] for row in conn.execute(text('PRAGMA table_info(liabilities)')).fetchall()]
                if 'liability_type' not in columns:
                    conn.execute(text("ALTER TABLE liabilities ADD COLUMN liability_type VARCHAR(50) DEFAULT 'general'"))
                if 'credit_limit' not in columns:
                    conn.execute(text('ALTER TABLE liabilities ADD COLUMN credit_limit FLOAT'))
                if 'is_paid_off' not in columns:
                    conn.execute(text('ALTER TABLE liabilities ADD COLUMN is_paid_off BOOLEAN DEFAULT 0'))
            elif engine.dialect.name in ('mysql', 'mariadb'):
                for column_name, ddl in [
                    ('liability_type', "ALTER TABLE liabilities ADD COLUMN liability_type VARCHAR(50) NOT NULL DEFAULT 'general'"),
                    ('credit_limit', 'ALTER TABLE liabilities ADD COLUMN credit_limit DOUBLE NULL'),
                    ('is_paid_off', 'ALTER TABLE liabilities ADD COLUMN is_paid_off BOOLEAN NOT NULL DEFAULT FALSE'),
                ]:
                    exists = conn.execute(text(f"SHOW COLUMNS FROM liabilities LIKE '{column_name}'")).fetchone()
                    if not exists:
                        conn.execute(text(ddl))
            elif engine.dialect.name == 'postgresql':
                for column_name, ddl in [
                    ('liability_type', "ALTER TABLE liabilities ADD COLUMN liability_type VARCHAR(50) DEFAULT 'general'"),
                    ('credit_limit', 'ALTER TABLE liabilities ADD COLUMN credit_limit DOUBLE PRECISION'),
                    ('is_paid_off', 'ALTER TABLE liabilities ADD COLUMN is_paid_off BOOLEAN DEFAULT FALSE'),
                ]:
                    exists = conn.execute(text(f"SELECT column_name FROM information_schema.columns WHERE table_name='liabilities' AND column_name='{column_name}'")).fetchone()
                    if not exists:
                        conn.execute(text(ddl))
            conn.commit()
        except Exception as e:
            print(f"[database] Warning: could not ensure credit card columns in liabilities: {e}")


def ensure_integration_oauth_columns():
    """Ensure OAuth support columns exist on integrations table."""
    from sqlalchemy import text

    with engine.connect() as conn:
        try:
            if engine.dialect.name == 'sqlite':
                columns = [row[1] for row in conn.execute(text('PRAGMA table_info(integrations)')).fetchall()]
                if 'account_email' not in columns:
                    conn.execute(text('ALTER TABLE integrations ADD COLUMN account_email VARCHAR(255)'))
                if 'oauth_token' not in columns:
                    conn.execute(text('ALTER TABLE integrations ADD COLUMN oauth_token TEXT'))
            elif engine.dialect.name in ('mysql', 'mariadb'):
                account_email_exists = conn.execute(text("SHOW COLUMNS FROM integrations LIKE 'account_email'")).fetchone()
                if not account_email_exists:
                    conn.execute(text('ALTER TABLE integrations ADD COLUMN account_email VARCHAR(255) NULL'))
                oauth_token_exists = conn.execute(text("SHOW COLUMNS FROM integrations LIKE 'oauth_token'")).fetchone()
                if not oauth_token_exists:
                    conn.execute(text('ALTER TABLE integrations ADD COLUMN oauth_token TEXT NULL'))
            elif engine.dialect.name == 'postgresql':
                account_email_exists = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='integrations' AND column_name='account_email'")).fetchone()
                if not account_email_exists:
                    conn.execute(text('ALTER TABLE integrations ADD COLUMN account_email VARCHAR(255)'))
                oauth_token_exists = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='integrations' AND column_name='oauth_token'")).fetchone()
                if not oauth_token_exists:
                    conn.execute(text('ALTER TABLE integrations ADD COLUMN oauth_token TEXT'))
        except Exception as e:
            print(f"[database] Warning: could not ensure OAuth columns in integrations: {e}")


def ensure_investment_monthly_sip_column():
    """Ensure monthly_sip column exists on investments table."""
    from sqlalchemy import text

    with engine.connect() as conn:
        try:
            if engine.dialect.name == 'sqlite':
                columns = [row[1] for row in conn.execute(text('PRAGMA table_info(investments)')).fetchall()]
                if 'monthly_sip' not in columns:
                    conn.execute(text('ALTER TABLE investments ADD COLUMN monthly_sip BOOLEAN DEFAULT 0'))
            elif engine.dialect.name in ('mysql', 'mariadb'):
                exists = conn.execute(text("SHOW COLUMNS FROM investments LIKE 'monthly_sip'")).fetchone()
                if not exists:
                    conn.execute(text('ALTER TABLE investments ADD COLUMN monthly_sip BOOLEAN NOT NULL DEFAULT FALSE'))
            elif engine.dialect.name == 'postgresql':
                exists = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='investments' AND column_name='monthly_sip'")).fetchone()
                if not exists:
                    conn.execute(text('ALTER TABLE investments ADD COLUMN monthly_sip BOOLEAN NOT NULL DEFAULT FALSE'))
        except Exception as e:
            print(f"[database] Warning: could not ensure monthly_sip column in investments: {e}")
            conn.commit()


def ensure_investment_annual_growth_rate_column():
    """Ensure annual_growth_rate column exists on investments table."""
    from sqlalchemy import text

    with engine.connect() as conn:
        try:
            if engine.dialect.name == 'sqlite':
                columns = [row[1] for row in conn.execute(text('PRAGMA table_info(investments)')).fetchall()]
                if 'annual_growth_rate' not in columns:
                    conn.execute(text('ALTER TABLE investments ADD COLUMN annual_growth_rate FLOAT'))
            elif engine.dialect.name in ('mysql', 'mariadb'):
                exists = conn.execute(text("SHOW COLUMNS FROM investments LIKE 'annual_growth_rate'")) .fetchone()
                if not exists:
                    conn.execute(text('ALTER TABLE investments ADD COLUMN annual_growth_rate DOUBLE NULL'))
            elif engine.dialect.name == 'postgresql':
                exists = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='investments' AND column_name='annual_growth_rate'")) .fetchone()
                if not exists:
                    conn.execute(text('ALTER TABLE investments ADD COLUMN annual_growth_rate DOUBLE PRECISION'))
            conn.commit()
        except Exception as e:
            print(f"[database] Warning: could not ensure annual_growth_rate column in investments: {e}")


def ensure_investment_start_date_column():
    """Ensure start_date column exists on investments table."""
    from sqlalchemy import text

    with engine.connect() as conn:
        try:
            if engine.dialect.name == 'sqlite':
                columns = [row[1] for row in conn.execute(text('PRAGMA table_info(investments)')).fetchall()]
                if 'start_date' not in columns:
                    conn.execute(text('ALTER TABLE investments ADD COLUMN start_date DATE'))
            elif engine.dialect.name in ('mysql', 'mariadb'):
                exists = conn.execute(text("SHOW COLUMNS FROM investments LIKE 'start_date'")) .fetchone()
                if not exists:
                    conn.execute(text('ALTER TABLE investments ADD COLUMN start_date DATE NULL'))
            elif engine.dialect.name == 'postgresql':
                exists = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='investments' AND column_name='start_date'")) .fetchone()
                if not exists:
                    conn.execute(text('ALTER TABLE investments ADD COLUMN start_date DATE'))
            conn.commit()
        except Exception as e:
            print(f"[database] Warning: could not ensure start_date column in investments: {e}")


def ensure_investment_goal_id_column():
    """Ensure goal_id column exists on investments table."""
    from sqlalchemy import text

    with engine.connect() as conn:
        try:
            if engine.dialect.name == 'sqlite':
                columns = [row[1] for row in conn.execute(text('PRAGMA table_info(investments)')).fetchall()]
                if 'goal_id' not in columns:
                    conn.execute(text('ALTER TABLE investments ADD COLUMN goal_id INTEGER'))
            elif engine.dialect.name in ('mysql', 'mariadb'):
                exists = conn.execute(text("SHOW COLUMNS FROM investments LIKE 'goal_id'")) .fetchone()
                if not exists:
                    conn.execute(text('ALTER TABLE investments ADD COLUMN goal_id INTEGER NULL'))
            elif engine.dialect.name == 'postgresql':
                exists = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='investments' AND column_name='goal_id'")) .fetchone()
                if not exists:
                    conn.execute(text('ALTER TABLE investments ADD COLUMN goal_id INTEGER'))
            conn.commit()
        except Exception as e:
            print(f"[database] Warning: could not ensure goal_id column in investments: {e}")


def ensure_budget_period_column():
    """Ensure period column exists on budgets table."""
    from sqlalchemy import text

    with engine.connect() as conn:
        try:
            if engine.dialect.name == 'sqlite':
                columns = [row[1] for row in conn.execute(text('PRAGMA table_info(budgets)')).fetchall()]
                if 'period' not in columns:
                    conn.execute(text("ALTER TABLE budgets ADD COLUMN period VARCHAR(20) DEFAULT 'monthly'"))
            elif engine.dialect.name in ('mysql', 'mariadb'):
                exists = conn.execute(text("SHOW COLUMNS FROM budgets LIKE 'period'")).fetchone()
                if not exists:
                    conn.execute(text("ALTER TABLE budgets ADD COLUMN period VARCHAR(20) NOT NULL DEFAULT 'monthly'"))
            elif engine.dialect.name == 'postgresql':
                exists = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='budgets' AND column_name='period'")).fetchone()
                if not exists:
                    conn.execute(text("ALTER TABLE budgets ADD COLUMN period VARCHAR(20) NOT NULL DEFAULT 'monthly'"))
            conn.commit()
        except Exception as e:
            print(f"[database] Warning: could not ensure period column in budgets: {e}")


def ensure_budget_recurring_column():
    """Ensure recurring column exists on budgets table."""
    from sqlalchemy import text

    with engine.connect() as conn:
        try:
            if engine.dialect.name == 'sqlite':
                columns = [row[1] for row in conn.execute(text('PRAGMA table_info(budgets)')).fetchall()]
                if 'recurring' not in columns:
                    conn.execute(text("ALTER TABLE budgets ADD COLUMN recurring BOOLEAN DEFAULT 0"))
            elif engine.dialect.name in ('mysql', 'mariadb'):
                exists = conn.execute(text("SHOW COLUMNS FROM budgets LIKE 'recurring'")).fetchone()
                if not exists:
                    conn.execute(text("ALTER TABLE budgets ADD COLUMN recurring BOOLEAN NOT NULL DEFAULT FALSE"))
            elif engine.dialect.name == 'postgresql':
                exists = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='budgets' AND column_name='recurring'"))
                exists = exists.fetchone()
                if not exists:
                    conn.execute(text("ALTER TABLE budgets ADD COLUMN recurring BOOLEAN NOT NULL DEFAULT FALSE"))
            conn.commit()
        except Exception as e:
            print(f"[database] Warning: could not ensure recurring column in budgets: {e}")


def ensure_goal_target_date_column():
    """Ensure target_date column exists on goals table."""
    from sqlalchemy import text

    with engine.connect() as conn:
        try:
            if engine.dialect.name == 'sqlite':
                columns = [row[1] for row in conn.execute(text('PRAGMA table_info(goals)')).fetchall()]
                if 'target_date' not in columns:
                    conn.execute(text('ALTER TABLE goals ADD COLUMN target_date DATE'))
            elif engine.dialect.name in ('mysql', 'mariadb'):
                exists = conn.execute(text("SHOW COLUMNS FROM goals LIKE 'target_date'")).fetchone()
                if not exists:
                    conn.execute(text('ALTER TABLE goals ADD COLUMN target_date DATE'))
            elif engine.dialect.name == 'postgresql':
                exists = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='goals' AND column_name='target_date'")).fetchone()
                if not exists:
                    conn.execute(text('ALTER TABLE goals ADD COLUMN target_date DATE'))
        except Exception as e:
            print(f"[database] Warning: could not ensure target_date column in goals: {e}")


def ensure_budget_start_month_column():
    """Ensure start_month column exists on budgets table."""
    from sqlalchemy import text

    with engine.connect() as conn:
        try:
            if engine.dialect.name == 'sqlite':
                columns = [row[1] for row in conn.execute(text('PRAGMA table_info(budgets)')).fetchall()]
                if 'start_month' not in columns:
                    conn.execute(text("ALTER TABLE budgets ADD COLUMN start_month VARCHAR(7)"))
            elif engine.dialect.name in ('mysql', 'mariadb'):
                exists = conn.execute(text("SHOW COLUMNS FROM budgets LIKE 'start_month'")).fetchone()
                if not exists:
                    conn.execute(text("ALTER TABLE budgets ADD COLUMN start_month VARCHAR(7) NULL"))
            elif engine.dialect.name == 'postgresql':
                exists = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='budgets' AND column_name='start_month'")).fetchone()
                if not exists:
                    conn.execute(text("ALTER TABLE budgets ADD COLUMN start_month VARCHAR(7)"))
            conn.commit()
        except Exception as e:
            print(f"[database] Warning: could not ensure start_month column in budgets: {e}")


def init_db():
    """Initialize database tables"""
    from models import Base
    try:
        Base.metadata.create_all(bind=engine)
    except OperationalError as exc:
        # Multi-worker startup can race during first table creation; ignore benign
        # "already exists" errors and continue with column ensures.
        err_text = str(exc).lower()
        if "already exists" not in err_text and "1050" not in err_text:
            raise
    ensure_user_role_column()
    ensure_user_permissions_column()
    ensure_user_federation_columns()
    ensure_user_mfa_columns()
    ensure_bootstrap_admin()
    ensure_asset_balance_column()
    ensure_asset_income_column()
    ensure_asset_emergency_fund_column()
    ensure_asset_loan_emi_linked_column()
    ensure_liability_loan_columns()
    ensure_liability_credit_card_columns()
    ensure_integration_oauth_columns()
    ensure_investment_monthly_sip_column()
    ensure_investment_annual_growth_rate_column()
    ensure_investment_start_date_column()
    ensure_investment_goal_id_column()
    ensure_transaction_recurring_column()
    ensure_transaction_idempotency_key_column()
    ensure_transaction_amount_decimal_column()
    ensure_budget_period_column()
    ensure_budget_recurring_column()
    ensure_budget_start_month_column()
    ensure_transaction_spread_over_year_column()
    ensure_document_folder_columns()
    ensure_document_statement_columns()
    ensure_goal_target_date_column()
