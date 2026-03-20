from fastapi import FastAPI, Depends, HTTPException, status, Request, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List, Optional
import json
import os
from uuid import uuid4

from database import get_db, init_db, engine
from models import User, Transaction, Asset, Document, Budget, Goal, Investment, Liability, Integration, AuditLog, Base
from schemas import (
    UserCreate, User as UserSchema, Transaction as TransactionSchema,
    Asset as AssetSchema, AssetCreate, AssetUpdate,
    Document as DocumentSchema,
    TransactionCreate, TransactionUpdate, Budget as BudgetSchema,
    BudgetCreate, BudgetUpdate, Goal as GoalSchema, GoalCreate, GoalUpdate,
    Investment as InvestmentSchema, InvestmentCreate, InvestmentUpdate,
    Liability as LiabilitySchema, LiabilityCreate, LiabilityUpdate,
    Integration as IntegrationSchema, IntegrationCreate, IntegrationUpdate,
    AuditLog as AuditLogSchema, Token, DashboardStats, TransactionFilter,
    AuditLogFilter, LoginRequest
)
from auth import (
    get_password_hash, authenticate_user, create_access_token,
    get_current_active_user, ACCESS_TOKEN_EXPIRE_MINUTES,
    get_client_ip, check_registration_rate_limit
)
from integration_providers import get_provider

import csv
import io

from models import TransactionType

# Create tables and ensure migrations
init_db()

app = FastAPI(title="Ledger Finance API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static upload directory
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount('/uploads', StaticFiles(directory=UPLOAD_DIR), name='uploads')


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

        def make_serializable(obj):
            if isinstance(obj, (datetime.datetime, datetime.date)):
                return obj.isoformat()
            if isinstance(obj, dict):
                return {k: make_serializable(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [make_serializable(v) for v in obj]
            return obj

        serializable_details = make_serializable(details)
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
    request: Request,
    db: Session = Depends(get_db)
):
    """Login and get access token"""
    # Get client IP
    client_ip = get_client_ip(request)

    # Support both application/x-www-form-urlencoded and application/json credentials
    username = None
    password = None

    content_type = (request.headers.get("content-type") or "").split(";")[0].strip().lower()
    if content_type == "application/json":
        payload = await request.json()
        username = payload.get("username")
        password = payload.get("password")
    else:
        form_data = await request.form()
        username = form_data.get("username")
        password = form_data.get("password")

    if not username or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username and password are required"
        )

    # Authenticate user
    user = authenticate_user(db, username, password, client_ip)
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


@app.post("/api/transactions/upload", response_model=List[TransactionSchema])
def upload_transactions_csv(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Upload transactions from a CSV file.
    Required columns: type, description, amount, category, date
    Optional columns: notes, recurring (true/false)
    """
    try:
        data = file.file.read().decode('utf-8-sig')
        csv_reader = csv.DictReader(io.StringIO(data))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read CSV file: {e}")

    if not csv_reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV file has no header")

    required_cols = {'type', 'description', 'amount', 'category', 'date'}
    missing = required_cols - set([c.strip() for c in csv_reader.fieldnames if c])
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing required columns: {', '.join(missing)}")

    created_transactions = []
    for idx, row in enumerate(csv_reader, start=1):
        if not row.get('type') or not row.get('description') or not row.get('amount') or not row.get('category') or not row.get('date'):
            continue

        tx_type = row.get('type', '').strip().lower()
        if tx_type not in ('income', 'expense'):
            raise HTTPException(status_code=400, detail=f"Invalid transaction type on row {idx}: {tx_type}")

        try:
            amount = float(row.get('amount'))
        except Exception:
            raise HTTPException(status_code=400, detail=f"Invalid amount on row {idx}: {row.get('amount')}")

        notes = row.get('notes', '').strip() if row.get('notes') else ''
        recurring_value = row.get('recurring', '').strip().lower()
        recurring = recurring_value in ('1', 'true', 'yes', 'y')

        try:
            transaction_date = datetime.fromisoformat(row.get('date').strip()) if 'T' in row.get('date').strip() else datetime.strptime(row.get('date').strip(), '%Y-%m-%d')
        except Exception:
            raise HTTPException(status_code=400, detail=f"Invalid date format on row {idx}; expected YYYY-MM-DD or ISO format")

        db_transaction = Transaction(
            user_id=current_user.id,
            type=TransactionType(tx_type),
            description=row.get('description').strip(),
            amount=amount,
            category=row.get('category').strip(),
            date=transaction_date,
            notes=notes,
            recurring=recurring,
            synced=False,
            source='csv'
        )

        db.add(db_transaction)
        created_transactions.append(db_transaction)

    db.commit()

    for tx in created_transactions:
        db.refresh(tx)

    return created_transactions


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
    try:
        update_data = transaction.dict(exclude_unset=True)

        # Replace string values and date field with parsed datetime in case incoming API sends date string
        if 'date' in update_data and isinstance(update_data['date'], str):
            from datetime import datetime
            update_data['date'] = datetime.fromisoformat(update_data['date'])

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
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Update transaction error: {type(exc).__name__}: {exc}")


@app.get("/api/assets", response_model=List[AssetSchema])
def get_assets(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    return db.query(Asset).filter(Asset.user_id == current_user.id).all()


@app.post("/api/assets", response_model=AssetSchema)
def create_asset(
    asset: AssetCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    db_asset = Asset(**asset.dict(), user_id=current_user.id)
    db.add(db_asset)
    db.commit()
    db.refresh(db_asset)
    return db_asset


@app.put("/api/assets/{asset_id}", response_model=AssetSchema)
def update_asset(
    asset_id: int,
    asset: AssetUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    db_asset = db.query(Asset).filter(Asset.id == asset_id, Asset.user_id == current_user.id).first()
    if not db_asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    data = asset.dict(exclude_unset=True)
    for key, value in data.items():
        setattr(db_asset, key, value)

    db.commit()
    db.refresh(db_asset)
    return db_asset


@app.delete("/api/assets/{asset_id}")
def delete_asset(
    asset_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    db_asset = db.query(Asset).filter(Asset.id == asset_id, Asset.user_id == current_user.id).first()
    if not db_asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    db.delete(db_asset)
    db.commit()
    return {"message": "Asset deleted successfully"}


@app.get("/api/documents", response_model=List[DocumentSchema])
def get_documents(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    docs = db.query(Document).filter(Document.user_id == current_user.id).all()
    return [
        DocumentSchema(
            id=d.id,
            user_id=d.user_id,
            title=d.title,
            folder=d.folder or "General",
            subfolder=d.subfolder,
            file_name=d.file_name,
            content_type=d.content_type,
            uploaded_at=d.uploaded_at,
            url=f"/uploads/{os.path.basename(d.file_path)}"
        ) for d in docs
    ]


@app.post("/api/documents", response_model=DocumentSchema)
def upload_document(
    title: str = Form(...),
    folder: str = Form("General"),
    subfolder: str = Form(""),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    filename = f"{uuid4().hex}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, filename)
    with open(file_path, "wb") as f:
        f.write(file.file.read())

    db_doc = Document(
        user_id=current_user.id,
        title=title,
        folder=folder.strip() or "General",
        subfolder=subfolder.strip() or None,
        file_name=file.filename,
        file_path=file_path,
        content_type=file.content_type,
    )
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)

    return DocumentSchema(
        id=db_doc.id,
        user_id=db_doc.user_id,
        title=db_doc.title,
        folder=db_doc.folder or "General",
        subfolder=db_doc.subfolder,
        file_name=db_doc.file_name,
        content_type=db_doc.content_type,
        uploaded_at=db_doc.uploaded_at,
        url=f"/uploads/{os.path.basename(db_doc.file_path)}"
    )


@app.delete("/api/documents/{document_id}")
def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    db_doc = db.query(Document).filter(Document.id == document_id, Document.user_id == current_user.id).first()
    if not db_doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if os.path.exists(db_doc.file_path):
        os.remove(db_doc.file_path)

    db.delete(db_doc)
    db.commit()
    return {"message": "Document deleted successfully"}


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


@app.put("/api/budgets/{budget_id}", response_model=BudgetSchema)
def update_budget(
    budget_id: int,
    budget_update: BudgetUpdate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update an existing budget"""
    db_budget = db.query(Budget).filter(
        Budget.user_id == current_user.id,
        Budget.id == budget_id
    ).first()

    if not db_budget:
        raise HTTPException(status_code=404, detail="Budget not found")

    for field, value in budget_update.dict(exclude_unset=True).items():
        setattr(db_budget, field, value)

    db.commit()
    db.refresh(db_budget)

    log_audit(db, current_user.id, "update", "budget", db_budget.id,
              f"Updated budget for {db_budget.category}",
              details=budget_update.dict(exclude_unset=True),
              user_agent=request.headers.get("user-agent"))

    return db_budget


@app.delete("/api/budgets/{budget_id}", response_model=BudgetSchema)
def delete_budget(
    budget_id: int,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a budget"""
    db_budget = db.query(Budget).filter(
        Budget.user_id == current_user.id,
        Budget.id == budget_id
    ).first()

    if not db_budget:
        raise HTTPException(status_code=404, detail="Budget not found")

    db.delete(db_budget)
    db.commit()

    log_audit(db, current_user.id, "delete", "budget", budget_id,
              f"Deleted budget for {db_budget.category}",
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


@app.put("/api/goals/{goal_id}", response_model=GoalSchema)
def update_goal(
    goal_id: int,
    goal_update: GoalUpdate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update an existing goal"""
    db_goal = db.query(Goal).filter(
        Goal.user_id == current_user.id,
        Goal.id == goal_id
    ).first()

    if not db_goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    for field, value in goal_update.dict(exclude_unset=True).items():
        setattr(db_goal, field, value)

    db.commit()
    db.refresh(db_goal)

    log_audit(db, current_user.id, "update", "goal", db_goal.id,
              f"Updated goal: {db_goal.name}",
              details=goal_update.dict(exclude_unset=True),
              user_agent=request.headers.get("user-agent"))

    return db_goal


@app.delete("/api/goals/{goal_id}", response_model=GoalSchema)
def delete_goal(
    goal_id: int,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a goal"""
    db_goal = db.query(Goal).filter(
        Goal.user_id == current_user.id,
        Goal.id == goal_id
    ).first()

    if not db_goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    db.delete(db_goal)
    db.commit()

    log_audit(db, current_user.id, "delete", "goal", goal_id,
              f"Deleted goal: {db_goal.name}",
              user_agent=request.headers.get("user-agent"))

    return db_goal


# ==================== Investment Endpoints ====================

@app.get("/api/investments", response_model=List[InvestmentSchema])
def get_investments(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all investments for current user"""
    return db.query(Investment).filter(Investment.user_id == current_user.id).all()


@app.post("/api/investments", response_model=InvestmentSchema)
def create_investment(
    investment: InvestmentCreate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new investment record"""
    db_investment = Investment(**investment.dict(), user_id=current_user.id)
    db.add(db_investment)
    db.commit()
    db.refresh(db_investment)
    
    log_audit(db, current_user.id, "create", "investment", db_investment.id,
              f"Added investment: {investment.name}",
              details=investment.dict(),
              user_agent=request.headers.get("user-agent"))
    
    return db_investment


@app.put("/api/investments/{investment_id}", response_model=InvestmentSchema)
def update_investment(
    investment_id: int,
    investment_update: InvestmentUpdate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update an existing investment"""
    db_investment = db.query(Investment).filter(
        Investment.user_id == current_user.id,
        Investment.id == investment_id
    ).first()

    if not db_investment:
        raise HTTPException(status_code=404, detail="Investment not found")

    for field, value in investment_update.dict(exclude_unset=True).items():
        setattr(db_investment, field, value)

    db.commit()
    db.refresh(db_investment)

    log_audit(db, current_user.id, "update", "investment", db_investment.id,
              f"Updated investment: {db_investment.name}",
              details=investment_update.dict(exclude_unset=True),
              user_agent=request.headers.get("user-agent"))

    return db_investment


@app.delete("/api/investments/{investment_id}", response_model=InvestmentSchema)
def delete_investment(
    investment_id: int,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete an investment record"""
    db_investment = db.query(Investment).filter(
        Investment.user_id == current_user.id,
        Investment.id == investment_id
    ).first()

    if not db_investment:
        raise HTTPException(status_code=404, detail="Investment not found")

    db.delete(db_investment)
    db.commit()

    log_audit(db, current_user.id, "delete", "investment", investment_id,
              f"Deleted investment: {db_investment.name}",
              user_agent=request.headers.get("user-agent"))

    return db_investment


# ==================== Liability Endpoints ====================

@app.get("/api/liabilities", response_model=List[LiabilitySchema])
def get_liabilities(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all liabilities for current user"""
    return db.query(Liability).filter(Liability.user_id == current_user.id).all()


@app.post("/api/liabilities", response_model=LiabilitySchema)
def create_liability(
    liability: LiabilityCreate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new liability record"""
    db_liability = Liability(**liability.dict(), user_id=current_user.id)
    db.add(db_liability)
    db.commit()
    db.refresh(db_liability)

    log_audit(db, current_user.id, "create", "liability", db_liability.id,
              f"Added liability: {liability.lender}",
              details=liability.dict(),
              user_agent=request.headers.get("user-agent"))

    return db_liability


@app.put("/api/liabilities/{liability_id}", response_model=LiabilitySchema)
def update_liability(
    liability_id: int,
    liability_update: LiabilityUpdate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update an existing liability"""
    db_liability = db.query(Liability).filter(
        Liability.user_id == current_user.id,
        Liability.id == liability_id
    ).first()

    if not db_liability:
        raise HTTPException(status_code=404, detail="Liability not found")

    for field, value in liability_update.dict(exclude_unset=True).items():
        setattr(db_liability, field, value)

    db.commit()
    db.refresh(db_liability)

    log_audit(db, current_user.id, "update", "liability", db_liability.id,
              f"Updated liability: {db_liability.lender}",
              details=liability_update.dict(exclude_unset=True),
              user_agent=request.headers.get("user-agent"))

    return db_liability


@app.delete("/api/liabilities/{liability_id}", response_model=LiabilitySchema)
def delete_liability(
    liability_id: int,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a liability record"""
    db_liability = db.query(Liability).filter(
        Liability.user_id == current_user.id,
        Liability.id == liability_id
    ).first()

    if not db_liability:
        raise HTTPException(status_code=404, detail="Liability not found")

    db.delete(db_liability)
    db.commit()

    log_audit(db, current_user.id, "delete", "liability", liability_id,
              f"Deleted liability: {db_liability.lender}",
              user_agent=request.headers.get("user-agent"))

    return db_liability


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


@app.put("/api/integrations/{app_name}", response_model=IntegrationSchema)
def update_integration(
    app_name: str,
    integration_update: IntegrationUpdate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update an existing integration (e.g., disconnect or update credentials)."""
    db_integration = db.query(Integration).filter(
        Integration.user_id == current_user.id,
        Integration.app_name == app_name
    ).first()

    if not db_integration:
        raise HTTPException(status_code=404, detail="Integration not found")

    if integration_update.api_key is not None:
        db_integration.api_key = integration_update.api_key
    if integration_update.sync_frequency is not None:
        db_integration.sync_frequency = integration_update.sync_frequency
    if integration_update.connected is not None:
        db_integration.connected = integration_update.connected

    if db_integration.connected:
        db_integration.last_sync = datetime.utcnow()

    db.commit()
    db.refresh(db_integration)

    log_audit(db, current_user.id, "update", "integration", db_integration.id,
              f"Updated integration {app_name}",
              user_agent=request.headers.get("user-agent"))

    return db_integration


@app.delete("/api/integrations/{app_name}", response_model=IntegrationSchema)
def delete_integration(
    app_name: str,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete an integration configuration."""
    integration = db.query(Integration).filter(
        Integration.user_id == current_user.id,
        Integration.app_name == app_name
    ).first()

    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")

    db.delete(integration)
    db.commit()

    log_audit(db, current_user.id, "delete", "integration", app_name,
              f"Deleted integration {app_name}",
              user_agent=request.headers.get("user-agent"))

    return integration


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

    # Use a provider-based integration system.
    provider = get_provider(integration, current_user)

    try:
        fetched_transactions = provider.fetch_transactions()
    except Exception as e:
        # Mark integration as disconnected on failure so UI reflects connection issues
        integration.connected = False
        db.commit()
        raise HTTPException(status_code=502, detail=str(e))

    synced_transactions = []
    for trans_data in fetched_transactions:
        # Normalize incoming transaction fields
        tx_type = trans_data.get("type") or trans_data.get("transaction_type") or "expense"
        tx_date = trans_data.get("date") or trans_data.get("timestamp")

        # Ensure date is parsable (fallback to now)
        try:
            parsed_date = datetime.fromisoformat(tx_date) if tx_date else datetime.utcnow()
        except Exception:
            parsed_date = datetime.utcnow()

        db_transaction = Transaction(
            user_id=current_user.id,
            synced=True,
            source=app_name,
            date=parsed_date,
            type=tx_type,
            description=trans_data.get("description") or "Imported transaction",
            amount=float(trans_data.get("amount") or 0),
            category=trans_data.get("category") or "Imported",
            notes=trans_data.get("notes") or None
        )
        db.add(db_transaction)
        synced_transactions.append(db_transaction)

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
