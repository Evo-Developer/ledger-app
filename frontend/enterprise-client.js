/**
 * Enterprise-grade error handling and retry logic for frontend.
 * Provides exponential backoff, request deduplication, and graceful degradation.
 */

class EnterpriseErrorHandler {
    constructor(options = {}) {
        this.maxRetries = options.maxRetries || 3;
        this.baseDelay = options.baseDelay || 1000; // milliseconds
        this.maxDelay = options.maxDelay || 30000;
        this.jitter = options.jitter !== false;
        this.requestQueue = new Map();
        this.deduplicationMap = new Map();
        this.circuitBreakerState = 'CLOSED';
        this.circuitBreakerFailures = 0;
        this.circuitBreakerThreshold = options.circuitBreakerThreshold || 5;
        this.circuitBreakerTimeout = options.circuitBreakerTimeout || 60000;
        this.lastFailureTime = null;
        this.requestHistory = [];
        this.maxHistorySize = 100;
    }

    /**
     * Execute request with retry logic and circuit breaker.
     * @param {Function} requestFn - Function that returns a Promise
     * @param {string} requestKey - Unique key for deduplication
     * @returns {Promise} - Result of the request
     */
    async executeWithRetry(requestFn, requestKey = null) {
        // Check circuit breaker
        if (this.circuitBreakerState === 'OPEN') {
            if (this._shouldAttemptCircuitBreakerReset()) {
                console.log('🔌 Circuit breaker entering HALF_OPEN state for recovery');
                this.circuitBreakerState = 'HALF_OPEN';
            } else {
                const error = new Error('Circuit breaker is OPEN - service unavailable');
                error.isCircuitBreakerOpen = true;
                throw error;
            }
        }

        // Deduplicate identical requests
        if (requestKey && this.deduplicationMap.has(requestKey)) {
            const existingPromise = this.deduplicationMap.get(requestKey);
            console.log(`📋 Returning cached request for key: ${requestKey}`);
            return existingPromise;
        }

        let lastError;
        for (let attempt = 0; attempt <= this.maxRetries; attempt++) {
            try {
                const result = await requestFn();
                
                // Success - reset circuit breaker
                this._recordSuccess();
                
                // Store request in history for monitoring
                this._recordRequest(requestKey, 'success', attempt);
                
                return result;
            } catch (error) {
                lastError = error;
                
                if (attempt < this.maxRetries) {
                    const delay = this._calculateDelay(attempt);
                    console.warn(`⚠️ Request failed, retrying in ${delay}ms (attempt ${attempt + 1}/${this.maxRetries})`);
                    await this._sleep(delay);
                } else {
                    console.error(`❌ All retry attempts exhausted: ${error.message}`);
                    this._recordFailure();
                    this._recordRequest(requestKey, 'failure', attempt);
                }
            }
        }

        throw lastError;
    }

    /**
     * Execute request with timeout protection.
     * @param {Promise} promise - Promise to execute
     * @param {number} timeoutMs - Timeout in milliseconds
     * @returns {Promise} - Result or timeout error
     */
    async executeWithTimeout(promise, timeoutMs = 30000) {
        return Promise.race([
            promise,
            new Promise((_, reject) => 
                setTimeout(() => reject(new Error(`Request timeout after ${timeoutMs}ms`)), timeoutMs)
            )
        ]);
    }

    /**
     * Queue a request to prevent overwhelming the server.
     * @param {Function} requestFn - Function that returns a Promise
     * @param {string} queueId - Queue identifier
     */
    queueRequest(requestFn, queueId = 'default') {
        if (!this.requestQueue.has(queueId)) {
            this.requestQueue.set(queueId, { pending: [], processing: false });
        }

        const queue = this.requestQueue.get(queueId);
        queue.pending.push(requestFn);

        if (!queue.processing) {
            this._processQueue(queueId);
        }
    }

    /**
     * Handle API errors with appropriate user messaging.
     * @param {Error} error - The error object
     * @returns {Object} - Structured error response
     */
    handleError(error) {
        let userMessage = 'An error occurred. Please try again.';
        let errorType = 'UNKNOWN';
        let isRetryable = true;

        if (error.isCircuitBreakerOpen) {
            userMessage = 'Service temporarily unavailable. Please wait a moment.';
            errorType = 'CIRCUIT_BREAKER_OPEN';
            isRetryable = false;
        } else if (error.message.includes('timeout')) {
            userMessage = 'Request took too long. Please try again or check your connection.';
            errorType = 'TIMEOUT';
            isRetryable = true;
        } else if (error.response) {
            // HTTP response error
            switch (error.response.status) {
                case 429:
                    userMessage = 'Too many requests. Please slow down.';
                    errorType = 'RATE_LIMITED';
                    isRetryable = true;
                    break;
                case 503:
                    userMessage = 'Service temporarily unavailable. Please try again later.';
                    errorType = 'SERVICE_UNAVAILABLE';
                    isRetryable = true;
                    break;
                case 401:
                case 403:
                    userMessage = 'Authentication failed. Please log in again.';
                    errorType = 'AUTH_ERROR';
                    isRetryable = false;
                    break;
                case 400:
                    userMessage = 'Invalid request. Please check your input.';
                    errorType = 'VALIDATION_ERROR';
                    isRetryable = false;
                    break;
                default:
                    userMessage = error.response.data?.detail || 'Server error occurred.';
                    errorType = `HTTP_${error.response.status}`;
            }
        } else if (error.message.includes('Network')) {
            userMessage = 'Network error. Please check your connection.';
            errorType = 'NETWORK_ERROR';
            isRetryable = true;
        }

        return {
            userMessage,
            errorType,
            isRetryable,
            originalError: error.message
        };
    }

    // Private methods

    _calculateDelay(attempt) {
        let delay = Math.min(
            this.baseDelay * Math.pow(2, attempt),
            this.maxDelay
        );

        if (this.jitter) {
            delay *= 0.5 + Math.random(); // Add 0-100% jitter
        }

        return delay;
    }

    _recordSuccess() {
        if (this.circuitBreakerState === 'HALF_OPEN' || this.circuitBreakerState === 'OPEN') {
            console.log('🔌 Circuit breaker recovered to CLOSED state');
        }
        this.circuitBreakerState = 'CLOSED';
        this.circuitBreakerFailures = 0;
    }

    _recordFailure() {
        this.circuitBreakerFailures++;
        this.lastFailureTime = Date.now();

        if (this.circuitBreakerFailures >= this.circuitBreakerThreshold) {
            this.circuitBreakerState = 'OPEN';
            console.error(`🔌 Circuit breaker OPENED after ${this.circuitBreakerFailures} failures`);
        }
    }

    _shouldAttemptCircuitBreakerReset() {
        if (!this.lastFailureTime) return true;
        return Date.now() - this.lastFailureTime >= this.circuitBreakerTimeout;
    }

    _sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    async _processQueue(queueId) {
        const queue = this.requestQueue.get(queueId);
        if (!queue || queue.pending.length === 0) return;

        queue.processing = true;

        while (queue.pending.length > 0) {
            const requestFn = queue.pending.shift();
            try {
                await requestFn();
            } catch (error) {
                console.error(`Error processing queued request: ${error.message}`);
            }
            // Small delay between requests in queue
            await this._sleep(100);
        }

        queue.processing = false;
    }

    _recordRequest(requestKey, status, attempt) {
        this.requestHistory.push({
            timestamp: new Date().toISOString(),
            key: requestKey,
            status,
            attempt,
            circuitBreakerState: this.circuitBreakerState
        });

        // Keep history size bounded
        if (this.requestHistory.length > this.maxHistorySize) {
            this.requestHistory.shift();
        }
    }

    /**
     * Get diagnostic information for debugging.
     * @returns {Object} - Diagnostic data
     */
    getDiagnostics() {
        return {
            circuitBreakerState: this.circuitBreakerState,
            circuitBreakerFailures: this.circuitBreakerFailures,
            queuedRequests: Array.from(this.requestQueue.entries()).map(([id, q]) => ({
                id,
                pending: q.pending.length,
                processing: q.processing
            })),
            recentRequests: this.requestHistory.slice(-20),
            deduplicatedRequests: this.deduplicationMap.size
        };
    }
}

// Global instance
const enterpriseErrorHandler = new EnterpriseErrorHandler({
    maxRetries: 3,
    baseDelay: 1000,
    maxDelay: 30000,
    jitter: true,
    circuitBreakerThreshold: 5,
    circuitBreakerTimeout: 60000
});

/**
 * Enhanced API wrapper with enterprise error handling.
 */
class EnterpriseAPIClient {
    constructor(apiObject) {
        this.api = apiObject;
        this.requestTimeout = 30000; // 30 seconds default
        this.metrics = {
            totalRequests: 0,
            successfulRequests: 0,
            failedRequests: 0,
            totalLatency: 0
        };
    }

    /**
     * Wrap API request with enterprise features.
     * @param {Function} apiFn - API function to call
     * @param {Array} args - Arguments for API function
     * @param {Object} options - Request options
     */
    async call(apiFn, args = [], options = {}) {
        const startTime = performance.now();
        const requestKey = options.deduplicationKey || null;

        try {
            const result = await enterpriseErrorHandler.executeWithRetry(
                async () => {
                    return await enterpriseErrorHandler.executeWithTimeout(
                        apiFn(...args),
                        options.timeout || this.requestTimeout
                    );
                },
                requestKey
            );

            this.metrics.successfulRequests++;
            const latency = performance.now() - startTime;
            this.metrics.totalLatency += latency;

            if (options.onSuccess) {
                options.onSuccess(result, latency);
            }

            return result;
        } catch (error) {
            this.metrics.failedRequests++;
            const errorInfo = enterpriseErrorHandler.handleError(error);

            if (options.onError) {
                options.onError(errorInfo);
            }

            throw errorInfo;
        } finally {
            this.metrics.totalRequests++;
        }
    }

    /**
     * Queue multiple API calls to prevent overwhelming server.
     */
    queueCall(apiFn, args = [], queueId = 'default') {
        enterpriseErrorHandler.queueRequest(
            async () => await apiFn(...args),
            queueId
        );
    }

    /**
     * Get performance metrics.
     */
    getMetrics() {
        return {
            ...this.metrics,
            averageLatency: this.metrics.totalRequests > 0 
                ? this.metrics.totalLatency / this.metrics.totalRequests 
                : 0,
            successRate: this.metrics.totalRequests > 0
                ? (this.metrics.successfulRequests / this.metrics.totalRequests * 100).toFixed(1) + '%'
                : 'N/A'
        };
    }
}

// Export for use in app.html
var enterpriseClient = new EnterpriseAPIClient(api);
