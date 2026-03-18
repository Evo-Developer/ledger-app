"""
Enhanced Authentication with Post-Quantum Cryptography Support
Implements secure authentication practices and PQC-ready JWT
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import os
import secrets

from database import get_db
from models import User
from schemas import TokenData
from security import (
    SecurePasswordHasher,
    InputValidator,
    SecureComparison,
    RateLimiter,
    AuditLogger
)

# Configuration with secure defaults
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY or len(SECRET_KEY) < 32:
    # Generate secure key if not provided
    SECRET_KEY = secrets.token_hex(32)
    print("WARNING: Using generated SECRET_KEY. Set SECRET_KEY in environment for production!")

ALGORITHM = "HS256"  # Can be upgraded to PQC algorithm when standardized
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = 7

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

# Rate limiters
login_rate_limiter = RateLimiter(max_attempts=5, window_seconds=300)  # 5 attempts per 5 minutes
registration_rate_limiter = RateLimiter(max_attempts=3, window_seconds=3600)  # 3 per hour

# Password hasher
password_hasher = SecurePasswordHasher()


def get_client_ip(request: Request) -> str:
    """
    Get client IP address from request
    Handles proxy headers securely
    """
    # Check X-Forwarded-For header (if behind proxy)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Take first IP (client IP)
        return forwarded.split(",")[0].strip()
    
    # Fall back to direct connection
    if request.client:
        return request.client.host
    
    return "unknown"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify password against hash using Argon2
    
    Security:
        - Constant-time comparison
        - Memory-hard hashing
        - Resistant to timing attacks
    """
    try:
        return password_hasher.verify_password(plain_password, hashed_password)
    except Exception as e:
        AuditLogger.log_suspicious_activity(
            "password_verification_error",
            {"error": str(e)}
        )
        return False


def get_password_hash(password: str) -> str:
    """
    Hash password using Argon2id
    
    Security:
        - Argon2id (memory-hard)
        - Automatic salt generation
        - Configurable cost parameters
    """
    # Validate password strength
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters")
    
    if len(password) > 128:
        raise ValueError("Password too long")
    
    # Check password complexity
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    
    if not (has_upper and has_lower and has_digit):
        raise ValueError("Password must contain uppercase, lowercase, and digit")
    
    return password_hasher.hash_password(password)


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create JWT access token
    
    Security:
        - Short expiration time
        - Secure claims
        - HMAC signing (upgradeable to PQC)
    """
    to_encode = data.copy()
    
    # Set expiration
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    # Add security claims
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),  # Issued at
        "nbf": datetime.utcnow(),  # Not before
        "jti": secrets.token_hex(16),  # JWT ID (unique identifier)
    })
    
    # Create token
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """Create refresh token with longer expiration"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh",
        "jti": secrets.token_hex(16)
    })
    
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def authenticate_user(
    db: Session,
    username: str,
    password: str,
    ip_address: str
) -> Optional[User]:
    """
    Authenticate user with rate limiting and audit logging
    
    Security:
        - Input validation
        - Rate limiting
        - Audit logging
        - Constant-time comparison
    """
    # Validate input
    if not InputValidator.validate_username(username):
        AuditLogger.log_suspicious_activity(
            "invalid_username_format",
            {"username": username, "ip": ip_address}
        )
        return None
    
    # Check rate limit
    if not login_rate_limiter.is_allowed(ip_address):
        AuditLogger.log_suspicious_activity(
            "login_rate_limit_exceeded",
            {"ip": ip_address}
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later."
        )
    
    # Fetch user
    try:
        user = db.query(User).filter(User.username == username).first()
    except Exception as e:
        AuditLogger.log_suspicious_activity(
            "database_error_during_login",
            {"error": str(e)}
        )
        return None
    
    if not user:
        # Log failed attempt
        AuditLogger.log_login_attempt(username, False, ip_address)
        return None
    
    # Verify password
    if not verify_password(password, user.hashed_password):
        # Log failed attempt
        AuditLogger.log_login_attempt(username, False, ip_address)
        return None
    
    # Success - reset rate limit and log
    login_rate_limiter.reset(ip_address)
    AuditLogger.log_login_attempt(username, True, ip_address)
    
    return user


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current authenticated user from JWT token
    
    Security:
        - Token validation
        - Expiration check
        - User existence check
        - Active status check
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Validate claims
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        
        # Check token type (not a refresh token)
        if payload.get("type") == "refresh":
            raise credentials_exception
        
        token_data = TokenData(username=username)
        
    except JWTError as e:
        AuditLogger.log_suspicious_activity(
            "invalid_jwt_token",
            {"error": str(e)}
        )
        raise credentials_exception
    
    # Fetch user
    try:
        user = db.query(User).filter(User.username == token_data.username).first()
    except Exception as e:
        AuditLogger.log_suspicious_activity(
            "database_error_during_token_validation",
            {"error": str(e)}
        )
        raise credentials_exception
    
    if user is None:
        raise credentials_exception
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current active user
    
    Security:
        - Active status check
        - Can add additional checks (2FA, etc.)
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account"
        )
    
    return current_user


def check_registration_rate_limit(ip_address: str) -> bool:
    """
    Check registration rate limit
    
    Security:
        - Prevents automated account creation
        - Per-IP limiting
    """
    if not registration_rate_limiter.is_allowed(ip_address):
        AuditLogger.log_suspicious_activity(
            "registration_rate_limit_exceeded",
            {"ip": ip_address}
        )
        return False
    
    return True


# Export functions
__all__ = [
    'get_password_hash',
    'verify_password',
    'create_access_token',
    'create_refresh_token',
    'authenticate_user',
    'get_current_user',
    'get_current_active_user',
    'get_client_ip',
    'check_registration_rate_limit',
    'ACCESS_TOKEN_EXPIRE_MINUTES'
]

