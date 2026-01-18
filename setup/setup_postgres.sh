#!/bin/bash
# Automated PostgreSQL Setup with Docker

set -e

echo "======================================"
echo "PostgreSQL Setup with Docker"
echo "======================================"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "[ERROR] Docker is not running!"
    echo "Please start Docker and try again."
    exit 1
fi

echo "[1/5] Docker is running..."
echo ""

# Stop and remove existing container if exists
echo "[2/5] Cleaning up old containers..."
docker-compose down > /dev/null 2>&1 || true
docker rm -f trustpilot_postgres > /dev/null 2>&1 || true
echo "Done."
echo ""

# Start PostgreSQL container
echo "[3/5] Starting PostgreSQL container..."
docker-compose up -d
echo "Done."
echo ""

# Wait for PostgreSQL to be ready
echo "[4/5] Waiting for PostgreSQL to be ready..."
sleep 5

for i in {1..30}; do
    if docker exec trustpilot_postgres pg_isready -U trustpilot_user -d trustpilot_db > /dev/null 2>&1; then
        echo "PostgreSQL is ready!"
        break
    fi
    echo "Still waiting... ($i/30)"
    sleep 2
done
echo ""

# Configure .env
echo "[5/5] Configuring .env file..."
cat > .env << EOF
DATABASE_URL=postgresql://trustpilot_user:trustpilot_pass@localhost:5432/trustpilot_db
BRANDS=ketogo.app
MAX_PAGES=10
JWT_ACCESS_TOKEN=
EOF
echo "Done."
echo ""

echo "======================================"
echo "Setup Complete!"
echo "======================================"
echo ""
echo "Database: trustpilot_db"
echo "User: trustpilot_user"
echo "Password: trustpilot_pass"
echo "Port: 5432" 
echo ""
echo "Running tests..."
echo ""

python3 test_db.py

echo ""
echo "======================================"
echo "Next Steps:"
echo "======================================"
echo "  python3 onboarding.py trustpilot.com"
echo "  python3 daily_scrape.py"
echo ""
echo "To stop PostgreSQL:"
echo "  docker-compose down"
echo ""
