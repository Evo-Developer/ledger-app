# 🔧 Troubleshooting Guide

## Common Issues and Solutions

### 1. Port Already in Use

**Symptoms:**
- Error: "port is already allocated"
- Cannot access http://localhost

**Solution:**
```bash
# Option A: Stop conflicting services
# Check what's using port 80
sudo lsof -i :80
# Kill the process or stop the service

# Option B: Change ports in docker-compose.yml
# Edit the frontend section:
frontend:
  ports:
    - "8080:80"  # Use port 8080 instead of 80

# Then access at http://localhost:8080
```

### 2. Database Connection Failed

**Symptoms:**
- Backend logs show "Can't connect to MySQL"
- Health check fails

**Solution:**
```bash
# Wait for MySQL to initialize (first run takes ~30 seconds)
docker-compose logs db | grep "ready for connections"

# If still failing, restart database
docker-compose restart db

# Check database is running
docker-compose ps db
```

### 3. Backend Not Starting

**Symptoms:**
- Backend container exits immediately
- 500 errors on frontend

**Solution:**
```bash
# Check backend logs
docker-compose logs backend

# Common issues:
# - Missing dependencies: Rebuild
docker-compose up --build backend

# - Database not ready: Wait and restart
sleep 30
docker-compose restart backend

# - Environment variables: Check backend/.env exists
ls backend/.env
```

### 4. Frontend Shows White Page

**Symptoms:**
- Blank page at http://localhost
- No errors in browser console

**Solution:**
```bash
# Check frontend logs
docker-compose logs frontend

# Rebuild frontend
docker-compose up --build frontend

# Check nginx configuration
docker exec ledger_frontend cat /etc/nginx/conf.d/nginx.conf
```

### 5. Authentication Issues

**Symptoms:**
- Login fails
- Token invalid errors
- Redirected to login repeatedly

**Solution:**
```bash
# Check if SECRET_KEY is set
docker exec ledger_backend env | grep SECRET_KEY

# Generate new secret key
openssl rand -hex 32

# Update backend/.env with new key
# Restart backend
docker-compose restart backend

# Clear browser localStorage
# In browser console: localStorage.clear()
```

### 6. Transactions Not Saving

**Symptoms:**
- Created transactions don't appear
- 400/500 errors when creating

**Solution:**
```bash
# Check backend logs
docker-compose logs backend | tail -50

# Verify database tables exist
docker exec -it ledger_db mysql -u ledger_user -pledger_pass -e "USE ledger_db; SHOW TABLES;"

# If tables missing, recreate
docker-compose restart backend
# Tables are auto-created on backend startup
```

### 7. Slow Performance

**Symptoms:**
- App takes long to load
- Transactions slow to appear

**Solution:**
```bash
# Check resource usage
docker stats

# Allocate more resources in Docker Desktop:
# Settings → Resources → Increase CPU/Memory

# Check database size
docker exec ledger_db mysql -u ledger_user -pledger_pass -e "SELECT table_schema AS 'Database', ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS 'Size (MB)' FROM information_schema.tables WHERE table_schema = 'ledger_db' GROUP BY table_schema;"
```

### 8. Docker Commands Not Working

**Symptoms:**
- "docker command not found"
- "permission denied"

**Solution:**
```bash
# Verify Docker is installed
docker --version

# On Linux, add user to docker group
sudo usermod -aG docker $USER
# Log out and back in

# On Windows/Mac, ensure Docker Desktop is running
```

### 9. Can't Access API Documentation

**Symptoms:**
- http://localhost:8000/docs shows 404

**Solution:**
```bash
# Check backend is running
docker-compose ps backend

# Check port mapping
docker-compose ps | grep 8000

# Try accessing health endpoint
curl http://localhost:8000/health

# If using different port, update URL
# http://localhost:YOUR_PORT/docs
```

### 10. Data Loss After Restart

**Symptoms:**
- All data disappears when restarting
- Users need to re-register

**Solution:**
```bash
# Verify volumes are persisted
docker volume ls | grep ledger

# Don't use -v flag when stopping
docker-compose down  # Good - keeps data
# NOT: docker-compose down -v  # Bad - deletes data

# Create regular backups
./backup.sh
```

## Complete Reset

If nothing works, start fresh:

```bash
# 1. Stop everything
docker-compose down -v

# 2. Remove all containers
docker-compose rm -f

# 3. Remove images
docker-compose down --rmi all

# 4. Rebuild from scratch
docker-compose up --build -d

# 5. Wait for initialization
sleep 30

# 6. Check status
docker-compose ps
```

## Debugging Steps

### Check All Services

```bash
# View status
docker-compose ps

# All should show "Up" status
# If any show "Exit", check logs for that service
```

### View Logs

```bash
# All services
docker-compose logs

# Specific service
docker-compose logs backend
docker-compose logs db
docker-compose logs frontend

# Follow logs live
docker-compose logs -f

# Last 50 lines
docker-compose logs --tail=50
```

### Access Containers

```bash
# Backend shell
docker exec -it ledger_backend bash

# Database shell
docker exec -it ledger_db mysql -u ledger_user -pledger_pass ledger_db

# Frontend shell
docker exec -it ledger_frontend sh
```

### Network Issues

```bash
# Check if containers can communicate
docker-compose exec backend ping db
docker-compose exec backend ping frontend

# Inspect network
docker network inspect ledger_network
```

## Getting Help

1. **Collect Information:**
   ```bash
   docker-compose ps > status.txt
   docker-compose logs > logs.txt
   ```

2. **Check Logs** for error messages

3. **Verify Configuration:**
   - backend/.env exists
   - docker-compose.yml not modified incorrectly
   - Ports not in use by other services

4. **Test Each Component:**
   - Database: `docker-compose logs db`
   - Backend: `curl http://localhost:8000/health`
   - Frontend: `curl http://localhost`

## Prevention Tips

1. **Regular Backups:**
   ```bash
   # Run weekly
   ./backup.sh
   ```

2. **Monitor Resources:**
   ```bash
   docker stats
   ```

3. **Keep Docker Updated:**
   ```bash
   docker --version
   docker-compose --version
   ```

4. **Don't Modify:**
   - Database directly (use API)
   - Docker volumes manually
   - Container files directly

5. **Safe Shutdown:**
   ```bash
   docker-compose down  # NOT: docker-compose down -v
   ```

---

**Still having issues? Check the main README.md for more details.**
