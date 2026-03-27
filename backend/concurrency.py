"""
Enterprise-grade concurrency and connection management.
Handles multi-threading, connection pooling, and concurrent access control.
"""

import threading
import time
import logging
from typing import Dict, List, Optional, Callable, Any
from collections import defaultdict
from datetime import datetime, timedelta
from functools import wraps
import uuid

logger = logging.getLogger(__name__)


class ConnectionPool:
    """Advanced connection pooling with health checks and failover."""
    
    def __init__(self, max_pool_size: int = 20, max_overflow: int = 10, 
                 pool_recycle: int = 3600, pool_pre_ping: bool = True):
        """
        Initialize connection pool.
        
        Args:
            max_pool_size: Minimum number of connections to keep
            max_overflow: Maximum overflow connections
            pool_recycle: Recycle connections after N seconds
            pool_pre_ping: Test connection before using
        """
        self.max_pool_size = max_pool_size
        self.max_overflow = max_overflow
        self.pool_recycle = pool_recycle
        self.pool_pre_ping = pool_pre_ping
        self.connections: Dict[str, List[Any]] = defaultdict(list)
        self.lock = threading.RLock()
        self.connection_timestamps: Dict[str, List[float]] = defaultdict(list)
        logger.info(f"ConnectionPool initialized: max_pool_size={max_pool_size}, max_overflow={max_overflow}")
    
    def get_connection_config(self) -> Dict[str, Any]:
        """Get SQLAlchemy engine configuration for connection pooling."""
        return {
            'pool_size': self.max_pool_size,
            'max_overflow': self.max_overflow,
            'pool_pre_ping': self.pool_pre_ping,
            'pool_recycle': self.pool_recycle,
            'echo': False,
        }


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for fault tolerance.
    Prevents cascading failures by stopping requests to failing services.
    """
    
    CLOSED = 'CLOSED'
    OPEN = 'OPEN'
    HALF_OPEN = 'HALF_OPEN'
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds before attempting recovery
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = self.CLOSED
        self.failures = 0
        self.last_failure_time: Optional[float] = None
        self.lock = threading.RLock()
        logger.info(f"CircuitBreaker initialized: threshold={failure_threshold}, timeout={recovery_timeout}s")
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function through circuit breaker.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Exception: If circuit is OPEN or function fails
        """
        with self.lock:
            if self.state == self.OPEN:
                if self._should_attempt_reset():
                    self.state = self.HALF_OPEN
                    logger.info("CircuitBreaker entering HALF_OPEN state for recovery")
                else:
                    raise Exception(f"CircuitBreaker is OPEN (failures: {self.failures})")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt recovery."""
        if self.last_failure_time is None:
            return True
        return time.time() - self.last_failure_time >= self.recovery_timeout
    
    def _on_success(self):
        """Handle successful call."""
        with self.lock:
            self.failures = 0
            self.state = self.CLOSED
            logger.debug("CircuitBreaker call successful, resetting to CLOSED")
    
    def _on_failure(self):
        """Handle failed call."""
        with self.lock:
            self.failures += 1
            self.last_failure_time = time.time()
            
            if self.failures >= self.failure_threshold:
                self.state = self.OPEN
                logger.warning(f"CircuitBreaker opened after {self.failures} failures")
            elif self.state == self.HALF_OPEN:
                self.state = self.OPEN
                logger.warning("CircuitBreaker reopened during recovery attempt")


class RetryPolicy:
    """Intelligent retry logic with exponential backoff and jitter."""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, 
                 max_delay: float = 60.0, jitter: bool = True):
        """
        Initialize retry policy.
        
        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Initial delay between retries (seconds)
            max_delay: Maximum delay between retries (seconds)
            jitter: Add random jitter to delays
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter = jitter
    
    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with retry logic.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Exception: If all retry attempts fail
        """
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                if attempt < self.max_retries:
                    delay = self._calculate_delay(attempt)
                    logger.warning(f"Retry attempt {attempt + 1}/{self.max_retries} after {delay:.2f}s: {str(e)[:100]}")
                    time.sleep(delay)
                else:
                    logger.error(f"All {self.max_retries + 1} retry attempts exhausted: {str(e)[:200]}")
        
        raise last_exception
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay with exponential backoff and optional jitter."""
        delay = min(self.base_delay * (2 ** attempt), self.max_delay)
        
        if self.jitter:
            import random
            delay *= (0.5 + random.random())  # Add 0-100% jitter
        
        return delay


class ThreadSafeCounter:
    """Thread-safe counter for tracking concurrent operations."""
    
    def __init__(self):
        self.value = 0
        self.lock = threading.RLock()
        self.max_value = 0
    
    def increment(self) -> int:
        """Increment counter and return new value."""
        with self.lock:
            self.value += 1
            self.max_value = max(self.max_value, self.value)
            return self.value
    
    def decrement(self) -> int:
        """Decrement counter and return new value."""
        with self.lock:
            self.value = max(0, self.value - 1)
            return self.value
    
    def get(self) -> tuple:
        """Get current value and max value reached."""
        with self.lock:
            return self.value, self.max_value
    
    def reset(self):
        """Reset counter."""
        with self.lock:
            self.value = 0
            self.max_value = 0


class RequestBudget:
    """Token bucket for rate limiting with per-user tracking."""
    
    def __init__(self, capacity: int = 100, refill_rate: float = 10.0):
        """
        Initialize request budget using token bucket algorithm.
        
        Args:
            capacity: Maximum tokens in bucket
            refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.buckets: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.RLock()
    
    def check_budget(self, user_id: str, tokens_required: int = 1) -> tuple:
        """
        Check if user has sufficient budget.
        
        Args:
            user_id: User identifier
            tokens_required: Tokens to consume
            
        Returns:
            Tuple of (allowed: bool, remaining_tokens: int, retry_after: float)
        """
        with self.lock:
            if user_id not in self.buckets:
                self.buckets[user_id] = {
                    'tokens': self.capacity,
                    'last_refill': time.time()
                }
            
            bucket = self.buckets[user_id]
            now = time.time()
            time_since_refill = now - bucket['last_refill']
            
            # Add tokens based on elapsed time
            new_tokens = time_since_refill * self.refill_rate
            bucket['tokens'] = min(self.capacity, bucket['tokens'] + new_tokens)
            bucket['last_refill'] = now
            
            if bucket['tokens'] >= tokens_required:
                bucket['tokens'] -= tokens_required
                return True, int(bucket['tokens']), 0.0
            else:
                # Calculate when next token will be available
                tokens_needed = tokens_required - bucket['tokens']
                retry_after = tokens_needed / self.refill_rate
                return False, 0, retry_after


class DeadlockDetector:
    """Detect and handle potential deadlocks in database operations."""
    
    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
        self.active_operations: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.RLock()
    
    def register_operation(self, operation_id: str, operation_type: str, user_id: str):
        """Register a database operation for monitoring."""
        with self.lock:
            self.active_operations[operation_id] = {
                'type': operation_type,
                'user_id': user_id,
                'start_time': time.time(),
                'thread_id': threading.get_ident()
            }
            logger.debug(f"Operation registered: {operation_id} ({operation_type})")
    
    def unregister_operation(self, operation_id: str):
        """Unregister a completed operation."""
        with self.lock:
            if operation_id in self.active_operations:
                duration = time.time() - self.active_operations[operation_id]['start_time']
                if duration > self.timeout * 0.8:  # Warn if close to timeout
                    logger.warning(f"Long-running operation: {operation_id} took {duration:.2f}s")
                del self.active_operations[operation_id]
    
    def get_stalled_operations(self) -> List[Dict[str, Any]]:
        """Get list of operations that appear to be stalled."""
        with self.lock:
            now = time.time()
            stalled = [
                {
                    'id': op_id,
                    'type': op_info['type'],
                    'user_id': op_info['user_id'],
                    'duration': now - op_info['start_time'],
                    'thread_id': op_info['thread_id']
                }
                for op_id, op_info in self.active_operations.items()
                if now - op_info['start_time'] > self.timeout
            ]
            return stalled


class UserSessionManager:
    """Manage user sessions with concurrent access control."""
    
    def __init__(self):
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.user_locks: Dict[int, threading.RLock] = defaultdict(threading.RLock)
        self.lock = threading.RLock()
    
    def create_session(self, user_id: int, session_token: str) -> str:
        """Create a new user session."""
        with self.lock:
            session_id = str(uuid.uuid4())
            self.sessions[session_id] = {
                'user_id': user_id,
                'token': session_token,
                'created_at': datetime.utcnow(),
                'last_activity': datetime.utcnow(),
                'active_requests': 0
            }
            logger.info(f"Session created for user {user_id}: {session_id}")
            return session_id
    
    def get_user_lock(self, user_id: int) -> threading.RLock:
        """Get or create lock for user to prevent concurrent modifications."""
        with self.lock:
            return self.user_locks[user_id]
    
    def register_activity(self, session_id: str):
        """Update last activity timestamp."""
        with self.lock:
            if session_id in self.sessions:
                self.sessions[session_id]['last_activity'] = datetime.utcnow()
                self.sessions[session_id]['active_requests'] += 1
    
    def unregister_activity(self, session_id: str):
        """Decrement active requests counter."""
        with self.lock:
            if session_id in self.sessions:
                self.sessions[session_id]['active_requests'] = max(0, 
                    self.sessions[session_id]['active_requests'] - 1)
    
    def get_active_users(self) -> Dict[int, int]:
        """Get count of active users and their request counts."""
        with self.lock:
            active_users = defaultdict(int)
            for session_data in self.sessions.values():
                user_id = session_data['user_id']
                active_users[user_id] += session_data['active_requests']
            return dict(active_users)
    
    def cleanup_expired_sessions(self, max_age_seconds: int = 86400):
        """Remove sessions older than max_age_seconds."""
        with self.lock:
            cutoff_time = datetime.utcnow() - timedelta(seconds=max_age_seconds)
            expired = [sid for sid, sdata in self.sessions.items() 
                      if sdata['last_activity'] < cutoff_time]
            for sid in expired:
                del self.sessions[sid]
            if expired:
                logger.info(f"Cleaned up {len(expired)} expired sessions")


# Global instances
connection_pool = ConnectionPool(max_pool_size=20, max_overflow=10)
circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)
retry_policy = RetryPolicy(max_retries=3, base_delay=1.0, max_delay=60.0)
active_requests = ThreadSafeCounter()
request_budget = RequestBudget(capacity=1000, refill_rate=50.0)  # 50 requests/sec per user
deadlock_detector = DeadlockDetector(timeout=30.0)
session_manager = UserSessionManager()
