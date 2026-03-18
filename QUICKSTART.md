# 🚀 Quick Start Guide

## For Mac/Linux Users

```bash
# 1. Navigate to the project folder
cd ledger-app

# 2. Run the start script
./start.sh

# 3. Open your browser
# Visit: http://localhost
```

## For Windows Users

```batch
# 1. Navigate to the project folder
cd ledger-app

# 2. Run the start script
start.bat

# 3. Open your browser
# Visit: http://localhost
```

## Manual Setup (All Platforms)

```bash
# 1. Navigate to project
cd ledger-app

# 2. Create environment file
cd backend
cp .env.example .env
cd ..

# 3. Start all services
docker-compose up --build -d

# 4. Open browser
# Visit: http://localhost
```

## First Time Login

1. Visit http://localhost (you'll see the login/register page)
2. **Register** (first time only):
   - Click on "Register" tab
   - Enter:
     - Full Name: Your Name
     - Email: your-email@example.com
     - Username: your-username
     - Password: secure-password (min 6 characters)
     - Confirm Password: (same password)
   - Click "Create Account"
   - You'll see "Account created successfully!"
3. **Login**:
   - Switch to "Login" tab (or wait, it switches automatically)
   - Enter your username and password
   - Click "Sign In"
   - You'll be redirected to the main app
4. Start tracking your finances!

**Note:** The app is protected. You cannot access the main app without logging in first. Your session persists, so you won't need to login every time unless you logout.

## Common Commands

```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f backend
docker-compose logs -f db
docker-compose logs -f frontend

# Stop all services
docker-compose down

# Restart services
docker-compose restart

# Stop and remove all data (fresh start)
docker-compose down -v
docker-compose up --build -d

# Access database directly
docker exec -it ledger_db mysql -u ledger_user -pledger_pass ledger_db
```

## Testing the API

Visit http://localhost:8000/docs for interactive API documentation.

## Troubleshooting

### Port Already in Use

Edit `docker-compose.yml` and change the ports:
```yaml
frontend:
  ports:
    - "8080:80"  # Change from 80 to 8080

backend:
  ports:
    - "8001:8000"  # Change from 8000 to 8001
```

### Database Connection Issues

Wait 30 seconds for MySQL to fully initialize on first run:
```bash
docker-compose logs db
# Look for: "ready for connections"
```

### Clear Everything and Start Fresh

```bash
docker-compose down -v
docker-compose up --build -d
```

## Default Credentials

**Database (for development only):**
- Host: localhost:3306
- Database: ledger_db
- Username: ledger_user
- Password: ledger_pass

**Change these in production!**

## Security Notes

- Change SECRET_KEY in backend/.env
- Change database passwords in docker-compose.yml
- Keep on local network only
- Don't expose to internet without proper security
- Regular backups recommended

## Need Help?

1. Check logs: `docker-compose logs`
2. Verify containers: `docker-compose ps`
3. Check README.md for detailed documentation
4. Check API docs: http://localhost:8000/docs

---

**Happy Tracking! 💰**
