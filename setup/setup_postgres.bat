@echo off
REM Automated PostgreSQL Setup with Docker for Windows

echo ======================================
echo PostgreSQL Setup with Docker
echo ======================================
echo.

REM Check if Docker is running
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker is not running!
    echo Please start Docker Desktop and try again.
    pause
    exit /b 1
)

echo [1/5] Docker is running...
echo.

REM Stop and remove existing container if exists
echo [2/5] Cleaning up old containers...
docker-compose down >nul 2>&1
docker rm -f trustpilot_postgres >nul 2>&1
echo Done.
echo.

REM Start PostgreSQL container
echo [3/5] Starting PostgreSQL container...
docker-compose up -d
if %errorlevel% neq 0 (
    echo [ERROR] Failed to start PostgreSQL container
    pause
    exit /b 1
)
echo Done.
echo.

REM Wait for PostgreSQL to be ready
echo [4/5] Waiting for PostgreSQL to be ready...
timeout /t 10 /nobreak >nul

REM Test connection
:retry
docker exec trustpilot_postgres pg_isready -U trustpilot_user -d trustpilot_db >nul 2>&1
if %errorlevel% neq 0 (
    echo Still waiting...
    timeout /t 2 /nobreak >nul
    goto retry
)
echo PostgreSQL is ready!
echo.

REM Configure .env
echo [5/5] Configuring .env file...
echo DATABASE_URL=postgresql://trustpilot_user:trustpilot_pass@localhost:5432/trustpilot_db > .env
echo BRANDS=ketogo.app >> .env
echo MAX_PAGES=10 >> .env
echo JWT_ACCESS_TOKEN= >> .env
echo Done.
echo. 

echo ======================================
echo Setup Complete!
echo ======================================
echo.
echo Database: trustpilot_db
echo User: trustpilot_user
echo Password: trustpilot_pass
echo Port: 5432
echo.
echo Running tests...
echo.

python test_db.py

echo.
echo ======================================
echo Next Steps:
echo ======================================
echo   python onboarding.py trustpilot.com
echo   python daily_scrape.py
echo.
echo To stop PostgreSQL:
echo   docker-compose down
echo.
pause
