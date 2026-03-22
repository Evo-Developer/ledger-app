#!/bin/bash

# Ledger App Quick Fix Script
# Resolves common "Failed to fetch" login errors

set -e

echo "🔧 Ledger App - Quick Fix"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Step 1: Ensure Docker is ready
echo "1️⃣  Ensuring Docker is running..."
if ! docker ps &> /dev/null; then
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "Starting Docker Desktop..."
        open -a Docker
        # Wait for Docker to be ready
        for i in {1..30}; do
            if docker ps &> /dev/null; then
                break
            fi
            echo -n "."
            sleep 1
        done
        echo ""
    else
        echo "Please start Docker and try again."
        exit 1
    fi
fi
echo -e "${GREEN}✅ Docker is ready${NC}"
echo ""

# Step 2: Stop existing containers  
echo "2️⃣  Stopping existing containers..."
docker-compose down 2>/dev/null || true
sleep 2
echo -e "${GREEN}✅ Stopped${NC}"
echo ""

# Step 3: Rebuild and start fresh
echo "3️⃣  Building and starting services..."
docker-compose up -d --build
echo "Waiting for services to be ready..."
sleep 15
echo -e "${GREEN}✅ Services started${NC}"
echo ""

# Step 4: Verify all containers are running
echo "4️⃣  Verifying services..."
FAILED=0

echo "Checking database..."
if ! docker exec ledger_db mysqladmin ping -h localhost -u root -prootpassword &> /dev/null; then
    echo -e "${RED}❌ Database failed to start${NC}"
    FAILED=1
else
    echo -e "${GREEN}✅ Database running${NC}"
fi

echo "Checking backend API..."
BACKEND_READY=0
for i in {1..30}; do
    if docker exec ledger_backend python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=8).read()" &> /dev/null; then
        echo -e "${GREEN}✅ Backend running${NC}"
        BACKEND_READY=1
        break
    fi
    echo -n "."
    sleep 1
done

if [ $BACKEND_READY -eq 0 ]; then
    echo -e "${RED}❌ Backend failed to start${NC}"
    echo "Backend logs:"
    docker logs ledger_backend | tail -30
    FAILED=1
fi

echo "Checking frontend..."
if docker exec ledger_frontend nginx -t &> /dev/null; then
    echo -e "${GREEN}✅ Frontend running${NC}"
else
    echo -e "${RED}❌ Frontend failed to start${NC}"
    FAILED=1
fi

if [ $FAILED -eq 0 ]; then
    echo ""
    echo "========================================="
    echo -e "${GREEN}✅ All services are running!${NC}"
    echo "========================================="
    echo ""
    echo "🌐 Open your browser to: http://localhost"
    echo ""
    echo "📝 First Time Setup:"
    echo "   1. Click 'Register' tab"
    echo "   2. Create a test account"
    echo "   3. Login with your credentials"
    echo ""
else
    echo ""
    echo -e "${RED}❌ Some services failed to start${NC}"
    echo ""
    echo "For detailed logs, run:"
    echo "  docker-compose logs -f"
    echo ""
    exit 1
fi
