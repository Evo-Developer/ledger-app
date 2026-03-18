"""
Security Configuration
Implements secure headers, CSP, and security best practices
"""

from fastapi import Request
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
import secrets


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all responses
    Implements OWASP recommendations
    """
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Generate nonce for CSP
        nonce = secrets.token_hex(16)
        request.state.csp_nonce = nonce
        
        # Security Headers
        security_headers = {
            # Prevent clickjacking
            "X-Frame-Options": "DENY",
            
            # Prevent MIME type sniffing
            "X-Content-Type-Options": "nosniff",
            
            # Enable XSS protection
            "X-XSS-Protection": "1; mode=block",
            
            # Referrer policy
            "Referrer-Policy": "strict-origin-when-cross-origin",
            
            # Permissions policy
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
            
            # HSTS (HTTP Strict Transport Security)
            # Enable only if using HTTPS
            # "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
            
            # Content Security Policy
            "Content-Security-Policy": (
                f"default-src 'self'; "
                f"script-src 'self' 'nonce-{nonce}' https://cdn.jsdelivr.net; "
                f"style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                f"font-src 'self' https://fonts.gstatic.com; "
                f"img-src 'self' data: https:; "
                f"connect-src 'self'; "
                f"frame-ancestors 'none'; "
                f"base-uri 'self'; "
                f"form-action 'self';"
            ),
            
            # Remove server header
            "Server": "Ledger"
        }
        
        # Apply headers
        for header, value in security_headers.items():
            response.headers[header] = value
        
        return response


# SQL Injection Prevention Patterns
SQL_INJECTION_PATTERNS = [
    "' OR '1'='1",
    "' OR 1=1--",
    "'; DROP TABLE",
    "UNION SELECT",
    "'; EXEC",
    "<script>",
    "javascript:",
    "onerror=",
]


def detect_sql_injection(text: str) -> bool:
    """
    Detect potential SQL injection attempts
    
    Args:
        text: Input text to check
        
    Returns:
        True if potential SQL injection detected
    """
    if not text:
        return False
    
    text_upper = text.upper()
    
    for pattern in SQL_INJECTION_PATTERNS:
        if pattern.upper() in text_upper:
            return True
    
    return False


# XSS Prevention Patterns
XSS_PATTERNS = [
    "<script",
    "javascript:",
    "onerror=",
    "onload=",
    "onclick=",
    "onfocus=",
    "onmouseover=",
]


def detect_xss(text: str) -> bool:
    """
    Detect potential XSS attempts
    
    Args:
        text: Input text to check
        
    Returns:
        True if potential XSS detected
    """
    if not text:
        return False
    
    text_lower = text.lower()
    
    for pattern in XSS_PATTERNS:
        if pattern in text_lower:
            return True
    
    return False


# Allowed file extensions for uploads
ALLOWED_EXTENSIONS = {
    'pdf', 'png', 'jpg', 'jpeg', 'gif', 'csv', 'xlsx'
}


def allowed_file(filename: str) -> bool:
    """
    Check if file extension is allowed
    
    Args:
        filename: Name of file
        
    Returns:
        True if allowed, False otherwise
    """
    if '.' not in filename:
        return False
    
    extension = filename.rsplit('.', 1)[1].lower()
    return extension in ALLOWED_EXTENSIONS


# Maximum request sizes
MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_JSON_SIZE = 1 * 1024 * 1024  # 1 MB


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """
    Limit request body size to prevent DoS attacks
    """
    
    async def dispatch(self, request: Request, call_next):
        # Check content length
        content_length = request.headers.get('content-length')
        
        if content_length:
            content_length = int(content_length)
            
            # Check if exceeds limit
            if content_length > MAX_REQUEST_SIZE:
                return Response(
                    content="Request too large",
                    status_code=413
                )
        
        return await call_next(request)


# CORS configuration for production
ALLOWED_ORIGINS = [
    "http://localhost",
    "http://localhost:80",
    "http://localhost:8080",
    # Add your production domains here
]


def get_cors_origins():
    """Get CORS allowed origins"""
    import os
    
    # Allow environment variable override
    env_origins = os.getenv("ALLOWED_ORIGINS")
    if env_origins:
        return env_origins.split(",")
    
    return ALLOWED_ORIGINS


# Export
__all__ = [
    'SecurityHeadersMiddleware',
    'RequestSizeLimitMiddleware',
    'detect_sql_injection',
    'detect_xss',
    'allowed_file',
    'get_cors_origins',
]
