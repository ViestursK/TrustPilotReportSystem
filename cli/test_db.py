#!/usr/bin/env python3
"""
Test script to verify database setup and basic functionality
"""

import sys
import os

# Test imports
try:
    import sqlalchemy
    from sqlalchemy import text, delete
    import requests
    from dotenv import load_dotenv
    print("✓ All required packages imported successfully")
except ImportError as e:
    print(f"✗ Missing package: {e}")
    print("\nPlease install requirements:")
    print("  pip install -r requirements.txt")
    sys.exit(1)

# Load environment
load_dotenv()

# Test database connection
from db.engine import get_engine
from db.schema import brands, reviews, weekly_snapshots

# Test domain to use (won't conflict with real data)
TEST_DOMAIN = "test-company.com"

def cleanup_test_data():
    """Remove any existing test data"""
    try:
        engine = get_engine()
        with engine.begin() as conn:
            # Delete in correct order (foreign key constraints)
            conn.execute(delete(weekly_snapshots).where(
                weekly_snapshots.c.brand_id.in_(
                    sqlalchemy.select(brands.c.id).where(brands.c.domain == TEST_DOMAIN)
                )
            ))
            conn.execute(delete(reviews).where(
                reviews.c.brand_id.in_(
                    sqlalchemy.select(brands.c.id).where(brands.c.domain == TEST_DOMAIN)
                )
            ))
            conn.execute(delete(brands).where(brands.c.domain == TEST_DOMAIN))
    except Exception as e:
        # Ignore errors during cleanup (table might not exist yet)
        pass

def test_database_connection():
    """Test database connectivity"""
    print("\n" + "="*60)
    print("TESTING DATABASE CONNECTION")
    print("="*60)
    
    try:
        engine = get_engine()
        db_url = str(engine.url)
        print(f"\nDatabase URL: {db_url}")
        
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
            print("✓ Database connection successful")
        
        return True
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False

def test_table_creation():
    """Test table creation"""
    print("\n" + "="*60)
    print("TESTING TABLE CREATION")
    print("="*60)
    
    try:
        from db import init_db
        init_db()
        print("✓ Tables created successfully")
        
        # Verify tables exist
        engine = get_engine()
        with engine.connect() as conn:
            # Check if it's PostgreSQL or SQLite
            db_url = str(engine.url)
            if 'postgresql' in db_url:
                result = conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'"))
            else:
                result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
            
            tables = [row[0] for row in result.fetchall()]
            
            expected_tables = ['brands', 'reviews', 'weekly_snapshots']
            for table in expected_tables:
                if table in tables:
                    print(f"  ✓ Table '{table}' exists")
                else:
                    print(f"  ✗ Table '{table}' missing")
                    return False
        
        return True
    except Exception as e:
        print(f"✗ Table creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_brand_operations():
    """Test basic brand database operations"""
    print("\n" + "="*60)
    print("TESTING BRAND OPERATIONS")
    print("="*60)
    
    try:
        from db import queries as database
        from datetime import datetime
        
        # Clean up any existing test data first
        cleanup_test_data()
        
        # Test data
        test_company_data = {
            'business_id': 'test123',
            'brand_name': 'Test Company',
            'trust_score': 4.5,
            'stars': 5,
            'total_reviews': 100,
            'past_week_reviews': 10,
            'website': 'https://test-company.com',
            'is_claimed': True,
            'categories': ['Technology', 'Software'],
            'ai_summary': {
                'summary': 'Great company',
                'updated_at': datetime.now().isoformat(),
                'language': 'en',
                'model_version': '1.0'
            }
        }
        
        # Add brand
        brand_id = database.add_brand(TEST_DOMAIN, test_company_data)
        print(f"✓ Brand added with ID: {brand_id}")
        
        # Retrieve brand
        brand_info = database.get_brand_info(brand_id)
        if brand_info:
            print(f"✓ Brand retrieved: {brand_info['brand_name']}")
        else:
            print("✗ Failed to retrieve brand")
            return False
        
        # Get all domains
        domains = database.get_all_brand_domains()
        if TEST_DOMAIN in domains:
            print(f"✓ Brand domain found in list: {TEST_DOMAIN}")
        else:
            print("✗ Brand domain not in list")
            return False
        
        return True
    except Exception as e:
        print(f"✗ Brand operations failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("\n" + "="*60)
    print("TRUSTPILOT SCRAPER - DATABASE TEST")
    print("="*60)
    
    tests = [
        ("Database Connection", test_database_connection),
        ("Table Creation", test_table_creation),
        ("Brand Operations", test_brand_operations),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ Test '{test_name}' crashed: {e}")
            results.append((test_name, False))
    
    # Clean up test data after all tests
    print("\n" + "="*60)
    print("CLEANING UP TEST DATA")
    print("="*60)
    cleanup_test_data()
    print("✓ Test data cleaned")
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for test_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{status}: {test_name}")
    
    all_passed = all(result for _, result in results)
    
    if all_passed:
        print("\n✓ ALL TESTS PASSED")
        print("\nYou can now run:")
        print("  python onboarding.py <domain>  # Onboard a new brand")
        print("  python daily_scrape.py          # Run daily scrape")
    else:
        print("\n✗ SOME TESTS FAILED")
        print("\nPlease fix the issues above before proceeding.")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())