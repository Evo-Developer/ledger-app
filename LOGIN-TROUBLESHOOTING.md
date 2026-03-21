# 🔧 Login "Failed to Fetch" Troubleshooting Guide

If you're seeing **"Failed to fetch"** when trying to login, follow these steps:

## Quick Fix (Try First!)

```bash
cd /Users/ravikumar/projects/ledger-app
chmod +x fix-login.sh
./fix-login.sh
```

Then open http://localhost in your browser.

---

## Manual Troubleshooting Steps

### Step 1: Verify Docker is Running

**On Mac:**
```bash
# Check if Docker is running
docker ps

# If command not found, start Docker:
open -a Docker

# Wait ~30 seconds for Docker to start, then try again
docker ps
```

**On Linux:**
```bash
sudo systemctl start docker
docker ps
```

**On Windows:**
- Open Docker Desktop application
- Wait for it to be fully running

### Step 2: Check Current Container Status

```bash
# See all containers
docker ps -a

# You should see:
# ledger_db (MySQL database)
# ledger_backend (FastAPI server)  
# ledger_frontend (Nginx)
```

If containers don't exist or are stopped:
```bash
cd /Users/ravikumar/projects/ledger-app

# Start all services
docker-compose up -d

# Wait 10-15 seconds for initialization
sleep 15

# Check status again
docker-compose ps
```

### Step 3: Check Individual Services

#### Database Connection
```bash
docker exec ledger_db mysqladmin ping -h localhost -u root -prootpassword
# Expected output: mysqld is alive
```

If fails:
```bash
# Check database logs
docker logs ledger_db | tail -30
```

#### Backend API Health
```bash
docker exec ledger_backend curl -s http://localhost:8000/health
# Expected output: {"status":"ok"}
```

If fails:
```bash
# Check backend logs
docker logs -f ledger_backend

# Look for errors like:
# - "Connection refused" (database not running)
# - "ModuleNotFoundError" (missing dependencies)
# - "Address already in use" (port conflict)
```

#### Frontend Server
```bash
docker exec ledger_frontend curl -s http://localhost/login.html | head -20
# Should show HTML content
```

### Step 4: Rebuild Everything (Nuclear Option)

If the above doesn't work:

```bash
cd /Users/ravikumar/projects/ledger-app

# Stop everything
docker-compose down

# Remove volumes (clears database)
docker volume rm ledger_db || true

# Clean up images
docker-compose down --rmi all

# Rebuild from scratch
docker-compose up -d --build

# Wait for initialization
echo "Waiting 20 seconds for services to initialize..."
sleep 20

# Verify
docker-compose ps
```

### Step 5: Test API Directly

```bash
# Try to login with test credentials (to test endpoint, not actual login)
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password&username=testuser&password=testpass"

# Expected response (even for wrong credentials):
# {"detail":"Incorrect username or password"}
#
# If you see this, the API is working!
```

---

## Common Error Messages & Fixes

### "Failed to fetch"
- **Cause**: Network error between frontend and backend
- **Fix**: Run `./fix-login.sh` or restart containers with `docker-compose up -d`

### "TypeError: Failed to fetch"
- **Cause**: Backend is not accessible from frontend
- **Check**:
  ```bash
  docker logs ledger_backend | tail -30
  ```
- **Fix**: Check if backend is running and database is accessible

### "Connection refused" (in backend logs)
- **Cause**: Backend can't connect to database
- **Fix**:
  ```bash
  docker logs ledger_db | tail -30
  # If database failed to start, try rebuilding volume
  docker volume rm ledger_db
  docker-compose down && docker-compose up -d --build
  ```

### "Address already in use"
- **Cause**: Port 80, 443, 8000, or 3306 is already in use
- **Fix**:
  ```bash
  # Kill service using the port (Linux/Mac)
  lsof -i :8000
  lsof -i :3306
  lsof -i :80
  
  # Or stop conflicting services and retry
  docker-compose down
  # Wait 5 seconds
  sleep 5
  docker-compose up -d
  ```

### "Database initialization failed"
- **Cause**: init.sql script failed or database permissions issue
- **Fix**:
  ```bash
  docker-compose down
  docker volume rm ledger_db
  docker-compose up -d --build
  sleep 20
  ```

---

## Advanced Debugging

### View Real-time Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f db
docker-compose logs -f frontend
```

### Browser Developer Tools
1. Open browser to http://localhost
2. Press **F12** to open Developer Tools
3. Go to **Console** tab
4. Try to login and look for error messages
5. Go to **Network** tab and click the failed request to see details

### Check Network Connectivity
```bash
# From frontend container to backend
docker exec ledger_frontend curl -v http://ledger_backend:8000/health

# From backend container to database
docker exec ledger_backend mysql -u ledger_user -pledger_pass -h db -D ledger_db -e "SELECT 1"
```

---

## Still Not Working?

Run the diagnostics script:
```bash
chmod +x diagnose.sh
./diagnose.sh
```

This will:
- Check Docker status
- Verify all containers
- Test database connectivity
- Test API endpoints
- Show you relevant logs

Share the output when asking for help!

---

## Expected Workflow

1. **First visit**: http://localhost → Login page
2. **First time**: Click "Register" → Create account
3. **Then**: Switch to "Login" tab → Enter credentials
4. **Success**: Redirected to main app dashboard

---

## Notes

- ✅ All services should be running (check with `docker-compose ps`)
- ✅ Database should initialize on first run (takes 10-15 seconds)
- ✅ Backend should connect to database (check logs if not)
- ✅ Frontend should proxy API requests to backend (nginx configured)

If you continue to have issues, collect the output from:
```bash
./diagnose.sh 2>&1 | tee diagnostics.log
```

And share that file for detailed support.
