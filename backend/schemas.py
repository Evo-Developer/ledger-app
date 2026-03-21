from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime, date
from enum import Enum


class TransactionType(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"


class AuditAction(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    SYNC = "sync"


class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"
    READONLY = "readonly"


# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    password: Optional[str] = None


class User(UserBase):
    id: int
    role: UserRole
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Transaction Schemas
class TransactionBase(BaseModel):
    type: TransactionType
    description: str
    amount: float
    category: str
    date: datetime
    recurring: Optional[bool] = False
    spread_over_year: Optional[bool] = False
    notes: Optional[str] = None


class TransactionCreate(TransactionBase):
    pass


class TransactionUpdate(BaseModel):
    type: Optional[TransactionType] = None
    description: Optional[str] = None
    amount: Optional[float] = None
    category: Optional[str] = None
    date: Optional[datetime] = None
    recurring: Optional[bool] = None
    spread_over_year: Optional[bool] = None
    notes: Optional[str] = None


class Transaction(TransactionBase):
    id: int
    user_id: int
    recurring: bool
    spread_over_year: bool
    synced: bool
    source: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Asset Schemas
class AssetBase(BaseModel):
    name: str
    type: Optional[str] = None
    value: float
    include_in_balance: bool = False
    include_in_income: bool = False
    emergency_fund: bool = False
    loan_emi_linked: bool = False
    description: Optional[str] = None


class AssetCreate(AssetBase):
    pass


class AssetUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    value: Optional[float] = None
    include_in_balance: Optional[bool] = None
    include_in_income: Optional[bool] = None
    emergency_fund: Optional[bool] = None
    loan_emi_linked: Optional[bool] = None
    description: Optional[str] = None


class Asset(AssetBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Document Schemas
class DocumentBase(BaseModel):
    title: str
    folder: Optional[str] = "General"
    subfolder: Optional[str] = None


class DocumentCreate(DocumentBase):
    pass


class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    folder: Optional[str] = None
    subfolder: Optional[str] = None


class Document(DocumentBase):
    id: int
    user_id: int
    file_name: str
    content_type: Optional[str]
    uploaded_at: datetime
    url: str

    class Config:
        from_attributes = True


# Budget Schemas
class BudgetBase(BaseModel):
    category: str
    limit: float
    period: str = "monthly"  # 'monthly' or 'yearly'
    recurring: bool = False
    start_month: Optional[str] = None


class BudgetCreate(BudgetBase):
    pass


class BudgetUpdate(BaseModel):
    category: Optional[str] = None
    limit: Optional[float] = None
    period: Optional[str] = None
    recurring: Optional[bool] = None
    start_month: Optional[str] = None


class Budget(BudgetBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Budget with Spending Schema (for monthly tracking)
class BudgetWithSpending(BudgetBase):
    id: int
    user_id: int
    spent: float
    remaining: float
    percentage_used: float
    is_over_budget: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Goal Schemas
class GoalBase(BaseModel):
    name: str
    target: float
    current: float = 0.0
    target_date: Optional[date] = None


class GoalCreate(GoalBase):
    pass


class GoalUpdate(BaseModel):
    name: Optional[str] = None
    target: Optional[float] = None
    current: Optional[float] = None
    target_date: Optional[date] = None


class Goal(GoalBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Investment Schemas
class InvestmentBase(BaseModel):
    name: str
    type: str
    amount_invested: float
    current_value: Optional[float] = None
    annual_growth_rate: Optional[float] = None
    monthly_sip: bool = False
    notes: Optional[str] = None


class InvestmentCreate(InvestmentBase):
    pass


class InvestmentUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    amount_invested: Optional[float] = None
    current_value: Optional[float] = None
    annual_growth_rate: Optional[float] = None
    monthly_sip: Optional[bool] = None
    notes: Optional[str] = None


class Investment(InvestmentBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Liability Schemas
class LiabilityBase(BaseModel):
    lender: str
    amount: float
    outstanding: float
    is_loan: bool = False
    loan_start_date: Optional[datetime] = None
    loan_tenure_months: Optional[int] = None
    interest_rate: Optional[float] = None
    opportunity_cost_rate: Optional[float] = None
    monthly_payment: Optional[float] = None
    linked_asset_id: Optional[int] = None
    due_date: Optional[datetime] = None
    notes: Optional[str] = None


class LiabilityCreate(LiabilityBase):
    pass


class LiabilityUpdate(BaseModel):
    lender: Optional[str] = None
    amount: Optional[float] = None
    outstanding: Optional[float] = None
    is_loan: Optional[bool] = None
    loan_start_date: Optional[datetime] = None
    loan_tenure_months: Optional[int] = None
    interest_rate: Optional[float] = None
    opportunity_cost_rate: Optional[float] = None
    monthly_payment: Optional[float] = None
    linked_asset_id: Optional[int] = None
    due_date: Optional[datetime] = None
    notes: Optional[str] = None


class Liability(LiabilityBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Integration Schemas
class IntegrationBase(BaseModel):
    app_name: str
    sync_frequency: Optional[str] = "daily"


class IntegrationCreate(IntegrationBase):
    api_key: Optional[str] = None


class IntegrationUpdate(BaseModel):
    connected: Optional[bool] = None
    api_key: Optional[str] = None
    account_email: Optional[str] = None
    sync_frequency: Optional[str] = None


class Integration(IntegrationBase):
    id: int
    user_id: int
    connected: bool
    account_email: Optional[str] = None
    last_sync: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


# Audit Log Schemas
class AuditLogBase(BaseModel):
    action: AuditAction
    entity_type: str
    entity_id: Optional[str] = None
    description: Optional[str] = None
    details: Optional[str] = None


class AuditLogCreate(AuditLogBase):
    user_agent: Optional[str] = None


class AuditLog(AuditLogBase):
    id: int
    user_id: int
    user_agent: Optional[str] = None
    timestamp: datetime

    class Config:
        from_attributes = True


# Authentication Schemas
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str


class UserRoleUpdate(BaseModel):
    role: UserRole


class UserStatusUpdate(BaseModel):
    is_active: bool


class ExpenseReportEmailRequest(BaseModel):
    recipient_email: EmailStr
    report_month: Optional[str] = None


class ExpenseReportEmailResponse(BaseModel):
    message: str
    recipient_email: EmailStr
    report_month: str


class IntegrationAuthUrlResponse(BaseModel):
    auth_url: str


class DataImportResponse(BaseModel):
    message: str
    created: int
    updated: int
    skipped: int


# Dashboard Stats
class DashboardStats(BaseModel):
    total_balance: float
    total_income: float
    total_expenses: float
    savings_rate: float
    transaction_count: int
    budget_count: int
    goal_count: int
    budgets_with_spending: Optional[List['BudgetWithSpending']] = None
    total_budget_limit: float = 0.0
    total_budget_spent: float = 0.0
    budget_remaining: float = 0.0
    budgets_over_limit: int = 0


# Filter Schemas
class TransactionFilter(BaseModel):
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    type: Optional[TransactionType] = None
    category: Optional[str] = None
    source: Optional[str] = None
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    search: Optional[str] = None


class AuditLogFilter(BaseModel):
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    action: Optional[AuditAction] = None
    entity_type: Optional[str] = None


# Update forward references for DashboardStats
DashboardStats.model_rebuild()
