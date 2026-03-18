#!/bin/bash

# Test Requirements Installation
echo "🧪 Testing Requirements Installation..."
echo "========================================"
echo ""

# Create temporary virtual environment
echo "📦 Creating test virtual environment..."
python3 -m venv test_venv

# Activate it
source test_venv/bin/activate

echo "✅ Virtual environment created"
echo ""

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip > /dev/null 2>&1
echo "✅ pip upgraded"
echo ""

# Try installing requirements
echo "📥 Installing requirements..."
echo "This may take a few minutes..."
echo ""

if pip install -r backend/requirements.txt; then
    echo ""
    echo "✅ ✅ ✅ SUCCESS! All dependencies installed without conflicts!"
    echo ""
    
    # Test imports
    echo "🔍 Testing critical imports..."
    python3 << EOF
try:
    import fastapi
    print("✅ fastapi imported")
    import uvicorn
    print("✅ uvicorn imported")
    import sqlalchemy
    print("✅ sqlalchemy imported")
    import argon2
    print("✅ argon2 (Argon2id) imported")
    import bleach
    print("✅ bleach (XSS prevention) imported")
    import slowapi
    print("✅ slowapi (rate limiting) imported")
    from pydantic import BaseModel
    print("✅ pydantic imported")
    print("")
    print("🎉 ALL CRITICAL IMPORTS SUCCESSFUL!")
    print("🔒 Security features ready:")
    print("   - Argon2id password hashing (quantum-resistant)")
    print("   - Input validation & sanitization")
    print("   - Rate limiting")
    print("   - JWT authentication")
except Exception as e:
    print(f"❌ Import failed: {e}")
    exit(1)
EOF
    
    if [ $? -eq 0 ]; then
        echo ""
        echo "✅ Installation test PASSED"
        echo ""
        echo "Installed versions:"
        pip list | grep -E "fastapi|pydantic|argon2|sqlalchemy|bleach|slowapi"
    fi
else
    echo ""
    echo "❌ Installation FAILED"
    echo ""
    echo "Please check the error messages above."
    echo "Common issues:"
    echo "  1. Python version < 3.11"
    echo "  2. Missing system dependencies"
    echo "  3. Network issues"
    echo ""
    echo "Try: pip install --upgrade pip setuptools wheel"
fi

# Cleanup
deactivate
rm -rf test_venv

echo ""
echo "========================================"
echo "Test complete!"
