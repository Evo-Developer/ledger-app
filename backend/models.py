from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text, Enum, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime, date
import enum

Base = declarative_base()


class UserRole(str, enum.Enum):
    SUPERADMIN = "superadmin"
    ADMIN = "admin"
    USER = "user"
    READONLY = "readonly"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    full_name = Column(String(255))
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(32), nullable=False, default=UserRole.USER.value)
    permissions_json = Column(Text, nullable=True)
    identity_provider = Column(String(64), nullable=True)
    external_subject = Column(String(255), nullable=True, index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")
    budgets = relationship("Budget", back_populates="user", cascade="all, delete-orphan")
    goals = relationship("Goal", back_populates="user", cascade="all, delete-orphan")
    investments = relationship("Investment", back_populates="user", cascade="all, delete-orphan")
    liabilities = relationship("Liability", back_populates="user", cascade="all, delete-orphan")
    integrations = relationship("Integration", back_populates="user", cascade="all, delete-orphan")
    assets = relationship("Asset", back_populates="user", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")


class TransactionType(str, enum.Enum):
    INCOME = "income"
    EXPENSE = "expense"


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type = Column(Enum(TransactionType), nullable=False)
    description = Column(String(500), nullable=False)
    amount = Column(Float, nullable=False)
    category = Column(String(100), nullable=False)
    date = Column(DateTime, nullable=False)
    notes = Column(Text)
    recurring = Column(Boolean, default=False)
    spread_over_year = Column(Boolean, default=False)
    synced = Column(Boolean, default=False)
    source = Column(String(100))  # phonepe, groww, manual, etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="transactions")


class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    type = Column(String(100), nullable=True)
    value = Column(Float, nullable=False, default=0.0)
    include_in_balance = Column(Boolean, nullable=False, default=False)
    include_in_income = Column(Boolean, nullable=False, default=False)
    emergency_fund = Column(Boolean, nullable=False, default=False)
    loan_emi_linked = Column(Boolean, nullable=False, default=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="assets")


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    folder = Column(String(255), nullable=False, default="General")
    subfolder = Column(String(255), nullable=True)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(1024), nullable=False)
    content_type = Column(String(255), nullable=True)
    document_type = Column(String(50), nullable=False, default="general")
    frozen_import = Column(Boolean, nullable=False, default=False)
    imported_transaction_count = Column(Integer, nullable=False, default=0)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="documents")


class Budget(Base):
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    category = Column(String(100), nullable=False)
    limit = Column(Float, nullable=False)
    period = Column(String(20), default="monthly", nullable=False)  # 'monthly' or 'yearly'
    recurring = Column(Boolean, nullable=False, default=False)
    start_month = Column(String(7), nullable=True)  # YYYY-MM
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="budgets")


class Goal(Base):
    __tablename__ = "goals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    target = Column(Float, nullable=False)
    current = Column(Float, default=0.0)
    target_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="goals")


class Investment(Base):
    __tablename__ = "investments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    type = Column(String(100), nullable=False)
    amount_invested = Column(Float, nullable=False)
    current_value = Column(Float, nullable=True)
    annual_growth_rate = Column(Float, nullable=True)
    monthly_sip = Column(Boolean, nullable=False, default=False)
    start_date = Column(Date, nullable=True)
    goal_id = Column(Integer, nullable=True)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="investments")


class Liability(Base):
    __tablename__ = "liabilities"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    lender = Column(String(255), nullable=False)
    amount = Column(Float, nullable=False)
    outstanding = Column(Float, nullable=False)
    is_loan = Column(Boolean, nullable=False, default=False)
    liability_type = Column(String(50), nullable=True, default='general')  # general, credit_card, tax
    credit_limit = Column(Float, nullable=True)
    is_paid_off = Column(Boolean, nullable=True, default=False)
    loan_start_date = Column(DateTime, nullable=True)
    loan_tenure_months = Column(Integer, nullable=True)
    interest_rate = Column(Float, nullable=True)
    opportunity_cost_rate = Column(Float, nullable=True)
    monthly_payment = Column(Float, nullable=True)
    linked_asset_id = Column(Integer, ForeignKey("assets.id"), nullable=True)
    due_date = Column(DateTime, nullable=True)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="liabilities")


class Integration(Base):
    __tablename__ = "integrations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    app_name = Column(String(100), nullable=False)  # phonepe, groww, etc.
    connected = Column(Boolean, default=False)
    api_key = Column(String(500))
    account_email = Column(String(255), nullable=True)
    oauth_token = Column(Text, nullable=True)
    sync_frequency = Column(String(50))
    last_sync = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="integrations")


class AuditAction(str, enum.Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    SYNC = "sync"


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(Enum(AuditAction), nullable=False)
    entity_type = Column(String(100), nullable=False)
    entity_id = Column(String(100))
    description = Column(Text)
    details = Column(Text)  # JSON string
    user_agent = Column(String(500))
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="audit_logs")


class AppInsightsMetric(Base):
    __tablename__ = "app_insights_metrics"

    id = Column(Integer, primary_key=True, index=True)
    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Backend (FastAPI) metrics
    backend_active_requests = Column(Integer, default=0)
    backend_errors_5xx = Column(Integer, default=0)
    backend_discards_4xx = Column(Integer, default=0)
    backend_avg_latency_ms = Column(Float, default=0.0)
    backend_requests_total = Column(Integer, default=0)
    backend_memory_mb = Column(Float, default=0.0)
    
    # Frontend (Nginx) metrics
    frontend_active_connections = Column(Integer, default=0)
    frontend_reading = Column(Integer, default=0)
    frontend_writing = Column(Integer, default=0)
    frontend_waiting = Column(Integer, default=0)
    frontend_accepts = Column(Integer, default=0)
    frontend_handled = Column(Integer, default=0)
    frontend_requests_total = Column(Integer, default=0)
    
    # Database (MySQL) metrics
    db_connections = Column(Integer, default=0)
    db_threads_running = Column(Integer, default=0)
    db_errors = Column(Integer, default=0)
    db_total_queries = Column(Integer, default=0)
