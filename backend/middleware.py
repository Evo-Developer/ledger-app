"""
Enterprise middleware for handling concurrent requests, rate limiting, and fault tolerance.
"""

from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import time
import logging
import uuid
import asyncio
from typing import Callable

from concurrency import (
    active_requests, request_budget, deadlock_detector, session_manager,
    retry_policy, ThreadSafeCounter
)

logger = logging.getLogger(__name__)


class RequestTrackingMiddleware(BaseHTTPMiddleware):
    """Track request metrics and manage concurrent connections."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Increment active requests. ThreadSafeCounter.increment() returns only
        # the current value; peak is available via get().
        current = active_requests.increment()
        _, peak = active_requests.get()
        request.state.active_requests = current
        
        start_time = time.time()
        
        try:
            logger.info(f"[{request_id}] {request.method} {request.url.path} | Active: {current}")
            
            response = await call_next(request)
            
            # Add request tracking headers to response
            duration_ms = (time.time() - start_time) * 1000
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
            
            logger.info(f"[{request_id}] {response.status_code} | {duration_ms:.2f}ms")
            
            return response
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"[{request_id}] Exception after {duration_ms:.2f}ms: {str(e)[:200]}")
            
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "detail": "Internal server error",
                    "request_id": request_id,
                    "error_type": type(e).__name__
                }
            )
        finally:
            # Decrement active requests
            active_requests.decrement()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Enforce rate limiting per user."""
    
    # Paths that should bypass rate limiting
    BYPASS_PATHS = {'/health', '/health/detailed', '/metrics', '/docs', '/openapi.json', '/favicon.ico'}
    
    # Different rate limits for different endpoints
    RATE_LIMITS = {
        '/auth/': 2,
        '/users/': 3,
        '/transactions/': 2,
        '/': 1
    }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        normalized_path = self._normalize_path(request.url.path)

        # Skip rate limiting for certain paths
        if normalized_path in self.BYPASS_PATHS or normalized_path.startswith('/uploads'):
            return await call_next(request)
        
        # Get user identifier (from token or IP)
        user_id = self._extract_user_id(request)
        if not user_id:
            user_id = self._get_client_ip(request)
        
        # Determine tokens required based on endpoint
        tokens_required = self._get_tokens_required(normalized_path)
        
        # Check rate limit
        allowed, remaining, retry_after = request_budget.check_budget(user_id, tokens_required)
        
        if not allowed:
            logger.warning(f"Rate limit exceeded for {user_id} on {request.url.path}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded",
                    "retry_after": retry_after
                },
                headers={"Retry-After": str(int(retry_after) + 1)}
            )
        
        request.state.user_id = user_id
        request.state.remaining_requests = remaining
        
        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        
        return response

    def _normalize_path(self, path: str) -> str:
        """Normalize API paths so middleware rules work for both /api/* and non-/api routes."""
        if path == '/api':
            return '/'
        if path.startswith('/api/'):
            return path[4:]
        return path
    
    def _extract_user_id(self, request: Request) -> str:
        """Extract user ID from JWT token or session."""
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            return auth_header[7:40]  # Use token prefix as identifier
        return None
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address."""
        if 'x-forwarded-for' in request.headers:
            return request.headers['x-forwarded-for'].split(',')[0].strip()
        if 'x-real-ip' in request.headers:
            return request.headers['x-real-ip']
        return request.client.host if request.client else 'unknown'
    
    def _get_tokens_required(self, path: str) -> int:
        """Get token cost for endpoint based on path."""
        for endpoint_pattern, tokens in self.RATE_LIMITS.items():
            if path.startswith(endpoint_pattern):
                return tokens
        return self.RATE_LIMITS['/']


class TimeoutMiddleware(BaseHTTPMiddleware):
    """Enforce request timeouts to prevent hanging connections."""
    
    # Timeout in seconds per endpoint type
    TIMEOUTS = {
        'file-upload': 60,
        'file-export': 30,
        'bulk-operation': 45,
        'default': 30
    }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        timeout = self._get_timeout(request.url.path)
        request.state.timeout = timeout
        
        try:
            # Execute with timeout
            response = await asyncio.wait_for(
                call_next(request),
                timeout=timeout
            )
            return response
        except asyncio.TimeoutError:
            logger.error(f"Request timeout for {request.method} {request.url.path}")
            return JSONResponse(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                content={
                    "detail": "Request timeout",
                    "timeout_seconds": timeout
                }
            )
    
    def _get_timeout(self, path: str) -> int:
        """Determine timeout based on endpoint."""
        if 'upload' in path or 'import' in path:
            return self.TIMEOUTS['file-upload']
        elif 'export' in path:
            return self.TIMEOUTS['file-export']
        elif 'bulk' in path or 'batch' in path:
            return self.TIMEOUTS['bulk-operation']
        return self.TIMEOUTS['default']


class CircuitBreakerMiddleware(BaseHTTPMiddleware):
    """Circuit breaker middleware for graceful degradation."""
    
    def __init__(self, app, failure_threshold: int = 5, recovery_timeout: int = 60):
        super().__init__(app)
        self.failure_threshold = failure_threshold
        self.consecutive_failures = 0
        self.is_open = False
        self.last_failure_time = None
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check if circuit should be closed
        if self.is_open:
            if self._should_attempt_recovery():
                self.is_open = False
                self.consecutive_failures = 0
                logger.info("Circuit breaker attempting recovery")
            else:
                return JSONResponse(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    content={"detail": "Service temporarily unavailable"}
                )
        
        try:
            response = await call_next(request)
            
            # Reset failures on success
            if response.status_code < 500:
                self.consecutive_failures = 0
            else:
                self._handle_failure()
            
            return response
        except Exception as e:
            self._handle_failure()
            logger.error(f"Circuit breaker handling exception: {str(e)[:100]}")
            
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"detail": "Service error, please retry"}
            )
    
    def _handle_failure(self):
        """Handle a failure and potentially open circuit."""
        self.consecutive_failures += 1
        self.last_failure_time = time.time()
        
        if self.consecutive_failures >= self.failure_threshold:
            self.is_open = True
            logger.warning(f"Circuit breaker opened after {self.consecutive_failures} failures")
    
    def _should_attempt_recovery(self) -> bool:
        """Check if enough time has passed to attempt recovery."""
        if self.last_failure_time is None:
            return True
        return time.time() - self.last_failure_time >= 60  # 60 second recovery timeout


class UserIsolationMiddleware(BaseHTTPMiddleware):
    """Ensure user isolation and prevent data leakage."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Extract and validate user context
        user_context = self._extract_user_context(request)
        request.state.user_context = user_context
        
        response = await call_next(request)
        
        # Ensure sensitive headers aren't exposed
        if 'X-Database-Query' in response.headers:
            del response.headers['X-Database-Query']
        if 'X-Internal-Error' in response.headers:
            del response.headers['X-Internal-Error']
        
        return response
    
    def _extract_user_context(self, request: Request) -> dict:
        """Extract and validate user context from request."""
        return {
            'timestamp': time.time(),
            'ip': self._get_client_ip(request),
            'path': request.url.path,
            'method': request.method
        }
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address."""
        if 'x-forwarded-for' in request.headers:
            return request.headers['x-forwarded-for'].split(',')[0].strip()
        if 'x-real-ip' in request.headers:
            return request.headers['x-real-ip']
        return request.client.host if request.client else 'unknown'


# For imports in main.py
__all__ = [
    'RequestTrackingMiddleware',
    'RateLimitMiddleware',
    'TimeoutMiddleware',
    'CircuitBreakerMiddleware',
    'UserIsolationMiddleware'
]
