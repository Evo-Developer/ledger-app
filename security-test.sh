#!/bin/bash

# Security Testing and Validation Script
# Runs various security checks on the Ledger application

echo "🔒 Ledger App - Security Testing Suite"
echo "======================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
PASSED=0
FAILED=0
WARNINGS=0

# Function to print test result
print_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓ PASS${NC}: $2"
        ((PASSED++))
    else
        echo -e "${RED}✗ FAIL${NC}: $2"
        ((FAILED++))
    fi
}

print_warning() {
    echo -e "${YELLOW}⚠ WARNING${NC}: $1"
    ((WARNINGS++))
}

# Check if backend is running
echo "📋 Checking Backend Status..."
if docker-compose ps | grep -q "ledger_backend.*Up"; then
    print_result 0 "Backend container is running"
else
    print_result 1 "Backend container is not running"
    echo "Please start the application with: docker-compose up -d"
    exit 1
fi

echo ""

# Test 1: Check SECRET_KEY is set and strong
echo "🔑 Testing SECRET_KEY Configuration..."
SECRET_KEY=$(docker-compose exec -T backend python -c "import os; print(os.getenv('SECRET_KEY', 'NOT_SET'))" 2>/dev/null)

if [ "$SECRET_KEY" = "NOT_SET" ] || [ -z "$SECRET_KEY" ]; then
    print_result 1 "SECRET_KEY not set in environment"
elif [ "$SECRET_KEY" = "your-secret-key-change-this-in-production" ]; then
    print_result 1 "SECRET_KEY using default value - CHANGE THIS!"
elif [ ${#SECRET_KEY} -lt 32 ]; then
    print_result 1 "SECRET_KEY too short (min 32 characters)"
else
    print_result 0 "SECRET_KEY properly configured"
fi

echo ""

# Test 2: Check Security Headers
echo "🛡️  Testing Security Headers..."

# Test X-Frame-Options
HEADER=$(curl -s -I http://localhost:8000/health 2>/dev/null | grep -i "x-frame-options")
if echo "$HEADER" | grep -qi "DENY"; then
    print_result 0 "X-Frame-Options header present"
else
    print_result 1 "X-Frame-Options header missing"
fi

# Test X-Content-Type-Options
HEADER=$(curl -s -I http://localhost:8000/health 2>/dev/null | grep -i "x-content-type-options")
if echo "$HEADER" | grep -qi "nosniff"; then
    print_result 0 "X-Content-Type-Options header present"
else
    print_result 1 "X-Content-Type-Options header missing"
fi

# Test CSP
HEADER=$(curl -s -I http://localhost:8000/health 2>/dev/null | grep -i "content-security-policy")
if [ ! -z "$HEADER" ]; then
    print_result 0 "Content-Security-Policy header present"
else
    print_result 1 "Content-Security-Policy header missing"
fi

echo ""

# Test 3: SQL Injection Protection
echo "💉 Testing SQL Injection Protection..."

# Test with SQL injection payload
RESPONSE=$(curl -s -X POST http://localhost:8000/api/auth/login \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=' OR '1'='1&password=test" 2>/dev/null)

if echo "$RESPONSE" | grep -qi "error\|unauthorized\|incorrect"; then
    print_result 0 "SQL injection payload rejected"
else
    print_result 1 "SQL injection protection may be weak"
fi

echo ""

# Test 4: XSS Protection
echo "🚫 Testing XSS Protection..."

# This would need a proper test endpoint
print_warning "XSS testing requires manual verification"

echo ""

# Test 5: Rate Limiting
echo "⏱️  Testing Rate Limiting..."

# Make multiple rapid login attempts
echo "   Making 6 rapid login attempts..."
RATE_LIMITED=0

for i in {1..6}; do
    RESPONSE=$(curl -s -X POST http://localhost:8000/api/auth/login \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "username=testuser&password=wrongpass" 2>/dev/null)
    
    if echo "$RESPONSE" | grep -qi "too many"; then
        RATE_LIMITED=1
        break
    fi
    sleep 0.5
done

if [ $RATE_LIMITED -eq 1 ]; then
    print_result 0 "Rate limiting is working"
else
    print_warning "Rate limiting may not be properly configured"
fi

echo ""

# Test 6: Password Complexity Requirements
echo "🔐 Testing Password Requirements..."

# Try to register with weak password
RESPONSE=$(curl -s -X POST http://localhost:8000/api/auth/register \
    -H "Content-Type: application/json" \
    -d '{
        "email": "test@test.com",
        "username": "testuser123",
        "password": "weak",
        "full_name": "Test User"
    }' 2>/dev/null)

if echo "$RESPONSE" | grep -qi "error\|invalid\|weak\|short"; then
    print_result 0 "Weak password rejected"
else
    print_warning "Password requirements may need strengthening"
fi

echo ""

# Test 7: HTTPS Redirect (if applicable)
echo "🔒 Testing HTTPS Configuration..."
print_warning "HTTPS testing requires manual verification in production"

echo ""

# Test 8: Database Connection Security
echo "💾 Testing Database Security..."

# Check if database requires authentication
DB_TEST=$(docker-compose exec -T db mysql -u root -prootpassword -e "SELECT 1" 2>&1)
if echo "$DB_TEST" | grep -qi "error\|denied"; then
    print_warning "Database connection test inconclusive"
else
    print_warning "Verify database uses strong credentials"
fi

echo ""

# Test 9: Check for exposed secrets in code
echo "🔍 Checking for Exposed Secrets..."

if command -v trufflehog &> /dev/null; then
    trufflehog --regex --entropy=False backend/ > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        print_result 0 "No exposed secrets found"
    else
        print_result 1 "Potential secrets found in code"
    fi
else
    print_warning "trufflehog not installed - skipping secret scanning"
fi

echo ""

# Test 10: Dependency Vulnerabilities
echo "📦 Checking for Vulnerable Dependencies..."

if docker-compose exec -T backend safety check > /dev/null 2>&1; then
    print_result 0 "No known vulnerabilities in dependencies"
else
    print_warning "Some dependencies may have known vulnerabilities"
fi

echo ""

# Test 11: Input Validation
echo "✅ Testing Input Validation..."

# Test with overly long input
LONG_STRING=$(python3 -c "print('A' * 10000)")
RESPONSE=$(curl -s -X POST http://localhost:8000/api/auth/register \
    -H "Content-Type: application/json" \
    -d "{
        \"email\": \"$LONG_STRING@test.com\",
        \"username\": \"test\",
        \"password\": \"Test123!\",
        \"full_name\": \"Test\"
    }" 2>/dev/null)

if echo "$RESPONSE" | grep -qi "error\|invalid\|too long"; then
    print_result 0 "Input length validation working"
else
    print_warning "Input length validation may need improvement"
fi

echo ""

# Test 12: CORS Configuration
echo "🌐 Testing CORS Configuration..."

# Test CORS headers
CORS_HEADER=$(curl -s -I -H "Origin: http://evil.com" http://localhost:8000/health 2>/dev/null | grep -i "access-control-allow-origin")

if echo "$CORS_HEADER" | grep -qi "\*"; then
    print_warning "CORS allows all origins - restrict in production"
elif [ ! -z "$CORS_HEADER" ]; then
    print_result 0 "CORS configured (verify allowed origins)"
else
    print_result 0 "CORS not allowing external origins"
fi

echo ""

# Summary
echo "======================================="
echo "📊 Test Summary"
echo "======================================="
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo -e "${YELLOW}Warnings: $WARNINGS${NC}"
echo ""

if [ $FAILED -gt 0 ]; then
    echo -e "${RED}⚠️  SECURITY ISSUES DETECTED${NC}"
    echo "Please review and fix failed tests before production deployment"
    exit 1
elif [ $WARNINGS -gt 0 ]; then
    echo -e "${YELLOW}⚠️  WARNINGS PRESENT${NC}"
    echo "Review warnings and ensure proper configuration"
    exit 0
else
    echo -e "${GREEN}✅ ALL TESTS PASSED${NC}"
    echo "Security configuration looks good!"
    exit 0
fi
