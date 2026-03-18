#!/bin/bash

# Ledger App Setup Script

echo "🚀 Starting Ledger Finance App..."
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker Desktop first."
    exit 1
fi

echo "✅ Docker is running"
echo ""

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose not found. Please install Docker Compose."
    exit 1
fi

echo "✅ Docker Compose is available"
echo ""

# Create backend .env if it doesn't exist
if [ ! -f backend/.env ]; then
    echo "📝 Creating backend/.env from template..."
    cp backend/.env.example backend/.env
    
    # Generate a random secret key
    SECRET_KEY=$(openssl rand -hex 32)
    
    # Update the .env file with the generated key
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s/your-secret-key-change-this-in-production-use-openssl-rand-hex-32/$SECRET_KEY/" backend/.env
    else
        # Linux
        sed -i "s/your-secret-key-change-this-in-production-use-openssl-rand-hex-32/$SECRET_KEY/" backend/.env
    fi
    
    echo "✅ Created backend/.env with secure secret key"
else
    echo "✅ backend/.env already exists"
fi

echo ""
echo "🏗️  Building and starting containers..."
echo "This may take a few minutes on first run..."
echo ""

# Build and start containers
docker-compose up --build -d

# Wait for services to be healthy
echo ""
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check if services are running
if docker-compose ps | grep -q "Up"; then
    echo ""
    echo "✅ All services are running!"
    echo ""
    echo "📱 Access your app at:"
    echo "   Frontend: http://localhost"
    echo "   API Docs: http://localhost:8000/docs"
    echo "   Health:   http://localhost:8000/health"
    echo ""
    echo "📊 View logs with:"
    echo "   docker-compose logs -f"
    echo ""
    echo "🛑 Stop the app with:"
    echo "   docker-compose down"
    echo ""
    echo "🎉 Happy tracking!"
else
    echo ""
    echo "❌ Some services failed to start. Check logs:"
    echo "   docker-compose logs"
fi
