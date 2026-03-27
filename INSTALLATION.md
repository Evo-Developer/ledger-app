# 📦 Ledger App - Complete Package

## What You Have

A complete, production-ready personal finance tracking application with:

✅ **Full-Stack Application**
- FastAPI backend (Python)
- MySQL database
- Modern responsive frontend
- Docker containerization

✅ **Authentication & Security**
- User registration and login
- JWT token-based authentication
- Password hashing with bcrypt
- User-specific data isolation

✅ **Core Features**
- Transaction tracking (income/expense)
- Budget management
- Savings goals
- External app integrations
- Complete audit trail
- Interactive dashboards with drill-down

✅ **Production Ready**
- Docker Compose orchestration
- Database persistence
- Automatic table creation
- Health checks
- Nginx reverse proxy
- Environment configuration

## 📁 File Structure

```
ledger-app/
│
├── 📄 README.md                    # Complete documentation
├── 📄 QUICKSTART.md                # Quick start guide
├── 📄 TROUBLESHOOTING.md           # Troubleshooting guide
├── 🐳 docker-compose.yml           # Docker orchestration
├── 🗄️ init.sql                     # Database initialization
├── 📋 requirements.txt             # Python dependencies (root)
│
├── 🚀 start.sh                     # Linux/Mac startup script
├── 🚀 start.bat                    # Windows startup script
├── 💾 backup.sh                    # Database backup script
├── 💾 restore.sh                   # Database restore script
│
├── backend/                        # FastAPI Backend
│   ├── 🐳 Dockerfile               # Backend container config
│   ├── 📋 requirements.txt         # Python dependencies
│   ├── 🐍 main.py                  # Main API application
│   ├── 🐍 models.py                # Database models
│   ├── 🐍 schemas.py               # Pydantic schemas
│   ├── 🐍 database.py              # Database connection
│   ├── 🐍 auth.py                  # Authentication logic
│   └── ⚙️ .env.example             # Environment template
│
└── frontend/                       # Frontend Application
    ├── 🐳 Dockerfile               # Frontend container config
    ├── ⚙️ nginx.conf               # Nginx configuration
    ├── 🌐 index.html               # Main application
    └── assets/
        └── 📜 api.js               # API integration layer

```

## 🚀 Installation Steps

### Step 1: Prerequisites

Install Docker Desktop:
- **Windows/Mac**: Download from https://www.docker.com/products/docker-desktop
- **Linux**: Follow instructions at https://docs.docker.com/engine/install/

### Step 2: Extract Files

Extract the `ledger-app` folder to your desired location:
```
C:\Users\YourName\ledger-app     # Windows
/Users/YourName/ledger-app       # Mac
/home/username/ledger-app        # Linux
```

### Step 3: Start the Application

**On Windows:**
1. Open `ledger-app` folder
2. Double-click `start.bat`
3. Wait for services to start
4. Open browser to http://localhost

**On Mac/Linux:**
1. Open Terminal
2. Navigate to folder: `cd /path/to/ledger-app`
3. Run: `./start.sh`
4. Open browser to http://localhost

**Manual Start:**
```bash
cd ledger-app
docker-compose up --build -d
```

### Step 4: First-Time Setup

1. Open http://localhost
2. Click "Register"
3. Create your account:
   - Email: your-email@example.com
   - Username: choose a username
   - Full Name: Your Name
   - Password: secure password
4. Login with credentials
5. Start tracking!

## 🔐 Security Configuration

### Change Default Passwords (Important!)

Edit `docker-compose.yml`:
```yaml
db:
  environment:
    MYSQL_ROOT_PASSWORD: YOUR_STRONG_PASSWORD_HERE
    MYSQL_PASSWORD: YOUR_DB_PASSWORD_HERE
```

### Generate Secure Secret Key

```bash
# On Mac/Linux
openssl rand -hex 32

# Copy the output to backend/.env
SECRET_KEY=paste-generated-key-here
```

## 📊 Usage Examples

### Creating Transactions

1. Click "Add Transaction"
2. Fill details:
   - Type: Income or Expense
   - Description: "Salary", "Grocery", etc.
   - Amount: 5000
   - Category: Food, Transport, etc.
   - Date: Select date
3. Save

### Setting Budgets

1. Go to "Budgets" tab
2. Click "Add Budget"
3. Select category
4. Set monthly limit
5. Track spending vs budget

### External Integrations

1. Go to "Integrations" tab
2. Click on app (PhonePe, Groww, etc.)
3. Enter credentials (demo mode available)
4. Click "Sync"
5. Transactions auto-imported

### Viewing Insights

- Click on **Balance** card → See income/expense sources
- Click on **Income** card → Income breakdown
- Click on **Expenses** card → Spending patterns
- Click on **Savings** card → Cash flow analysis

## 🗄️ Database Backup

### Create Backup
```bash
./backup.sh
```

Backups saved in `backups/` folder.

### Restore Backup
```bash
./restore.sh
```

Choose backup file to restore.

## 🛠️ Useful Commands

### View Logs
```bash
docker-compose logs -f
```

### Stop Application
```bash
docker-compose down
```

### Restart Services
```bash
docker-compose restart
```

### Complete Reset
```bash
docker-compose down -v
docker-compose up --build -d
```

## 📡 API Access

Interactive API documentation:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## 🔌 Ports Used

- **80**: Frontend (Nginx)
- **8000**: Backend (FastAPI)
- **3306**: Database (MySQL)
- **3000**: Grafana
- **9090**: Prometheus
```yaml
ports:
  - "8080:80"   # Use 8080 instead of 80
```

## 👥 Family Members

Each family member can:
1. Create their own account
2. Track personal finances separately
3. Data is completely isolated per user
4. All stored securely in MySQL

## 💡 Tips

1. **Regular Backups**: Run `./backup.sh` weekly
2. **Use Categories**: Organize transactions properly
3. **Set Budgets**: Track spending limits
4. **Review Audit Trail**: See all changes
5. **Export Data**: Use audit log export feature

## ⚠️ Important Notes

### For Local/Family Use Only

This setup is optimized for:
- Home networks
- Family members
- Local Docker deployment

**NOT recommended for:**
- Public internet exposure
- Production hosting
- Untrusted users

### Security Best Practices

1. ✅ Change default passwords
2. ✅ Generate secure SECRET_KEY
3. ✅ Keep on local network
4. ✅ Regular backups
5. ✅ Update Docker images periodically

## 🐛 Issues?

1. Check TROUBLESHOOTING.md
2. View logs: `docker-compose logs`
3. Verify containers: `docker-compose ps`
4. Review README.md

## 📚 Documentation Files

- **README.md** - Complete documentation
- **QUICKSTART.md** - Quick setup guide
- **TROUBLESHOOTING.md** - Common issues and solutions

## 🎉 You're All Set!

Your personal finance tracker is ready to use. Enjoy tracking your finances with clarity and confidence!

---

**Version**: 1.0.0  
**Created**: 2024  
**Stack**: FastAPI + MySQL + Docker  
**Purpose**: Family Finance Tracking
