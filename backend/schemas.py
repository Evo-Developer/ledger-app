from pydantic import BaseModel, EmailStr, Field, field_validator, field_serializer, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from enum import Enum
from decimal import Decimal, ROUND_HALF_UP


class TransactionType(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"


class AuditAction(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    SYNC = "sync"


class UserRole(str, Enum):
    SUPERADMIN = "superadmin"
    ADMIN = "admin"
    USER = "user"
    READONLY = "readonly"


class UserPermissions(BaseModel):
    tabs: List[str] = Field(default_factory=list)
    pages: List[str] = Field(default_factory=list)
    fields: List[str] = Field(default_factory=list)
    permissions: List[str] = Field(default_factory=list)


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
    permissions: UserPermissions = Field(default_factory=UserPermissions)
    identity_provider: Optional[str] = None
    external_subject: Optional[str] = None
    mfa_enabled: bool = False
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Transaction Schemas
class TransactionBase(BaseModel):
    type: TransactionType
    description: str
    amount: Decimal
    category: str
    date: datetime
    recurring: Optional[bool] = False
    spread_over_year: Optional[bool] = False
    notes: Optional[str] = None

    @field_validator("amount")
    @classmethod
    def _normalize_amount(cls, value: Decimal) -> Decimal:
        if value is None:
            return value
        normalized = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if normalized <= 0:
            raise ValueError("amount must be greater than 0")
        return normalized

    @field_serializer("amount")
    def _serialize_amount(self, value: Decimal) -> float:
        return float(value)


class TransactionCreate(TransactionBase):
    pass


class TransactionUpdate(BaseModel):
    type: Optional[TransactionType] = None
    description: Optional[str] = None
    amount: Optional[Decimal] = None
    category: Optional[str] = None
    date: Optional[datetime] = None
    recurring: Optional[bool] = None
    spread_over_year: Optional[bool] = None
    notes: Optional[str] = None

    @field_validator("amount")
    @classmethod
    def _normalize_amount(cls, value: Optional[Decimal]) -> Optional[Decimal]:
        if value is None:
            return value
        normalized = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if normalized <= 0:
            raise ValueError("amount must be greater than 0")
        return normalized


class TransactionReversalRequest(BaseModel):
    reason: Optional[str] = None


class Transaction(TransactionBase):
    id: int
    user_id: int
    recurring: bool
    spread_over_year: bool
    synced: bool
    source: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


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

    model_config = ConfigDict(from_attributes=True)


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
    frozen_import: Optional[bool] = None


class Document(DocumentBase):
    id: int
    user_id: int
    file_name: str
    content_type: Optional[str]
    document_type: str = "general"
    frozen_import: bool = False
    imported_transaction_count: int = 0
    uploaded_at: datetime
    url: str

    model_config = ConfigDict(from_attributes=True)


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

    model_config = ConfigDict(from_attributes=True)


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

    model_config = ConfigDict(from_attributes=True)


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

    model_config = ConfigDict(from_attributes=True)


class EventBase(BaseModel):
    title: str
    details: Optional[str] = None
    event_type: Optional[str] = None
    start_date: date
    end_date: Optional[date] = None
    reminder_enabled: bool = False
    reminder_days_before: int = 1

    @field_validator("reminder_days_before")
    @classmethod
    def _validate_reminder_days(cls, value: int) -> int:
        if value < 0 or value > 365:
            raise ValueError("reminder_days_before must be between 0 and 365")
        return value

    @field_validator("end_date")
    @classmethod
    def _validate_end_date(cls, value: Optional[date], info):
        start_date = info.data.get("start_date") if info and info.data else None
        if value is not None and start_date is not None and value < start_date:
            raise ValueError("end_date cannot be before start_date")
        return value


class EventCreate(EventBase):
    pass


class EventUpdate(BaseModel):
    title: Optional[str] = None
    details: Optional[str] = None
    event_type: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    reminder_enabled: Optional[bool] = None
    reminder_days_before: Optional[int] = None

    @field_validator("reminder_days_before")
    @classmethod
    def _validate_update_reminder_days(cls, value: Optional[int]) -> Optional[int]:
        if value is None:
            return value
        if value < 0 or value > 365:
            raise ValueError("reminder_days_before must be between 0 and 365")
        return value


class Event(EventBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Investment Schemas
class InvestmentBase(BaseModel):
    name: str
    type: str
    amount_invested: float
    current_value: Optional[float] = None
    annual_growth_rate: Optional[float] = None
    monthly_sip: bool = False
    start_date: Optional[date] = None
    goal_id: Optional[int] = None
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
    start_date: Optional[date] = None
    goal_id: Optional[int] = None
    notes: Optional[str] = None


class Investment(InvestmentBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Liability Schemas
class LiabilityBase(BaseModel):
    lender: str
    amount: float
    outstanding: float
    is_loan: bool = False
    liability_type: Optional[str] = 'general'  # general, credit_card, tax
    credit_limit: Optional[float] = None
    is_paid_off: Optional[bool] = False
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
    liability_type: Optional[str] = None
    credit_limit: Optional[float] = None
    is_paid_off: Optional[bool] = None
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

    model_config = ConfigDict(from_attributes=True)


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

    model_config = ConfigDict(from_attributes=True)


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

    model_config = ConfigDict(from_attributes=True)


class LedgerEntry(BaseModel):
    id: int
    transaction_id: int
    user_id: int
    entry_type: str
    account_code: str
    amount: Decimal
    created_at: datetime

    @field_serializer("amount")
    def _serialize_amount(self, value: Decimal) -> float:
        return float(value)

    model_config = ConfigDict(from_attributes=True)


# Authentication Schemas
class Token(BaseModel):
    access_token: Optional[str] = None
    token_type: Optional[str] = None
    mfa_required: bool = False
    mfa_message: Optional[str] = None


class TokenData(BaseModel):
    username: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str
    mfa_code: Optional[str] = None


class MfaSetupResponse(BaseModel):
    enabled: bool
    pending_setup: bool = False
    manual_entry_key: Optional[str] = None
    otpauth_uri: Optional[str] = None


class MfaVerifyRequest(BaseModel):
    code: str


class MfaDisableRequest(BaseModel):
    current_password: str
    code: str


class UserProfileUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None


class UserPasswordChange(BaseModel):
    current_password: str
    new_password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class ExternalRBACProvisionRequest(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: UserRole = UserRole.USER
    is_active: bool = True
    permissions: Optional[UserPermissions] = None
    create_if_missing: bool = True
    identity_provider: Optional[str] = None
    external_subject: Optional[str] = None


class FederatedClaimSyncRequest(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    groups: List[str] = Field(default_factory=list)
    claims: Dict[str, Any] = Field(default_factory=dict)
    role_hint: Optional[UserRole] = None
    permissions_override: Optional[UserPermissions] = None
    create_if_missing: bool = True
    identity_provider: Optional[str] = None
    external_subject: Optional[str] = None


class UserRoleUpdate(BaseModel):
    role: UserRole


class UserPermissionsUpdate(BaseModel):
    permissions: UserPermissions


class UserStatusUpdate(BaseModel):
    is_active: bool


class AdminResetRequest(BaseModel):
    password: str


class AdminResetResponse(BaseModel):
    message: str
    transactions_deleted: int = 0
    budgets_deleted: int = 0
    goals_deleted: int = 0
    investments_deleted: int = 0
    liabilities_deleted: int = 0
    assets_deleted: int = 0
    documents_deleted: int = 0
    integrations_deleted: int = 0
    files_deleted: int = 0


class FirewallStatusUpdateRequest(BaseModel):
    internet_enabled: bool


class FirewallStatusResponse(BaseModel):
    internet_enabled: bool
    inbound_blocked: bool
    outbound_blocked: bool
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None


class FirewallConnectivityTestRequest(BaseModel):
    url: str


class FirewallConnectivityTestResponse(BaseModel):
    url: str
    internet_enabled: bool
    success: bool
    message: str
    status_code: Optional[int] = None
    latency_ms: Optional[float] = None


class ProxySettings(BaseModel):
    enabled: bool = False
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    bypass: Optional[str] = None


class ActiveDirectorySettings(BaseModel):
    enabled: bool = False
    server: Optional[str] = None
    domain: Optional[str] = None
    base_dn: Optional[str] = None
    group_dn: Optional[str] = None
    bind_user: Optional[str] = None
    use_ssl: bool = True


class SmtpSettings(BaseModel):
    enabled: bool = False
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    from_email: Optional[str] = None
    use_tls: bool = True


class NetworkAdminSettingsUpdateRequest(BaseModel):
    ntp_servers: List[str] = Field(default_factory=list)
    dns_servers: List[str] = Field(default_factory=list)
    proxy: ProxySettings = Field(default_factory=ProxySettings)
    active_directory: ActiveDirectorySettings = Field(default_factory=ActiveDirectorySettings)
    smtp: SmtpSettings = Field(default_factory=SmtpSettings)


class NetworkAdminSettingsResponse(NetworkAdminSettingsUpdateRequest):
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None


class ExternalConnectivityService(BaseModel):
    id: str
    name: str
    category: str
    protocol: str
    enabled: bool = True
    url: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    timeout_sec: float = 5.0
    method: Optional[str] = "GET"
    community: Optional[str] = "public"
    oid: Optional[str] = "1.3.6.1.2.1.1.1.0"
    notes: Optional[str] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None
    last_test: Optional[Dict[str, Any]] = None


class ExternalConnectivityServiceUpdate(BaseModel):
    name: str
    category: str
    protocol: str
    enabled: bool = True
    url: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    timeout_sec: float = 5.0
    method: Optional[str] = "GET"
    community: Optional[str] = "public"
    oid: Optional[str] = "1.3.6.1.2.1.1.1.0"
    notes: Optional[str] = None


class ExternalConnectivityServiceCreate(ExternalConnectivityServiceUpdate):
    pass


class ExternalConnectivityTestRequest(BaseModel):
    protocol: str
    url: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    timeout_sec: float = 5.0
    method: Optional[str] = "GET"
    community: Optional[str] = "public"
    oid: Optional[str] = "1.3.6.1.2.1.1.1.0"


class ExternalConnectivityTestResponse(BaseModel):
    service_id: Optional[str] = None
    protocol: str
    success: bool
    message: str
    status_code: Optional[int] = None
    latency_ms: Optional[float] = None
    response_preview: Optional[str] = None


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


class GmailBankAlertTransaction(BaseModel):
    type: str
    amount: float
    description: str
    category: str
    date: str


class GmailBankAlertSyncResult(BaseModel):
    message: str
    imported: int
    skipped: int
    errors: int
    transactions: List[GmailBankAlertTransaction] = []


class StatementImportTransaction(BaseModel):
    date: str
    description: str
    amount: float
    type: str
    category: str


class StatementImportResponse(BaseModel):
    message: str
    detected: int
    imported: int
    skipped: int
    liabilities_created: int = 0
    liabilities_updated: int = 0
    document: Optional[Document] = None
    transactions: List[StatementImportTransaction] = []


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
    upcoming_event_count: int = 0
    next_upcoming_event: Optional[str] = None


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
