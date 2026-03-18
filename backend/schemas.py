from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class TransactionType(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"


class AuditAction(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    SYNC = "sync"


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
    notes: Optional[str] = None


class TransactionCreate(TransactionBase):
    pass


class TransactionUpdate(BaseModel):
    type: Optional[TransactionType] = None
    description: Optional[str] = None
    amount: Optional[float] = None
    category: Optional[str] = None
    date: Optional[datetime] = None
    notes: Optional[str] = None


class Transaction(TransactionBase):
    id: int
    user_id: int
    synced: bool
    source: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Budget Schemas
class BudgetBase(BaseModel):
    category: str
    limit: float


class BudgetCreate(BudgetBase):
    pass


class BudgetUpdate(BaseModel):
    category: Optional[str] = None
    limit: Optional[float] = None


class Budget(BudgetBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Goal Schemas
class GoalBase(BaseModel):
    name: str
    target: float
    current: float = 0.0


class GoalCreate(GoalBase):
    pass


class GoalUpdate(BaseModel):
    name: Optional[str] = None
    target: Optional[float] = None
    current: Optional[float] = None


class Goal(GoalBase):
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
    sync_frequency: Optional[str] = None


class Integration(IntegrationBase):
    id: int
    user_id: int
    connected: bool
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


# Dashboard Stats
class DashboardStats(BaseModel):
    total_balance: float
    total_income: float
    total_expenses: float
    savings_rate: float
    transaction_count: int
    budget_count: int
    goal_count: int


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
