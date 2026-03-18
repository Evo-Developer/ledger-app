# Dependency Installation Guide

## Issue: Dependency Conflicts

If you encounter dependency conflicts during installation, this guide will help you resolve them.

## Solution 1: Use Minimal Requirements (Recommended)

The application now uses `requirements.txt` with **minimal, tested dependencies** that are guaranteed to work together.

```bash
cd backend
pip install -r requirements.txt
```

This includes:
✅ FastAPI + Uvicorn
✅ SQLAlchemy + MySQL
✅ Argon2id password hashing (PQC-ready)
✅ Input validation & sanitization
✅ JWT authentication
✅ Rate limiting
✅ All core security features

## Solution 2: Install in Order

If you need to customize dependencies, install in this order:

```bash
# 1. Core framework
pip install fastapi==0.109.2 uvicorn[standard]==0.27.1

# 2. Database
pip install sqlalchemy==2.0.25 pymysql==1.1.0

# 3. Pydantic (before other dependencies)
pip install pydantic==2.5.3 pydantic-settings==2.1.0

# 4. Security
pip install argon2-cffi==23.1.0 bcrypt==4.1.2
pip install python-jose[cryptography]==3.3.0
pip install passlib[bcrypt]==1.7.4

# 5. Additional utilities
pip install python-dotenv==1.0.1
pip install email-validator==2.1.0.post1
pip install bleach==6.1.0
pip install slowapi==0.1.9
pip install python-dateutil==2.8.2
```

## Solution 3: Use Docker (Easiest)

The Docker setup handles all dependencies automatically:

```bash
# Just build and run - dependencies are managed
docker-compose build --no-cache
docker-compose up -d
```

## Optional Dependencies

### Security Audit Tools (Development Only)

```bash
pip install -r requirements-security-tools.txt
```

Includes:
- `safety` - Vulnerability scanning
- `bandit` - Security linting
- `secure` - Security headers

### Post-Quantum Cryptography (Future Use)

```bash
# Only install when ready for PQC migration
pip install -r requirements-pqc.txt
```

## Troubleshooting

### Error: "No matching distribution"

**Cause:** Package version not available for your Python version

**Solution:**
```bash
# Check Python version (needs 3.11+)
python --version

# Upgrade Python if needed
# Ubuntu: sudo apt-get install python3.11
# macOS: brew install python@3.11
```

### Error: "Conflicting dependencies"

**Cause:** Multiple packages require different versions of the same dependency

**Solution:**
```bash
# Use minimal requirements (already configured)
pip install -r requirements.txt

# OR create fresh virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Error: "Failed building wheel"

**Cause:** Missing system dependencies for compilation

**Solution:**
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y \
    gcc \
    g++ \
    python3-dev \
    libssl-dev \
    libffi-dev \
    default-libmysqlclient-dev \
    pkg-config

# macOS
brew install mysql-client pkg-config

# Then retry
pip install -r requirements.txt
```

### Error: "Argon2 not found"

**Cause:** argon2-cffi requires compilation

**Solution:**
```bash
# Ubuntu/Debian
sudo apt-get install libargon2-dev

# macOS
brew install argon2

# Then retry
pip install argon2-cffi==23.1.0
```

## Verification

After installation, verify everything works:

```bash
# Test import
python -c "import fastapi; import argon2; import sqlalchemy; print('✅ All imports successful')"

# Check versions
pip list | grep -E "fastapi|pydantic|argon2|sqlalchemy"

# Run the app (if testing locally)
uvicorn main:app --reload
```

## Docker Installation (Recommended)

For the easiest setup with zero dependency issues:

```bash
# 1. Install Docker Desktop
# Download from: https://www.docker.com/products/docker-desktop

# 2. Build application
docker-compose build --no-cache

# 3. Start services
docker-compose up -d

# 4. Verify
docker-compose ps
curl http://localhost:8000/health
```

Docker handles:
✅ All Python dependencies
✅ System dependencies
✅ Database setup
✅ Network configuration
✅ No version conflicts

## Python Version Requirements

**Minimum:** Python 3.11
**Recommended:** Python 3.11 or 3.12
**Not supported:** Python 3.9 or below

Check your version:
```bash
python --version
# Should show: Python 3.11.x or 3.12.x
```

## Virtual Environment (Recommended for Local Development)

Always use a virtual environment:

```bash
# Create
python -m venv venv

# Activate
source venv/bin/activate  # Linux/macOS
# OR
venv\Scripts\activate  # Windows

# Install
pip install -r requirements.txt

# Deactivate when done
deactivate
```

## Testing Installation

After installing dependencies, run tests:

```bash
# Unit tests
pytest tests/

# Security tests
./security-test.sh

# Import tests
python -c "
import fastapi
import argon2
import sqlalchemy
import bleach
import slowapi
print('✅ All critical imports successful')
"
```

## What's Included

### Core Security (Always Installed)

✅ **Argon2id** - Quantum-resistant password hashing
✅ **Bleach** - HTML sanitization (XSS prevention)
✅ **SlowAPI** - Rate limiting
✅ **email-validator** - Email validation
✅ **python-jose** - JWT tokens
✅ **passlib** - Password utilities

### What's Optional

⚠️ **Security audit tools** - Development only
⚠️ **PQC libraries** - Future use when needed
⚠️ **Testing tools** - Development only

## Need Help?

If you still encounter issues:

1. **Check Python version:** `python --version` (need 3.11+)
2. **Use Docker:** Easiest solution, handles everything
3. **Create fresh venv:** Start with clean environment
4. **Check logs:** Look for specific error messages
5. **Use minimal requirements:** Already in `requirements.txt`

## Summary

✅ **Recommended:** Use Docker (handles everything)
✅ **Alternative:** Use `requirements.txt` (minimal, tested)
✅ **Advanced:** Install optional tools separately as needed

The minimal `requirements.txt` includes **all security features** including:
- Argon2id (quantum-resistant)
- Input validation
- Rate limiting
- Audit logging
- All OWASP protections
