#!/bin/bash
# Quick Start Script for Trustpilot Scraper

set -e

echo "======================================"
echo "Trustpilot Scraper - Quick Start"
echo "======================================"
echo ""

# Check Python version
echo "[1/6] Checking Python version..."
python3 --version || { echo "Error: Python 3 not found"; exit 1; }
echo "✓ Python 3 available"
echo ""

# Install dependencies
echo "[2/6] Installing dependencies..."
pip install -r requirements.txt || { echo "Error: Failed to install dependencies"; exit 1; }
echo "✓ Dependencies installed"
echo ""

# Database selection
echo "[3/6] Select database:"
echo "  1) SQLite (quick local testing)"
echo "  2) PostgreSQL (via Docker - recommended)"
echo "  3) PostgreSQL (existing instance)"
read -p "Choice (1-3): " db_choice

case $db_choice in
    1)
        echo "Using SQLite..."
        cp .env.example .env
        sed -i 's|^DATABASE_URL=.*|DATABASE_URL=sqlite:///./local.db|' .env
        ;;
    2)
        echo "Starting PostgreSQL with Docker..."
        if ! command -v docker &> /dev/null; then
            echo "Error: Docker not found. Please install Docker first."
            exit 1
        fi
        
        docker-compose up -d
        echo "Waiting for PostgreSQL to be ready..."
        sleep 5
        
        cp .env.postgres .env
        ;;
    3)
        echo "Using existing PostgreSQL..."
        cp .env.postgres .env
        echo ""
        read -p "Database host [localhost]: " db_host
        db_host=${db_host:-localhost}
        read -p "Database port [5432]: " db_port
        db_port=${db_port:-5432}
        read -p "Database name [trustpilot_db]: " db_name
        db_name=${db_name:-trustpilot_db}
        read -p "Database user [trustpilot_user]: " db_user
        db_user=${db_user:-trustpilot_user}
        read -sp "Database password: " db_pass
        echo ""
        
        sed -i "s|^DATABASE_URL=.*|DATABASE_URL=postgresql://${db_user}:${db_pass}@${db_host}:${db_port}/${db_name}|" .env
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

echo "✓ Database configured"
echo ""

# Configure brands
echo "[4/6] Configure brands to scrape..."
read -p "Enter brand domains (comma-separated) [trustpilot.com]: " brands
brands=${brands:-trustpilot.com}
sed -i "s|^BRANDS=.*|BRANDS=$brands|" .env
echo "✓ Brands configured: $brands"
echo ""

# Run tests
echo "[5/6] Running database tests..."
python3 test_db.py || { echo "Error: Tests failed"; exit 1; }
echo ""

# Show next steps
echo "[6/6] Setup complete!"
echo ""
echo "======================================"
echo "Next Steps:"
echo "======================================"
echo ""
echo "1. Onboard a brand (full historical scrape):"
echo "   python3 onboarding.py trustpilot.com"
echo ""
echo "2. Run daily scrape (updates existing brands):"
echo "   python3 daily_scrape.py"
echo ""
echo "3. View database:"
if [ "$db_choice" = "1" ]; then
    echo "   sqlite3 local.db"
    echo "   sqlite> SELECT * FROM brands;"
else
    echo "   psql postgresql://trustpilot_user:trustpilot_pass@localhost:5432/trustpilot_db"
    echo "   trustpilot_db=> SELECT * FROM brands;"
fi
echo ""
echo "4. Stop PostgreSQL (if using Docker):"
echo "   docker-compose down"
echo ""
echo "======================================"
echo "Happy scraping! 🚀"
echo "======================================"
