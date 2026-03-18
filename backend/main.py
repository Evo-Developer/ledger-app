from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List, Optional
import json

from database import get_db, init_db, engine
from models import User, Transaction, Budget, Goal, Integration, AuditLog, Base
from schemas import (
    UserCreate, User as UserSchema, Transaction as TransactionSchema,
    TransactionCreate, TransactionUpdate, Budget as BudgetSchema,
    BudgetCreate, BudgetUpdate, Goal as GoalSchema, GoalCreate, GoalUpdate,
    Integration as IntegrationSchema, IntegrationCreate, IntegrationUpdate,
    AuditLog as AuditLogSchema, Token, DashboardStats, TransactionFilter,
    AuditLogFilter, LoginRequest
)
from auth import (
    get_password_hash, authenticate_user, create_access_token,
    get_current_active_user, ACCESS_TOKEN_EXPIRE_MINUTES,
    get_client_ip, check_registration_rate_limit
)

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Ledger Finance API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Helper function to log audit
def log_audit(db: Session, user_id: int, action: str, entity_type: str, 
               entity_id: str, description: str, details: dict = None, 
               user_agent: str = None):
    """
    Log audit trail entry
    Handles datetime serialization for JSON
    """
    # Convert details to JSON-serializable format
    if details:
        import datetime
        def convert_datetime(obj):
            if isinstance(obj, (datetime.datetime, datetime.date)):
                return obj.isoformat()
            return obj
        
        # Convert any datetime objects to strings
        serializable_details = {}
        for key, value in details.items():
            serializable_details[key] = convert_datetime(value)
        details_json = json.dumps(serializable_details)
    else:
        details_json = None
    
    audit_log = AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        description=description,
        details=details_json,
        user_agent=user_agent
    )
    db.add(audit_log)
    db.commit()


# ==================== Authentication Endpoints ====================

@app.post("/api/auth/register", response_model=UserSchema)
async def register(user: UserCreate, request: Request, db: Session = Depends(get_db)):
    """Register a new user"""
    # Get client IP
    client_ip = get_client_ip(request)
    
    # Check rate limit
    if not check_registration_rate_limit(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many registration attempts. Please try again later."
        )
    
    # Check if user exists
    db_user = db.query(User).filter(
        (User.email == user.email) | (User.username == user.username)
    ).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email or username already registered")
    
    # Create new user
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Log audit
    log_audit(db, db_user.id, "create", "user", db_user.id, 
              f"User registered: {user.username}")
    
    return db_user


@app.post("/api/auth/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Login and get access token"""
    # Get client IP
    client_ip = get_client_ip(request) if request else "unknown"
    
    # Authenticate user (includes rate limiting)
    user = authenticate_user(db, form_data.username, form_data.password, client_ip)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/api/auth/me", response_model=UserSchema)
def read_users_me(current_user: User = Depends(get_current_active_user)):
    """Get current user"""
    return current_user


# ==================== Transaction Endpoints ====================

@app.get("/api/transactions", response_model=List[TransactionSchema])
def get_transactions(
    skip: int = 0, 
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all transactions for current user"""
    transactions = db.query(Transaction).filter(
        Transaction.user_id == current_user.id
    ).order_by(Transaction.date.desc()).offset(skip).limit(limit).all()
    return transactions


@app.post("/api/transactions", response_model=TransactionSchema)
def create_transaction(
    transaction: TransactionCreate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new transaction"""
    db_transaction = Transaction(
        **transaction.dict(),
        user_id=current_user.id
    )
    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)
    
    # Log audit
    log_audit(db, current_user.id, "create", "transaction", db_transaction.id,
              f"Created transaction: {transaction.description}",
              details=transaction.dict(),
              user_agent=request.headers.get("user-agent"))
    
    return db_transaction


@app.put("/api/transactions/{transaction_id}", response_model=TransactionSchema)
def update_transaction(
    transaction_id: int,
    transaction: TransactionUpdate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update a transaction"""
    db_transaction = db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.user_id == current_user.id
    ).first()
    
    if not db_transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    if db_transaction.synced:
        raise HTTPException(status_code=400, detail="Cannot edit synced transactions")
    
    old_data = {
        "description": db_transaction.description,
        "amount": db_transaction.amount,
        "category": db_transaction.category
    }
    
    # Update fields
    update_data = transaction.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_transaction, key, value)
    
    db.commit()
    db.refresh(db_transaction)
    
    # Log audit
    log_audit(db, current_user.id, "update", "transaction", transaction_id,
              f"Updated transaction: {db_transaction.description}",
              details={"old": old_data, "new": update_data},
              user_agent=request.headers.get("user-agent"))
    
    return db_transaction


@app.delete("/api/transactions/{transaction_id}")
def delete_transaction(
    transaction_id: int,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a transaction"""
    db_transaction = db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.user_id == current_user.id
    ).first()
    
    if not db_transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    if db_transaction.synced:
        raise HTTPException(status_code=400, detail="Cannot delete synced transactions")
    
    description = db_transaction.description
    db.delete(db_transaction)
    db.commit()
    
    # Log audit
    log_audit(db, current_user.id, "delete", "transaction", transaction_id,
              f"Deleted transaction: {description}",
              user_agent=request.headers.get("user-agent"))
    
    return {"message": "Transaction deleted successfully"}


# ==================== Budget Endpoints ====================

@app.get("/api/budgets", response_model=List[BudgetSchema])
def get_budgets(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all budgets for current user"""
    budgets = db.query(Budget).filter(Budget.user_id == current_user.id).all()
    return budgets


@app.post("/api/budgets", response_model=BudgetSchema)
def create_budget(
    budget: BudgetCreate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new budget"""
    db_budget = Budget(**budget.dict(), user_id=current_user.id)
    db.add(db_budget)
    db.commit()
    db.refresh(db_budget)
    
    log_audit(db, current_user.id, "create", "budget", db_budget.id,
              f"Created budget for {budget.category}",
              details=budget.dict(),
              user_agent=request.headers.get("user-agent"))
    
    return db_budget


# ==================== Goal Endpoints ====================

@app.get("/api/goals", response_model=List[GoalSchema])
def get_goals(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all goals for current user"""
    goals = db.query(Goal).filter(Goal.user_id == current_user.id).all()
    return goals


@app.post("/api/goals", response_model=GoalSchema)
def create_goal(
    goal: GoalCreate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new goal"""
    db_goal = Goal(**goal.dict(), user_id=current_user.id)
    db.add(db_goal)
    db.commit()
    db.refresh(db_goal)
    
    log_audit(db, current_user.id, "create", "goal", db_goal.id,
              f"Created goal: {goal.name}",
              details=goal.dict(),
              user_agent=request.headers.get("user-agent"))
    
    return db_goal


# ==================== Integration Endpoints ====================

@app.get("/api/integrations", response_model=List[IntegrationSchema])
def get_integrations(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all integrations for current user"""
    integrations = db.query(Integration).filter(
        Integration.user_id == current_user.id
    ).all()
    return integrations


@app.post("/api/integrations", response_model=IntegrationSchema)
def create_integration(
    integration: IntegrationCreate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create or update an integration"""
    # Check if integration exists
    db_integration = db.query(Integration).filter(
        Integration.user_id == current_user.id,
        Integration.app_name == integration.app_name
    ).first()
    
    if db_integration:
        # Update existing
        db_integration.connected = True
        db_integration.api_key = integration.api_key
        db_integration.sync_frequency = integration.sync_frequency
        db_integration.last_sync = datetime.utcnow()
        action = "update"
    else:
        # Create new
        db_integration = Integration(
            **integration.dict(),
            user_id=current_user.id,
            connected=True,
            last_sync=datetime.utcnow()
        )
        db.add(db_integration)
        action = "create"
    
    db.commit()
    db.refresh(db_integration)
    
    log_audit(db, current_user.id, action, "integration", db_integration.id,
              f"Connected {integration.app_name}",
              user_agent=request.headers.get("user-agent"))
    
    return db_integration


@app.post("/api/integrations/{app_name}/sync")
def sync_integration(
    app_name: str,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Sync transactions from an integration"""
    integration = db.query(Integration).filter(
        Integration.user_id == current_user.id,
        Integration.app_name == app_name
    ).first()
    
    if not integration or not integration.connected:
        raise HTTPException(status_code=404, detail="Integration not found or not connected")
    
    # Mock sync - in production, this would call actual APIs
    sample_data = {
        "phonepe": [
            {"description": "UPI to Swiggy", "amount": 450, "category": "Food", "type": "expense"},
            {"description": "DTH Recharge", "amount": 299, "category": "Bills", "type": "expense"},
        ],
        "groww": [
            {"description": "Mutual Fund SIP", "amount": 5000, "category": "Investment", "type": "expense"},
        ],
    }
    
    synced_transactions = []
    if app_name in sample_data:
        for trans_data in sample_data[app_name]:
            db_transaction = Transaction(
                user_id=current_user.id,
                synced=True,
                source=app_name,
                date=datetime.utcnow(),
                **trans_data
            )
            db.add(db_transaction)
            synced_transactions.append(trans_data)
    
    integration.last_sync = datetime.utcnow()
    db.commit()
    
    log_audit(db, current_user.id, "sync", "transaction", app_name,
              f"Synced {len(synced_transactions)} transactions from {app_name}",
              details={"count": len(synced_transactions)},
              user_agent=request.headers.get("user-agent"))
    
    return {"message": f"Synced {len(synced_transactions)} transactions", "count": len(synced_transactions)}


# ==================== Audit Log Endpoints ====================

@app.get("/api/audit-logs", response_model=List[AuditLogSchema])
def get_audit_logs(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get audit logs for current user"""
    logs = db.query(AuditLog).filter(
        AuditLog.user_id == current_user.id
    ).order_by(AuditLog.timestamp.desc()).offset(skip).limit(limit).all()
    return logs


# ==================== Dashboard Endpoints ====================

@app.get("/api/dashboard/stats", response_model=DashboardStats)
def get_dashboard_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get dashboard statistics"""
    # Get current month transactions
    now = datetime.utcnow()
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    transactions = db.query(Transaction).filter(
        Transaction.user_id == current_user.id,
        Transaction.date >= start_of_month
    ).all()
    
    income = sum(t.amount for t in transactions if t.type == "income")
    expenses = sum(t.amount for t in transactions if t.type == "expense")
    balance = income - expenses
    savings_rate = (balance / income * 100) if income > 0 else 0
    
    budget_count = db.query(Budget).filter(Budget.user_id == current_user.id).count()
    goal_count = db.query(Goal).filter(Goal.user_id == current_user.id).count()
    
    return DashboardStats(
        total_balance=balance,
        total_income=income,
        total_expenses=expenses,
        savings_rate=round(savings_rate, 1),
        transaction_count=len(transactions),
        budget_count=budget_count,
        goal_count=goal_count
    )


# ==================== Health Check ====================

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
