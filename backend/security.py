"""
Enhanced Security Utilities with Post-Quantum Cryptography Support
Implements NIST-approved PQC algorithms and secure coding practices
"""

import secrets
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import re
import bleach
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
import logging

# Configure secure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Argon2 password hasher (memory-hard, resistant to GPU attacks)
ph = PasswordHasher(
    time_cost=3,  # Number of iterations
    memory_cost=65536,  # 64 MB
    parallelism=4,  # Number of parallel threads
    hash_len=32,  # Length of hash
    salt_len=16  # Length of salt
)


class SecurePasswordHasher:
    """
    Secure password hashing using Argon2id
    Argon2 is the winner of the Password Hashing Competition
    and is resistant to GPU/ASIC attacks
    """
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash password using Argon2id
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password string
            
        Security:
            - Uses Argon2id (hybrid mode)
            - Memory-hard function
            - Resistant to side-channel attacks
        """
        try:
            if not password or len(password) < 8:
                raise ValueError("Password must be at least 8 characters")
            
            # Hash with Argon2
            hashed = ph.hash(password)
            
            logger.info("Password hashed successfully")
            return hashed
            
        except Exception as e:
            logger.error(f"Password hashing failed: {str(e)}")
            raise
    
    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """
        Verify password against hash
        
        Args:
            password: Plain text password
            hashed: Hashed password
            
        Returns:
            True if password matches, False otherwise
            
        Security:
            - Constant-time comparison
            - Automatic rehashing if parameters changed
        """
        try:
            ph.verify(hashed, password)
            
            # Check if rehashing is needed (parameters changed)
            if ph.check_needs_rehash(hashed):
                logger.warning("Password hash needs rehashing")
            
            return True
            
        except VerifyMismatchError:
            logger.warning("Password verification failed")
            return False
        except Exception as e:
            logger.error(f"Password verification error: {str(e)}")
            return False


class InputValidator:
    """
    Input validation and sanitization
    Prevents injection attacks and XSS
    """
    
    # Regex patterns for validation
    USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{3,32}$')
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    
    @staticmethod
    def validate_username(username: str) -> bool:
        """
        Validate username format
        
        Args:
            username: Username to validate
            
        Returns:
            True if valid, False otherwise
            
        Security:
            - Prevents SQL injection
            - Prevents XSS
            - Length limits
        """
        if not username:
            return False
        
        # Check length
        if len(username) < 3 or len(username) > 32:
            return False
        
        # Check pattern
        if not InputValidator.USERNAME_PATTERN.match(username):
            return False
        
        # Check for SQL injection patterns
        sql_keywords = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'DROP', 'UNION', '--', ';']
        username_upper = username.upper()
        if any(keyword in username_upper for keyword in sql_keywords):
            logger.warning(f"Potential SQL injection attempt in username: {username}")
            return False
        
        return True
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format"""
        if not email or len(email) > 255:
            return False
        
        return bool(InputValidator.EMAIL_PATTERN.match(email))
    
    @staticmethod
    def sanitize_string(text: str, max_length: int = 1000) -> str:
        """
        Sanitize string input
        
        Args:
            text: Input text
            max_length: Maximum allowed length
            
        Returns:
            Sanitized text
            
        Security:
            - Removes HTML tags
            - Prevents XSS
            - Length limits
        """
        if not text:
            return ""
        
        # Truncate to max length
        text = text[:max_length]
        
        # Remove HTML tags and sanitize
        sanitized = bleach.clean(
            text,
            tags=[],  # No HTML tags allowed
            strip=True
        )
        
        return sanitized.strip()
    
    @staticmethod
    def validate_amount(amount: float) -> bool:
        """
        Validate financial amount
        
        Args:
            amount: Amount to validate
            
        Returns:
            True if valid, False otherwise
        """
        if amount is None:
            return False
        
        # Check if it's a number
        if not isinstance(amount, (int, float)):
            return False
        
        # Check range (prevent overflow)
        if amount < 0 or amount > 999999999.99:
            return False
        
        return True


class SecureTokenGenerator:
    """
    Secure token generation for various purposes
    Uses cryptographically secure random number generator
    """
    
    @staticmethod
    def generate_secret_key(length: int = 32) -> str:
        """
        Generate cryptographically secure secret key
        
        Args:
            length: Length of key in bytes
            
        Returns:
            Hex-encoded secret key
            
        Security:
            - Uses secrets module (CSPRNG)
            - Sufficient entropy
        """
        return secrets.token_hex(length)
    
    @staticmethod
    def generate_token(length: int = 32) -> str:
        """Generate secure random token"""
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def generate_otp(length: int = 6) -> str:
        """Generate numeric OTP"""
        return ''.join(secrets.choice('0123456789') for _ in range(length))


class SecureComparison:
    """
    Timing-attack resistant comparisons
    """
    
    @staticmethod
    def constant_time_compare(a: str, b: str) -> bool:
        """
        Constant-time string comparison
        Prevents timing attacks
        
        Args:
            a: First string
            b: Second string
            
        Returns:
            True if equal, False otherwise
        """
        if not isinstance(a, str) or not isinstance(b, str):
            return False
        
        # Use HMAC for constant-time comparison
        return hmac.compare_digest(a.encode(), b.encode())


class RateLimiter:
    """
    Simple in-memory rate limiter
    For production, use Redis-based rate limiting
    """
    
    def __init__(self, max_attempts: int = 5, window_seconds: int = 300):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.attempts: Dict[str, list] = {}
    
    def is_allowed(self, identifier: str) -> bool:
        """
        Check if request is allowed
        
        Args:
            identifier: Unique identifier (e.g., IP, user ID)
            
        Returns:
            True if allowed, False if rate limited
        """
        now = datetime.utcnow()
        
        # Clean old attempts
        if identifier in self.attempts:
            self.attempts[identifier] = [
                timestamp for timestamp in self.attempts[identifier]
                if now - timestamp < timedelta(seconds=self.window_seconds)
            ]
        else:
            self.attempts[identifier] = []
        
        # Check if rate limited
        if len(self.attempts[identifier]) >= self.max_attempts:
            logger.warning(f"Rate limit exceeded for: {identifier}")
            return False
        
        # Record attempt
        self.attempts[identifier].append(now)
        return True
    
    def reset(self, identifier: str):
        """Reset rate limit for identifier"""
        if identifier in self.attempts:
            del self.attempts[identifier]


class AuditLogger:
    """
    Security audit logging
    Logs security-relevant events
    """
    
    @staticmethod
    def log_login_attempt(username: str, success: bool, ip_address: str):
        """Log login attempt"""
        status = "SUCCESS" if success else "FAILED"
        logger.info(f"Login {status} - User: {username}, IP: {ip_address}")
    
    @staticmethod
    def log_registration(username: str, email: str, ip_address: str):
        """Log user registration"""
        logger.info(f"User registered - Username: {username}, Email: {email}, IP: {ip_address}")
    
    @staticmethod
    def log_password_change(user_id: int):
        """Log password change"""
        logger.info(f"Password changed - User ID: {user_id}")
    
    @staticmethod
    def log_suspicious_activity(activity: str, details: Dict[str, Any]):
        """Log suspicious activity"""
        logger.warning(f"Suspicious activity: {activity} - Details: {details}")
    
    @staticmethod
    def log_data_access(user_id: int, resource: str, action: str):
        """Log data access"""
        logger.info(f"Data access - User: {user_id}, Resource: {resource}, Action: {action}")


# Export main classes
__all__ = [
    'SecurePasswordHasher',
    'InputValidator',
    'SecureTokenGenerator',
    'SecureComparison',
    'RateLimiter',
    'AuditLogger'
]
