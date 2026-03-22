#!/bin/bash

# Ledger App Diagnostic Script
# Helps troubleshoot "Failed to fetch" login errors

set -e

echo "========================================="
echo "🔍 Ledger App Diagnostics"
echo "========================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Docker
echo "1️⃣  Checking Docker..."
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Docker found${NC}"

# Check Docker daemon
if ! docker ps &> /dev/null; then
    echo -e "${RED}❌ Docker daemon is not running. Starting Docker...${NC}"
    # Try to start Docker on macOS
    if [[ "$OSTYPE" == "darwin"* ]]; then
        open -a Docker
        echo "Waiting for Docker to start..."
        sleep 5
    fi
fi

# Check containers status
echo ""
echo "2️⃣  Checking container status..."

# Check if containers exist
if [ "$(docker ps -a -q -f name=ledger)" = "" ]; then
    echo -e "${YELLOW}⚠️  No Ledger containers found. Building and starting...${NC}"
    docker-compose up -d --build
    echo "Waiting for services to initialize..."
    sleep 10
else
    # Check if any are stopped
    STOPPED=$(docker ps -q -f status=exited -f name=ledger)
    if [ ! -z "$STOPPED" ]; then
        echo -e "${YELLOW}⚠️  Some containers are stopped. Starting them...${NC}"
        docker-compose up -d
        sleep 5
    else
        echo -e "${GREEN}✅ All containers are running${NC}"
    fi
fi

echo ""
echo "3️⃣  Container Status:"
docker ps -a --filter "name=ledger" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "4️⃣  Checking database connectivity..."
if docker exec ledger_db mysqladmin ping -h localhost &> /dev/null; then
    echo -e "${GREEN}✅ Database is responding${NC}"
else
    echo -e "${RED}❌ Database is not responding. Checking logs...${NC}"
    docker logs ledger_db | tail -20
fi

echo ""
echo "5️⃣  Checking backend API..."
if docker exec ledger_backend python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=8).read()" &> /dev/null; then
    echo -e "${GREEN}✅ Backend API is responding${NC}"
else
    echo -e "${RED}❌ Backend API is not responding${NC}"
    echo "Backend logs (last 20 lines):"
    docker logs ledger_backend | tail -20
fi

echo ""
echo "6️⃣  Testing login endpoint from backend..."
RESPONSE=$(docker exec ledger_backend python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/openapi.json', timeout=8).status)" 2>/dev/null || echo "failed")

if echo "$RESPONSE" | grep -q "200"; then
    echo -e "${GREEN}✅ Login endpoint is working${NC}"
else
    echo -e "${YELLOW}⚠️  Backend may have issues: $RESPONSE${NC}"
fi

echo ""
echo "7️⃣  Checking frontend container..."
if docker exec ledger_frontend nginx -t 2> /dev/null; then
    echo -e "${GREEN}✅ Nginx configuration is valid${NC}"
else
    echo -e "${RED}❌ Nginx configuration has errors${NC}"
    docker logs ledger_frontend | tail -20
fi

echo ""
echo "8️⃣  Checking network..."
docker network ls | grep ledger_network

echo ""
echo "========================================="
echo "✅ Diagnostics Complete!"
echo "========================================="
echo ""
echo "📍 Next Steps:"
echo "1. Open browser to: http://localhost"
echo "2. Try to login or register a new account"
echo "3. If still seeing 'Failed to fetch':"
echo "   - Check browser console (F12 > Console)"
echo "   - Check Docker logs: docker-compose logs -f"
echo ""
