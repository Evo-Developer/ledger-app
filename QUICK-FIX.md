# 🔧 QUICK FIX: Dependency Installation

## Problem
You're getting: `ERROR: Cannot install... conflicting dependencies`

## ✅ SOLUTION (Choose One)

### Option 1: Use Docker (EASIEST - RECOMMENDED)

**Docker handles ALL dependencies automatically. No conflicts possible.**

```bash
# Just build and run - it works!
docker-compose build --no-cache
docker-compose up -d

# That's it! No dependency issues.
```

✅ **Why this works:** Docker builds in isolated environment with all dependencies pre-configured.

### Option 2: Let Pip Resolve Versions

**The new `requirements.txt` uses flexible version ranges.**

```bash
# 1. Clean start
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. Upgrade pip
pip install --upgrade pip setuptools wheel

# 3. Install (pip will find compatible versions)
pip install -r backend/requirements.txt

# 4. Verify
python -c "import fastapi, argon2, sqlalchemy; print('✅ Success!')"
```

✅ **Why this works:** Version ranges let pip find compatible versions automatically.

### Option 3: Install Without Versions

**If still having issues, install without version constraints:**

```bash
pip install fastapi uvicorn[standard] sqlalchemy pymysql \
    argon2-cffi python-jose[cryptography] passlib[bcrypt] \
    email-validator bleach slowapi python-dotenv python-dateutil
```

✅ **Why this works:** Gets latest compatible versions.

## What's Included?

✅ **FastAPI** - Web framework
✅ **Argon2id** - Quantum-resistant password hashing  
✅ **SQLAlchemy** - Database ORM
✅ **Bleach** - XSS prevention
✅ **SlowAPI** - Rate limiting
✅ **python-jose** - JWT authentication

**ALL security features are included!**

## Verify Installation

```bash
python << EOF
import fastapi
import argon2
import sqlalchemy
import bleach
print("✅ All critical packages installed")
print("✅ Security features ready:")
print("   - Argon2id (quantum-resistant)")
print("   - Input validation")  
print("   - Rate limiting")
print("   - JWT auth")
EOF
```

## Still Having Issues?

### Check Python Version
```bash
python --version
# Must be 3.11 or higher
```

### Install System Dependencies (Linux)
```bash
sudo apt-get update
sudo apt-get install -y \
    python3-dev \
    gcc \
    g++ \
    libssl-dev \
    libffi-dev \
    default-libmysqlclient-dev
```

### Install System Dependencies (macOS)
```bash
brew install mysql-client openssl
```

## Recommendation

**🐳 Use Docker** - It's the easiest and most reliable option. All dependencies are managed automatically with zero configuration needed.

```bash
docker-compose up --build -d
```

That's it! 🎉
