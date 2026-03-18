// API Helper Functions
class API {
    constructor() {
        this.token = localStorage.getItem('token');
    }

    getApiBaseUrl() {
        // Allows overriding the base API URL from the page (e.g. for testing)
        return window.API_BASE_URL || (window.location.origin + '/api');
    }

    setToken(token) {
        this.token = token;
        localStorage.setItem('token', token);
    }

    clearToken() {
        this.token = null;
        localStorage.removeItem('token');
    }

    getHeaders() {
        const headers = {
            'Content-Type': 'application/json',
        };
        if (this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }
        return headers;
    }

    async request(endpoint, options = {}) {
        const url = `${this.getApiBaseUrl()}${endpoint}`;

        // Merge headers so callers can override default headers when needed
        const headers = {
            ...this.getHeaders(),
            ...(options.headers || {}),
        };

        const config = {
            ...options,
            headers,
        };

        try {
            const response = await fetch(url, config);
            
            if (response.status === 401) {
                // Unauthorized - clear token and redirect to login
                this.clearToken();
                window.location.href = '/login.html';
                throw new Error('Unauthorized');
            }

            if (!response.ok) {
                let errorMessage = `Request failed: ${response.status} ${response.statusText}`;
                try {
                    const error = await response.json();
                    errorMessage = error.detail || error.message || JSON.stringify(error);
                } catch {
                    // response was not JSON, fall back to HTTP status
                }
                throw new Error(errorMessage);
            }

            return await response.json();
        } catch (error) {
            console.error('API request failed:', error);
            throw error;
        }
    }

    // Authentication
    async register(email, username, password, fullName) {
        return this.request('/auth/register', {
            method: 'POST',
            body: JSON.stringify({ email, username, password, full_name: fullName }),
        });
    }

    async login(username, password) {
        const formData = new URLSearchParams();
        formData.append('username', username);
        formData.append('password', password);

        const response = await fetch(`${this.getApiBaseUrl()}/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: formData,
        });

        if (!response.ok) {
            let message = 'Login failed';
            try {
                const error = await response.json();
                message = error.detail || error.message || message;
            } catch {
                // ignore
            }
            throw new Error(message);
        }

        const data = await response.json();
        this.setToken(data.access_token);
        return data;
    }

    async getCurrentUser() {
        return this.request('/auth/me');
    }

    // Transactions
    async getTransactions() {
        return this.request('/transactions');
    }

    async createTransaction(transaction) {
        return this.request('/transactions', {
            method: 'POST',
            body: JSON.stringify(transaction),
        });
    }

    async updateTransaction(id, transaction) {
        return this.request(`/transactions/${id}`, {
            method: 'PUT',
            body: JSON.stringify(transaction),
        });
    }

    async deleteTransaction(id) {
        return this.request(`/transactions/${id}`, {
            method: 'DELETE',
        });
    }

    // Budgets
    async getBudgets() {
        return this.request('/budgets');
    }

    async createBudget(budget) {
        return this.request('/budgets', {
            method: 'POST',
            body: JSON.stringify(budget),
        });
    }

    // Goals
    async getGoals() {
        return this.request('/goals');
    }

    async createGoal(goal) {
        return this.request('/goals', {
            method: 'POST',
            body: JSON.stringify(goal),
        });
    }

    // Integrations
    async getIntegrations() {
        return this.request('/integrations');
    }

    async createIntegration(integration) {
        return this.request('/integrations', {
            method: 'POST',
            body: JSON.stringify(integration),
        });
    }

    async syncIntegration(appName) {
        return this.request(`/integrations/${appName}/sync`, {
            method: 'POST',
        });
    }

    // Audit Logs
    async getAuditLogs() {
        return this.request('/audit-logs');
    }

    // Dashboard
    async getDashboardStats() {
        return this.request('/dashboard/stats');
    }
}

// Export API instance
// Use `var` to ensure the global `api` identifier is available across all scripts.
var api = new API();
window.api = window.api || api;
