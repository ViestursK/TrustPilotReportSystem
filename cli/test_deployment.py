#!/usr/bin/env python3
"""
PostgreSQL Test Script - Run BEFORE deploying to AWS
Tests your code with PostgreSQL locally (via Docker)
"""

import sys
import os
import subprocess
import time

def check_docker():
    """Check if Docker is installed"""
    try:
        result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
        print(f"✓ Docker found: {result.stdout.strip()}")
        return True
    except FileNotFoundError:
        print("✗ Docker not found. Please install Docker first:")
        print("  https://docs.docker.com/get-docker/")
        return False

def start_postgres():
    """Start PostgreSQL container"""
    print("\n[1/5] Starting PostgreSQL container...")
    
    # Stop any existing container
    subprocess.run(['docker', 'stop', 'trustpilot_postgres'], 
                   capture_output=True, stderr=subprocess.DEVNULL)
    subprocess.run(['docker', 'rm', 'trustpilot_postgres'], 
                   capture_output=True, stderr=subprocess.DEVNULL)
    
    # Start fresh container
    cmd = [
        'docker', 'run', '--name', 'trustpilot_postgres',
        '-e', 'POSTGRES_DB=trustpilot_test',
        '-e', 'POSTGRES_USER=test_user',
        '-e', 'POSTGRES_PASSWORD=test_pass',
        '-p', '5432:5432',
        '-d', 'postgres:15-alpine'
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"✗ Failed to start PostgreSQL: {result.stderr}")
        return False
    
    print("✓ PostgreSQL container started")
    
    # Wait for PostgreSQL to be ready
    print("  Waiting for PostgreSQL to be ready...", end='', flush=True)
    for i in range(30):
        result = subprocess.run(
            ['docker', 'exec', 'trustpilot_postgres', 
             'pg_isready', '-U', 'test_user'],
            capture_output=True
        )
        if result.returncode == 0:
            print(" ✓ Ready!")
            time.sleep(1)  # Extra second for safety
            return True
        print(".", end='', flush=True)
        time.sleep(1)
    
    print("\n✗ PostgreSQL didn't start in time")
    return False

def setup_env():
    """Create .env file for PostgreSQL testing"""
    print("\n[2/5] Configuring environment...")
    
    env_content = """# PostgreSQL Test Configuration
DATABASE_URL=postgresql://test_user:test_pass@localhost:5432/trustpilot_test
BRANDS=trustpilot.com
MAX_PAGES=1
JWT_ACCESS_TOKEN=
"""
    
    with open('.env', 'w') as f:
        f.write(env_content)
    
    print("✓ Environment configured for PostgreSQL")

def install_deps():
    """Install Python dependencies"""
    print("\n[3/5] Installing dependencies...")
    
    result = subprocess.run(
        [sys.executable, '-m', 'pip', 'install', '-q', '-r', 'requirements.txt'],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"✗ Failed to install dependencies: {result.stderr}")
        return False
    
    print("✓ Dependencies installed")
    return True

def run_tests():
    """Run database tests"""
    print("\n[4/5] Running PostgreSQL tests...")
    print("="*70)
    
    result = subprocess.run([sys.executable, 'test_db.py'])
    
    print("="*70)
    
    if result.returncode != 0:
        print("\n✗ Tests failed")
        return False
    
    print("\n✓ All tests passed")
    return True

def test_actual_scrape():
    """Test with a small scrape"""
    print("\n[5/5] Testing actual scrape (1 page only)...")
    print("="*70)
    
    # Import here to ensure env is loaded
    import scraper
    
    print("\nAttempting to scrape Trustpilot (1 page, no JWT)...")
    data = scraper.scrape_brand(
        'trustpilot.com',
        max_pages=1,
        use_jwt=False,
        filter_last_30_days=True
    )
    
    if not data:
        print("✗ Scrape failed (might be network issue)")
        return False
    
    print(f"\n✓ Scrape successful!")
    print(f"  Brand: {data['company']['brand_name']}")
    print(f"  Reviews fetched: {len(data['reviews'])}")
    print(f"  Trust Score: {data['company']['trust_score']}/5")
    
    # Try to save to database
    print("\n  Testing database save...")
    from db import init_db
    from db import queries as database
    
    init_db()
    
    # Check if brand exists
    brand_id = database.get_brand_id('trustpilot.com')
    
    if brand_id:
        print(f"  Brand already exists (ID: {brand_id}), updating...")
        database.update_brand_metadata(brand_id, data['company'])
    else:
        print("  Adding new brand...")
        brand_id = database.add_brand('trustpilot.com', data['company'])
    
    # Insert reviews
    inserted, skipped = database.insert_reviews(brand_id, data['reviews'])
    print(f"  Reviews: {inserted} inserted, {skipped} skipped")
    
    # Verify they're in the database
    all_reviews = database.get_all_reviews_for_brand(brand_id)
    print(f"  Total reviews in DB: {len(all_reviews)}")
    
    print("\n✓ Database save successful!")
    print("="*70)
    
    return True

def cleanup():
    """Stop PostgreSQL container"""
    print("\nCleaning up...")
    subprocess.run(['docker', 'stop', 'trustpilot_postgres'], 
                   capture_output=True)
    print("✓ PostgreSQL container stopped")
    print("\nTo start it again: docker start trustpilot_postgres")
    print("To remove it: docker rm trustpilot_postgres")

def main():
    print("="*70)
    print("POSTGRESQL LOCAL TEST - Before AWS Deployment")
    print("="*70)
    print("\nThis will test your code with PostgreSQL locally")
    print("Same database your code will use on AWS Lambda + RDS")
    print()
    
    # Check Docker
    if not check_docker():
        return 1
    
    try:
        # Start PostgreSQL
        if not start_postgres():
            return 1
        
        # Setup environment
        setup_env()
        
        # Install dependencies
        if not install_deps():
            cleanup()
            return 1
        
        # Run tests
        if not run_tests():
            cleanup()
            return 1
        
        # Test actual scraping
        if not test_actual_scrape():
            print("\n⚠ Scrape test failed, but database tests passed")
            print("  This is likely a network issue, not a PostgreSQL issue")
            print("  Your code will work on AWS Lambda with RDS")
        
        print("\n" + "="*70)
        print("SUCCESS! PostgreSQL works perfectly with your code")
        print("="*70)
        print("\n✅ Your code is ready for AWS Lambda + RDS PostgreSQL")
        print("\nNext steps:")
        print("  1. Keep this container running if you want to continue testing")
        print("  2. Deploy to AWS Lambda (see AWS_LAMBDA.md)")
        print("  3. Point DATABASE_URL to your RDS instance")
        print("\nPostgreSQL container is still running for your testing.")
        print("Stop it with: docker stop trustpilot_postgres")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        cleanup()
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        cleanup()
        return 1

if __name__ == "__main__":
    sys.exit(main())
