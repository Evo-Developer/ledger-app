@echo off
echo.
echo ====================================
echo  Ledger Finance App - Setup
echo ====================================
echo.

REM Check if Docker is running
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker is not running. Please start Docker Desktop first.
    pause
    exit /b 1
)

echo [OK] Docker is running
echo.

REM Create .env if it doesn't exist
if not exist backend\.env (
    echo Creating backend\.env from template...
    copy backend\.env.example backend\.env
    echo [OK] Created backend\.env
) else (
    echo [OK] backend\.env already exists
)

echo.
echo Building and starting containers...
echo This may take a few minutes on first run...
echo.

docker-compose up --build -d

echo.
echo Waiting for services to be ready...
timeout /t 10 /nobreak >nul

echo.
echo ====================================
echo  Ledger App is Running!
echo ====================================
echo.
echo  Frontend: http://localhost
echo  API Docs: http://localhost:8000/docs
echo  Health:   http://localhost:8000/health
echo.
echo View logs: docker-compose logs -f
echo Stop app:  docker-compose down
echo.
echo Happy tracking!
echo.
pause
