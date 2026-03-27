"""
Simplified Authentication Module
Uses bcrypt only (no Argon2) to avoid build issues
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import json
import os
import re
import time
import threading
import logging

from database import get_db
from models import User, UserRole
from schemas import TokenData

logger = logging.getLogger(__name__)

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "change-this-in-production-please-use-openssl-rand-hex-32-to-generate")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
SUPERADMIN_USERNAME = os.getenv("SUPERADMIN_USERNAME", "admin")
SUPERADMIN_PASSWORD = os.getenv("SUPERADMIN_PASSWORD", "change-me-superadmin-password")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()


def _is_insecure_secret(secret: str) -> bool:
    if not secret:
        return True
    insecure_markers = [
        "change-this",
        "please-use-openssl",
        "secret",
    ]
    lowered = secret.lower()
    return any(marker in lowered for marker in insecure_markers) or len(secret) < 32


def _is_insecure_superadmin_password(password: str) -> bool:
    if not password:
        return True
    lowered = password.lower()
    weak_values = {
        "admin",
        "admin123",
        "password",
        "password123",
        "change-me-superadmin-password",
    }
    return lowered in weak_values or len(password) < 12


if ENVIRONMENT == "production":
    if _is_insecure_secret(SECRET_KEY):
        raise RuntimeError("Insecure SECRET_KEY for production. Set a strong random value.")
    if _is_insecure_superadmin_password(SUPERADMIN_PASSWORD):
        raise RuntimeError("Insecure SUPERADMIN_PASSWORD for production. Set a strong random value.")
else:
    if _is_insecure_secret(SECRET_KEY):
        logger.warning("Using insecure SECRET_KEY in non-production environment.")
    if _is_insecure_superadmin_password(SUPERADMIN_PASSWORD):
        logger.warning("Using weak SUPERADMIN_PASSWORD in non-production environment.")


def validate_password_policy(password: str) -> Optional[str]:
    """Validate password against configurable policy; returns error message or None."""
    min_len = int(os.getenv("MIN_PASSWORD_LENGTH", "8"))
    max_len = int(os.getenv("MAX_PASSWORD_LENGTH", "128"))
    require_complexity = os.getenv("REQUIRE_PASSWORD_COMPLEXITY", "true").lower() in {"1", "true", "yes", "on"}

    if password is None:
        return "Password is required"
    if len(password) < min_len:
        return f"Password must be at least {min_len} characters"
    if len(password) > max_len:
        return f"Password must be at most {max_len} characters"

    if require_complexity:
        if not re.search(r"[A-Z]", password):
            return "Password must include at least one uppercase letter"
        if not re.search(r"[a-z]", password):
            return "Password must include at least one lowercase letter"
        if not re.search(r"[0-9]", password):
            return "Password must include at least one number"
        if not re.search(r"[^A-Za-z0-9]", password):
            return "Password must include at least one special character"

    return None


_registration_attempts = {}
_registration_attempts_lock = threading.RLock()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")


ALL_TABS = [
    "expenses", "income", "budgets", "goals", "savings", "investments",
    "retirement", "insurance", "liabilities", "assets", "documents",
    "integrations", "insights", "users", "settings", "audit"
]

ALL_PAGES = [
    "dashboard", "financial_insights", "documents", "integrations", "users", "settings",
    "admin_app_insights", "formula_config", "danger_zone", "admin_docs", "audit_trail", "access_control"
]

ALL_FIELDS = [
    "financial_values", "budgets", "goals", "investments", "assets", "liabilities",
    "documents", "integrations", "insurance", "retirement", "audit_export", "user_role_controls", "federated_identity"
]

ALL_PERMISSIONS = [
    "write", "manage_users", "manage_roles", "manage_permissions", "manage_settings",
    "view_app_insights", "manage_formulas", "reset_data", "view_audit", "export_audit",
    "view_admin_docs", "external_rbac_sync"
]


def get_default_permissions(role: str) -> dict:
    normalized_role = (role or UserRole.USER.value).lower()
    if normalized_role == UserRole.SUPERADMIN.value:
        return {
            "tabs": ALL_TABS,
            "pages": ALL_PAGES,
            "fields": ALL_FIELDS,
            "permissions": ALL_PERMISSIONS,
        }

    if normalized_role == UserRole.ADMIN.value:
        return {
            "tabs": [
                "expenses", "income", "budgets", "goals", "savings", "investments",
                "retirement", "insurance", "liabilities", "assets", "documents",
                "integrations", "insights", "users", "settings"
            ],
            "pages": [
                "dashboard", "financial_insights", "documents", "integrations", "users", "settings",
                "admin_app_insights", "formula_config", "danger_zone", "admin_docs"
            ],
            "fields": [
                "financial_values", "budgets", "goals", "investments", "assets", "liabilities",
                "documents", "integrations", "insurance", "retirement", "user_role_controls"
            ],
            "permissions": [
                "write", "manage_users", "manage_settings", "view_app_insights",
                "manage_formulas", "reset_data", "view_admin_docs"
            ],
        }

    if normalized_role == UserRole.READONLY.value:
        return {
            "tabs": ["expenses", "income", "budgets", "goals", "savings", "investments", "retirement", "insurance", "liabilities", "assets", "documents", "integrations", "insights"],
            "pages": ["dashboard", "financial_insights", "documents", "integrations"],
            "fields": ["financial_values", "budgets", "goals", "investments", "assets", "liabilities", "documents", "insurance", "retirement"],
            "permissions": [],
        }

    return {
        "tabs": ["expenses", "income", "budgets", "goals", "savings", "investments", "retirement", "insurance", "liabilities", "assets", "documents", "integrations", "insights"],
        "pages": ["dashboard", "financial_insights", "documents", "integrations"],
        "fields": ["financial_values", "budgets", "goals", "investments", "assets", "liabilities", "documents", "insurance", "retirement"],
        "permissions": ["write"],
    }


def normalize_permissions(role: str, permissions_json: Optional[str]) -> dict:
    permissions = get_default_permissions(role)
    if not permissions_json:
        return permissions

    try:
        parsed = json.loads(permissions_json)
    except Exception:
        return permissions

    for key in ("tabs", "pages", "fields", "permissions"):
        if isinstance(parsed.get(key), list):
            permissions[key] = sorted({str(item) for item in parsed[key] if item is not None})

    return permissions


def user_has_permission(user: User, permission: str) -> bool:
    if not user:
        return False
    if user.role == UserRole.SUPERADMIN.value:
        return True
    return permission in normalize_permissions(user.role, getattr(user, "permissions_json", None)).get("permissions", [])


def get_client_ip(request: Request) -> str:
    """
    Get client IP address from request
    """
    if request and hasattr(request, 'client') and request.client:
        return request.client.host
    return "unknown"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify password against hash using bcrypt
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """
    Hash password using bcrypt
    """
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
    })
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def authenticate_user(db: Session, username: str, password: str, ip_address: str = "unknown"):
    """
    Authenticate user
    """
    user = db.query(User).filter((User.username == username) | (User.email == username)).first()
    if not user:
        return False
    if not user.is_active:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """
    Get current authenticated user from JWT token
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.username == token_data.username).first()
    if user is None:
        raise credentials_exception
    
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Get current active user
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account"
        )
    return current_user


async def require_admin(current_user: User = Depends(get_current_active_user)) -> User:
    """Require admin role."""
    if current_user.role not in {UserRole.ADMIN.value, UserRole.SUPERADMIN.value}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required"
        )
    return current_user


async def require_superadmin(current_user: User = Depends(get_current_active_user)) -> User:
    if current_user.role != UserRole.SUPERADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin role required"
        )
    return current_user


async def require_write_access(current_user: User = Depends(get_current_active_user)) -> User:
    """Require a non-readonly role for write operations."""
    if current_user.role == UserRole.READONLY.value or not user_has_permission(current_user, "write"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your role is readonly. You can view data but cannot make changes."
        )
    return current_user


def check_registration_rate_limit(ip_address: str) -> bool:
    """In-memory registration rate limit: max registrations per hour per source IP."""
    if not ip_address:
        return True

    max_registrations_per_hour = int(os.getenv("MAX_REGISTRATIONS_PER_HOUR", "3"))
    now = time.time()
    one_hour_ago = now - 3600

    with _registration_attempts_lock:
        attempts = _registration_attempts.get(ip_address, [])
        attempts = [ts for ts in attempts if ts >= one_hour_ago]

        if len(attempts) >= max_registrations_per_hour:
            return False

        attempts.append(now)
        _registration_attempts[ip_address] = attempts
        return True


# Export functions
__all__ = [
    'get_password_hash',
    'verify_password',
    'create_access_token',
    'authenticate_user',
    'get_current_user',
    'get_current_active_user',
    'require_admin',
    'require_superadmin',
    'require_write_access',
    'get_client_ip',
    'check_registration_rate_limit',
    'ACCESS_TOKEN_EXPIRE_MINUTES',
    'SUPERADMIN_USERNAME',
    'SUPERADMIN_PASSWORD',
    'validate_password_policy',
    'get_default_permissions',
    'normalize_permissions',
    'user_has_permission'
]
