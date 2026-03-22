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
    Base.metadata.create_all(bind=engine)
    ensure_user_role_column()
    ensure_bootstrap_admin()
    ensure_asset_balance_column()
    ensure_asset_income_column()
    ensure_asset_emergency_fund_column()
    ensure_asset_loan_emi_linked_column()
    ensure_liability_loan_columns()
    ensure_integration_oauth_columns()
    ensure_investment_monthly_sip_column()
    ensure_investment_annual_growth_rate_column()
    ensure_investment_start_date_column()
    ensure_transaction_recurring_column()
    ensure_budget_period_column()
    ensure_budget_recurring_column()
    ensure_budget_start_month_column()
    ensure_transaction_spread_over_year_column()
    ensure_document_folder_columns()
    ensure_document_statement_columns()
    ensure_goal_target_date_column()
