// API Helper Functions
class API {
    constructor() {
        this.token = localStorage.getItem('token');
    }

    getApiBaseUrls() {
        const urls = [];
        const pushUrl = (value) => {
            if (value && !urls.includes(value)) {
                urls.push(value);
            }
        };

        // Allows overriding the base API URL from the page (e.g. for testing)
        pushUrl(window.API_BASE_URL);
        pushUrl(window.location.origin + '/api');

        // Local development sometimes serves the frontend without the /api proxy.
        if (['localhost', '127.0.0.1'].includes(window.location.hostname) && window.location.port !== '8000' && window.location.protocol !== 'https:') {
            pushUrl(`http://${window.location.hostname}:8000/api`);
        }

        return urls;
    }

    getApiBaseUrl() {
        return this.getApiBaseUrls()[0];
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

    async parseResponseBody(response) {
        if (response.status === 204) {
            return null;
        }

        const text = await response.text();
        if (!text) {
            return null;
        }

        const contentType = (response.headers.get('content-type') || '').toLowerCase();
        const isJson = contentType.includes('application/json') || contentType.includes('+json');

        if (isJson) {
            try {
                return JSON.parse(text);
            } catch (error) {
                throw new Error('The API returned invalid JSON.');
            }
        }

        return {
            rawText: text,
            isHtml: text.trim().startsWith('<'),
        };
    }

    getErrorMessage(response, payload, fallbackMessage) {
        if (payload && typeof payload === 'object' && !payload.isHtml) {
            const detail = payload.detail;
            if (Array.isArray(detail)) {
                // FastAPI validation errors: [{loc, msg, type}, ...]
                const msg = detail.map(e => e.msg || JSON.stringify(e)).join('; ');
                return msg || fallbackMessage;
            }
            return detail || payload.message || fallbackMessage;
        }

        if (payload && payload.isHtml) {
            return 'The app reached an HTML page instead of the API. Check that the frontend is pointing to the backend.';
        }

        return fallbackMessage;
    }

    async fetchJson(endpoint, options = {}) {
        const baseUrls = this.getApiBaseUrls();
        let lastError = null;

        for (let index = 0; index < baseUrls.length; index += 1) {
            const baseUrl = baseUrls[index];
            const url = `${baseUrl}${endpoint}`;

            try {
                const response = await fetch(url, options);
                const payload = await this.parseResponseBody(response);
                const shouldRetry = payload && payload.isHtml && index < baseUrls.length - 1;

                if (response.ok && !(payload && payload.isHtml)) {
                    return { response, data: payload };
                }

                const fallbackMessage = `Request failed: ${response.status} ${response.statusText}`;
                const errorMessage = this.getErrorMessage(response, payload, fallbackMessage);

                if (shouldRetry) {
                    lastError = new Error(errorMessage);
                    continue;
                }

                const requestError = new Error(errorMessage);
                requestError.status = response.status;
                throw requestError;
            } catch (error) {
                lastError = error;
                if (error && error.status) {
                    throw error;
                }
                if (index === baseUrls.length - 1) {
                    throw error;
                }
            }
        }

        throw lastError || new Error('API request failed');
    }

    async request(endpoint, options = {}) {
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
            const { response, data } = await this.fetchJson(endpoint, config);
            
            if (response.status === 401) {
                // Unauthorized - clear token and redirect to login
                this.clearToken();
                window.location.href = '/login.html';
                throw new Error('Unauthorized');
            }

            return data;
        } catch (error) {
            if (error && error.status === 401) {
                this.clearToken();
                window.location.href = '/login.html';
            }
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
        formData.append('grant_type', 'password');
        formData.append('username', username);
        formData.append('password', password);

        const { data } = await this.fetchJson('/auth/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: formData,
        });
        this.setToken(data.access_token);
        return data;
    }

    async getCurrentUser() {
        return this.request('/auth/me');
    }

    async updateMyProfile(profile) {
        return this.request('/auth/me/profile', {
            method: 'PUT',
            body: JSON.stringify(profile),
        });
    }

    async changeMyPassword(currentPassword, newPassword) {
        return this.request('/auth/me/password', {
            method: 'POST',
            body: JSON.stringify({
                current_password: currentPassword,
                new_password: newPassword,
            }),
        });
    }

    async externalProvisionUser(payload, apiKey) {
        return this.request('/rbac/external/provision-user', {
            method: 'POST',
            headers: apiKey ? { 'X-RBAC-API-Key': apiKey } : {},
            body: JSON.stringify(payload),
        });
    }

    async externalFederatedSync(payload, apiKey) {
        return this.request('/rbac/external/federated-sync', {
            method: 'POST',
            headers: apiKey ? { 'X-RBAC-API-Key': apiKey } : {},
            body: JSON.stringify(payload),
        });
    }

    // Transactions
    async getTransactions() {
        return this.request('/transactions?limit=5000');
    }

    async createTransaction(transaction) {
        return this.request('/transactions', {
            method: 'POST',
            body: JSON.stringify(transaction),
        });
    }

    async uploadTransactionsCsv(file) {
        const formData = new FormData();
        formData.append('file', file);

        const headers = { ...this.getHeaders() };
        delete headers['Content-Type'];

        const { data } = await this.fetchJson('/transactions/upload', {
            method: 'POST',
            body: formData,
            headers,
        });
        return data;
    }

    async uploadStatementFile(file) {
        const formData = new FormData();
        formData.append('file', file);

        const headers = { ...this.getHeaders() };
        delete headers['Content-Type'];

        const { data } = await this.fetchJson('/transactions/upload-statement-file', {
            method: 'POST',
            body: formData,
            headers,
        });
        return data;
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

    async updateBudget(id, budget) {
        return this.request(`/budgets/${id}`, {
            method: 'PUT',
            body: JSON.stringify(budget),
        });
    }

    async deleteBudget(id) {
        return this.request(`/budgets/${id}`, {
            method: 'DELETE',
        });
    }

    async getBudgetsWithSpending() {
        return this.request('/budgets/spending/monthly');
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

    async updateGoal(id, goal) {
        return this.request(`/goals/${id}`, {
            method: 'PUT',
            body: JSON.stringify(goal),
        });
    }

    async deleteGoal(id) {
        return this.request(`/goals/${id}`, {
            method: 'DELETE',
        });
    }

    // Investments
    async getInvestments() {
        return this.request('/investments');
    }

    async createInvestment(investment) {
        return this.request('/investments', {
            method: 'POST',
            body: JSON.stringify(investment),
        });
    }

    async updateInvestment(id, investment) {
        return this.request(`/investments/${id}`, {
            method: 'PUT',
            body: JSON.stringify(investment),
        });
    }

    async deleteInvestment(id) {
        return this.request(`/investments/${id}`, {
            method: 'DELETE',
        });
    }

    // Liabilities
    async getLiabilities() {
        return this.request('/liabilities');
    }

    async createLiability(liability) {
        return this.request('/liabilities', {
            method: 'POST',
            body: JSON.stringify(liability),
        });
    }

    async updateLiability(id, liability) {
        return this.request(`/liabilities/${id}`, {
            method: 'PUT',
            body: JSON.stringify(liability),
        });
    }

    async deleteLiability(id) {
        return this.request(`/liabilities/${id}`, {
            method: 'DELETE',
        });
    }

    // Assets
    async getAssets() {
        return this.request('/assets');
    }

    async createAsset(asset) {
        return this.request('/assets', {
            method: 'POST',
            body: JSON.stringify(asset),
        });
    }

    async updateAsset(id, asset) {
        return this.request(`/assets/${id}`, {
            method: 'PUT',
            body: JSON.stringify(asset),
        });
    }

    async deleteAsset(id) {
        return this.request(`/assets/${id}`, {
            method: 'DELETE',
        });
    }

    // Documents
    async getDocuments() {
        return this.request('/documents');
    }

    async uploadDocument(title, file, folder = 'General', subfolder = '') {
        const formData = new FormData();
        formData.append('title', title);
        formData.append('folder', folder || 'General');
        formData.append('subfolder', subfolder || '');
        formData.append('file', file);

        const headers = { ...this.getHeaders() };
        delete headers['Content-Type'];

        const { data } = await this.fetchJson('/documents', {
            method: 'POST',
            body: formData,
            headers,
        });
        return data;
    }

    async deleteDocument(id) {
        return this.request(`/documents/${id}`, {
            method: 'DELETE',
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

    async updateIntegration(appName, update) {
        return this.request(`/integrations/${appName}`, {
            method: 'PUT',
            body: JSON.stringify(update),
        });
    }

    async deleteIntegration(appName) {
        return this.request(`/integrations/${appName}`, {
            method: 'DELETE',
        });
    }

    async syncIntegration(appName) {
        return this.request(`/integrations/${appName}/sync`, {
            method: 'POST',
        });
    }

    async getGmailAuthUrl() {
        return this.request('/integrations/gmail/auth-url');
    }

    async syncGmailBankAlerts() {
        return this.request('/integrations/gmail/sync-bank-alerts', {
            method: 'POST',
        });
    }

    // Audit Logs
    async getAuditLogs() {
        return this.request('/audit-logs');
    }

    // Users / RBAC
    async getUsers() {
        return this.request('/users');
    }

    async updateUserRole(userId, role) {
        return this.request(`/users/${userId}/role`, {
            method: 'PUT',
            body: JSON.stringify({ role }),
        });
    }

    async updateUserStatus(userId, isActive) {
        return this.request(`/users/${userId}/status`, {
            method: 'PUT',
            body: JSON.stringify({ is_active: isActive }),
        });
    }

    async updateUserPermissions(userId, permissions) {
        return this.request(`/users/${userId}/permissions`, {
            method: 'PUT',
            body: JSON.stringify({ permissions }),
        });
    }

    async deleteUser(userId) {
        return this.request(`/users/${userId}`, {
            method: 'DELETE',
        });
    }

    async resetAllFinancialData(password) {
        return this.request('/admin/reset-all-data', {
            method: 'POST',
            body: JSON.stringify({ password }),
        });
    }

    // Dashboard
    async getDashboardStats() {
        return this.request('/dashboard/stats');
    }

    async sendExpenseReportEmail(recipientEmail, reportMonth) {
        return this.request('/reports/expense-email', {
            method: 'POST',
            body: JSON.stringify({
                recipient_email: recipientEmail,
                report_month: reportMonth || null,
            }),
        });
    }

    async exportAllDataCsv() {
        const response = await fetch(`${this.getApiBaseUrl()}/data/export-csv`, {
            method: 'GET',
            headers: this.getHeaders(),
        });
        if (!response.ok) {
            throw new Error(`Export failed: ${response.status} ${response.statusText}`);
        }
        return response.blob();
    }

    async importAllDataCsv(file) {
        const formData = new FormData();
        formData.append('file', file);
        const headers = { ...this.getHeaders() };
        delete headers['Content-Type'];

        const { data } = await this.fetchJson('/data/import-csv', {
            method: 'POST',
            body: formData,
            headers,
        });
        return data;
    }
}

// Export API instance
// Use `var` to ensure the global `api` identifier is available across all scripts.
var api = new API();
window.api = window.api || api;
