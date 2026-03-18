#!/bin/bash

echo "🔍 Ledger App - Setup Verification"
echo "===================================="
echo ""

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Error: docker-compose.yml not found"
    echo "Please run this script from the ledger-app directory"
    exit 1
fi

echo "✅ Found docker-compose.yml"
echo ""

# Check frontend files
echo "📁 Checking frontend files..."
FRONTEND_FILES=("frontend/index.html" "frontend/app.html" "frontend/nginx.conf" "frontend/Dockerfile")

for file in "${FRONTEND_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ Missing: $file"
    fi
done

echo ""

# Check backend files
echo "📁 Checking backend files..."
BACKEND_FILES=("backend/main.py" "backend/models.py" "backend/Dockerfile" "backend/requirements.txt")

for file in "${BACKEND_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ Missing: $file"
    fi
done

echo ""

# Check if containers are running
echo "🐳 Checking Docker containers..."
if docker-compose ps | grep -q "Up"; then
    echo "  ✅ Containers are running"
    docker-compose ps
else
    echo "  ⚠️  Containers may not be running properly"
    docker-compose ps
fi

echo ""
echo "🔧 Diagnostic Commands:"
echo ""
echo "1. View frontend logs:"
echo "   docker-compose logs frontend"
echo ""
echo "2. View backend logs:"
echo "   docker-compose logs backend"
echo ""
echo "3. Check if nginx is serving files:"
echo "   docker exec ledger_frontend ls -la /usr/share/nginx/html/"
echo ""
echo "4. Test nginx config:"
echo "   docker exec ledger_frontend nginx -t"
echo ""
echo "5. Rebuild and restart:"
echo "   docker-compose down"
echo "   docker-compose up --build -d"
echo ""
