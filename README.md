# Ledger - Personal Finance Tracker

A full-stack personal finance tracking application with FastAPI backend, MySQL database, and beautiful responsive frontend. Designed for family members to track their expenses, income, budgets, and financial goals.

## 🏗️ Architecture

- **Frontend**: HTML/CSS/JavaScript with modern UI
- **Backend**: FastAPI (Python)
- **Database**: MySQL 8.0
- **Authentication**: JWT-based authentication
- **Deployment**: Docker & Docker Compose

## 🔒 Security Features

This application implements **enterprise-grade security** and is **Post-Quantum Cryptography (PQC) ready**.

### Secure Coding Practices

✅ **Password Security**
- Argon2id hashing (quantum-resistant, memory-hard)
- Password complexity requirements
- Protection against rainbow table attacks
- Secure password storage

✅ **Authentication & Authorization**
- JWT-based authentication with secure claims
- Short token expiration (30 minutes)
- Refresh token support
- Rate limiting (5 login attempts per 5 minutes)
- Session management

✅ **Input Validation**
- SQL injection prevention (parameterized queries)
- XSS prevention (HTML sanitization)
- Input length limits
- Type validation
- Pattern matching

✅ **Security Headers**
- Content Security Policy (CSP)
- X-Frame-Options (clickjacking prevention)
- X-Content-Type-Options (MIME sniffing prevention)
- XSS Protection headers
- HSTS support (for HTTPS)

✅ **Audit & Compliance**
- Complete audit trail
- Security event logging
- Suspicious activity detection
- OWASP Top 10 (2021) compliant
- PCI DSS ready

### Post-Quantum Cryptography (PQC)

**Current Status:** PQC-Ready ✅

- **Argon2id** for password hashing (quantum-resistant)
- Modular cryptographic design (easy algorithm swapping)
- Upgrade path to NIST PQC standards (Dilithium, KYBER)
- See [PQC-GUIDE.md](PQC-GUIDE.md) for details

### Security Testing

Run automated security tests:
```bash
./security-test.sh
```

Tests include:
- SECRET_KEY strength
- Security headers
- SQL injection protection
- Rate limiting
- Password requirements
- Input validation
- Dependency vulnerabilities

For complete security documentation, see [SECURITY.md](SECURITY.md).

## 📋 Features

✅ **Authentication & Security**
- Secure login/register system
- JWT token-based authentication
- Password strength indicator
- Auto-redirect if not authenticated
- Logout functionality
- Session persistence

✅ **User Authentication**
- Secure registration and login
- JWT token-based authentication
- User profiles with personalized data

✅ **Transaction Management**
- Track income and expenses
- Categorize transactions
- Add notes and details
- Edit and delete manual entries
- Advanced filtering (date range, category, amount, etc.)
- Pagination for large datasets

✅ **Budget Tracking**
- Set monthly budgets by category
- Visual progress indicators
- Overspending alerts

✅ **Savings Goals**
- Create financial goals
- Track progress
- Visual progress bars

✅ **External Integrations**
- Connect to apps like PhonePe, Groww, Paytm, GPay, CRED, Zerodha
- Auto-sync transactions
- Mark synced transactions as read-only

✅ **Audit Trail**
- Complete activity logging
- Track all create, update, delete operations
- Filter by date, action, entity type
- Export audit logs to CSV

✅ **Interactive Dashboards**
- Click on overview cards to drill down
- Detailed breakdowns by category and source
- Visual charts and graphs
- Real-time calculations

## 🚀 Quick Start

### Prerequisites

- Docker Desktop installed
- At least 4GB RAM available
- Ports 80, 3306, and 8000 available

### Installation

1. **Clone or download this project**
   ```bash
   cd ledger-app
   ```

2. **Configure environment variables (optional)**
   ```bash
   cd backend
   cp .env.example .env
   # Edit .env with your preferred settings
   cd ..
   ```

3. **Build and start all services**
   ```bash
   docker-compose up --build
   ```

   This will:
   - Start MySQL database on port 3306
   - Start FastAPI backend on port 8000
   - Start Nginx frontend on port 80
   - Create database tables automatically
   - Set up networking between containers

4. **Access the application**
   - Frontend: http://localhost (Login page)
   - API Documentation: http://localhost:8000/docs
   - API Health Check: http://localhost:8000/health

### First-Time Setup

1. Open http://localhost in your browser (you'll see the login page)
2. Click "Register" tab to create your account
3. Fill in your details:
   - Full Name
   - Email
   - Username
   - Password (minimum 6 characters)
   - Confirm Password
4. Click "Create Account"
5. Switch to "Login" tab
6. Enter your username and password
7. Click "Sign In"
8. You'll be redirected to the main app
9. Start tracking your finances!

**Important:** The app requires authentication. You must create an account and login before accessing any features.

## 📁 Project Structure

```
ledger-app/
├── docker-compose.yml          # Docker orchestration
├── init.sql                    # Database initialization
├── README.md                   # This file
│
├── backend/                    # FastAPI backend
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                # Main API application
│   ├── models.py              # SQLAlchemy models
│   ├── schemas.py             # Pydantic schemas
│   ├── database.py            # Database configuration
│   ├── auth.py                # Authentication utilities
│   └── .env.example           # Environment variables template
│
└── frontend/                   # Frontend application
    ├── Dockerfile
    ├── nginx.conf             # Nginx configuration
    ├── index.html             # Main application
    └── assets/                # Static assets (optional)
```

## 🔧 Configuration

### Environment Variables

Edit `backend/.env`:

```env
# Database
DATABASE_URL=mysql+pymysql://ledger_user:ledger_pass@db:3306/ledger_db

# Security (CHANGE THESE IN PRODUCTION!)
SECRET_KEY=your-secret-key-change-this
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### Database Credentials

Default credentials (change in `docker-compose.yml` for production):
- **Root Password**: rootpassword
- **Database**: ledger_db
- **User**: ledger_user
- **Password**: ledger_pass

## 🎯 Usage

### Creating Your First Transaction

1. Click "Add Transaction" button
2. Fill in:
   - Type (Income/Expense)
   - Description
   - Amount
   - Category
   - Date
   - Notes (optional)
3. Click "Add Transaction"

### Setting Up Budgets

1. Go to "Budgets" tab
2. Click "Add Budget"
3. Select category and set monthly limit
4. Track your spending against budgets

### Connecting External Apps

1. Go to "Integrations" tab
2. Click on an app card (PhonePe, Groww, etc.)
3. Enter API credentials (demo mode available)
4. Click "Connect & Sync"
5. Transactions will be automatically imported

### Using Filters

1. Click "Filters" button on Transactions page
2. Set desired filters:
   - Date range
   - Type (Income/Expense)
   - Category
   - Source
   - Amount range
   - Text search
3. Click "Apply Filters"

### Viewing Audit Trail

1. Go to "Audit Trail" tab
2. See all activities
3. Use filters to narrow down
4. Export to CSV for compliance

### Interactive Dashboards

- Click on **Balance** card to see income/expense sources
- Click on **Income** card to see income breakdown by category and source
- Click on **Expenses** card to see spending breakdown
- Click on **Savings Rate** card to see cash flow analysis

## 🐳 Docker Commands

### Start services
```bash
docker-compose up -d
```

### Stop services
```bash
docker-compose down
```

### View logs
```bash
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f db
```

### Restart a service
```bash
docker-compose restart backend
```

### Rebuild after code changes
```bash
docker-compose up --build
```

### Access MySQL directly
```bash
docker exec -it ledger_db mysql -u ledger_user -pledger_pass ledger_db
```

### Access backend shell
```bash
docker exec -it ledger_backend bash
```

## 🔒 Security Notes

### For Family Use (Local Network)

This setup is designed for family members on the same local network:

1. **Change default passwords** in `docker-compose.yml`
2. **Generate a strong SECRET_KEY**:
   ```bash
   openssl rand -hex 32
   ```
3. **Keep it on your local network** - don't expose to internet
4. **Regular backups** of MySQL data:
   ```bash
   docker exec ledger_db mysqldump -u ledger_user -pledger_pass ledger_db > backup.sql
   ```

### For Production Deployment

If deploying to production:
- Use HTTPS (add SSL certificates)
- Set strong passwords
- Configure CORS properly
- Use environment secrets
- Set up regular backups
- Enable rate limiting
- Add monitoring

## 📊 API Documentation

Once running, visit http://localhost:8000/docs for:
- Interactive API documentation
- Test endpoints directly
- View request/response schemas
- Authentication testing

## 🛠️ Development

### Backend Development

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

### Database Migrations

Using Alembic (if you make model changes):

```bash
cd backend
alembic init alembic
alembic revision --autogenerate -m "description"
alembic upgrade head
```

## 🧪 Testing

API endpoints with curl:

```bash
# Register a user
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","username":"testuser","password":"password123"}'

# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=password123"

# Get transactions (with token)
curl -X GET http://localhost:8000/api/transactions \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

## ❓ Troubleshooting

### Database connection errors
```bash
# Wait for MySQL to be ready
docker-compose logs db
# Look for "ready for connections"
```

### Port already in use
```bash
# Change ports in docker-compose.yml
# Frontend: "8080:80"
# Backend: "8001:8000"
# Database: "3307:3306"
```

### Clear all data and start fresh
```bash
docker-compose down -v  # Removes volumes
docker-compose up --build
```

## 📝 Future Enhancements

- [ ] Mobile app (React Native)
- [ ] Recurring transactions
- [ ] Bill reminders
- [ ] Investment tracking
- [ ] Multi-currency support
- [ ] Data export (CSV, PDF)
- [ ] Receipt uploads
- [ ] Spending insights with AI

## 📄 License

This project is for personal/family use. Modify as needed for your requirements.

## 🤝 Contributing

Since this is a family project, feel free to:
1. Fork for your family
2. Customize categories
3. Add integrations
4. Improve UI/UX
5. Share improvements back!

## 💬 Support

For issues:
1. Check logs: `docker-compose logs`
2. Verify all containers are running: `docker-compose ps`
3. Check database connection
4. Review API documentation at `/docs`

---

**Happy tracking! 💰📊**
