#!/usr/bin/env python3
"""
Daily incremental scrape with auto-onboarding
1. Checks for new brands → triggers onboarding
2. Scrapes existing brands (last 30 days, max 10 pages)
3. Updates database with deduplication
"""
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from db import init_db
from db import queries as database
from scraper import scraper
from scraper import onboarding
load_dotenv()

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_week_boundaries(date=None):
    """Get Monday-Sunday for a given date (or today)"""
    if date is None:
        date = datetime.now()
    
    monday = date - timedelta(days=date.weekday())
    monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)
    sunday = monday + timedelta(days=6, hours=23, minutes=59, seconds=59)
    
    return monday, sunday

def get_week_key(monday):
    """Get ISO week key like '2025-W01'"""
    return monday.strftime("%Y-W%U")

# =============================================================================
# DAILY SCRAPE FOR EXISTING BRAND
# =============================================================================

def daily_scrape_brand(domain, brand_id):
    """Daily scrape for an existing brand (smart pagination, auto-tag topics)"""
    print(f"\n{'='*60}")
    print(f"DAILY SCRAPE: {domain}")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print('='*60)
    
    # Get last saved review ID for smart pagination
    last_review_id = database.get_latest_review_id(brand_id)
    if last_review_id:
        print(f"[INFO] Last saved review: {last_review_id}")
    
    # Scrape last 30 days (max 10 pages)
    max_pages = int(os.getenv('MAX_PAGES', 10))
    print(f"\n[INFO] Scraping last 30 days (max {max_pages} pages, public data)...")
    new_data = scraper.scrape_brand(
        domain, 
        max_pages=max_pages, 
        use_jwt=False,
        last_review_id=last_review_id,
        filter_last_30_days=True
    )
    
    if not new_data:
        print("[WARNING] Scrape failed, skipping")
        return False
    
    print(f"[INFO] Retrieved {len(new_data['reviews'])} reviews")
    
    # Update brand metadata
    database.update_brand_metadata(brand_id, new_data['company'])
    
    # Insert new reviews (deduplicated)
    inserted, skipped = database.insert_reviews(brand_id, new_data['reviews'])
    print(f"[INFO] Reviews inserted: {inserted}, skipped: {skipped}")
    
    # ==========================
    # ALWAYS TAG TOPICS
    # ==========================
    import scraper.tag_topics as tag_topics
    
    # Determine top mentions
    top_mentions = new_data['company'].get('top_mentions')
    if not top_mentions:
        # Fetch current top mentions from Trustpilot if missing
        top_mentions = scraper.get_top_mentions(new_data['company']['business_id'])
    
    if top_mentions:
        # Get current week's reviews
        today = datetime.now()
        current_monday, current_sunday = get_week_boundaries(today)
        week_reviews = database.get_reviews_for_week(
            brand_id, current_monday.isoformat(), current_sunday.isoformat()
        )
        
        if week_reviews:
            print(f"[INFO] Tagging {len(week_reviews)} reviews with topics...")
            tag_topics.tag_reviews_with_topics(domain, brand_id, top_mentions, reviews_list=week_reviews)
        else:
            print("[INFO] No reviews in current week to tag")
    else:
        print("[WARNING] No top mentions available for tagging")
    
    # ==========================
    # UPDATE CURRENT WEEK SNAPSHOT
    # ==========================
    week_key = get_week_key(current_monday)
    print(f"\n[INFO] Updating current week snapshot: {week_key}")
    database.calculate_and_save_snapshot(
        brand_id,
        week_key,
        current_monday.isoformat(),
        current_sunday.isoformat(),
        top_mentions,
        new_data['company'].get('ai_summary', {}).get('summary')
    )
    
    print(f"\n[COMPLETE] Daily scrape complete for {domain}")
    return True

# =============================================================================
# MAIN
# =============================================================================

def main():
    print("\n" + "="*70)
    print("DAILY SCRAPE AUTOMATION")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("="*70)
    
    # Initialize database
    init_db()
    
    # Get brands from .env
    brands_env = os.getenv('BRANDS', '').split(',')
    brands_env = [b.strip() for b in brands_env if b.strip()]
    
    if not brands_env:
        print("[WARNING] No brands found in .env file")
        return
    
    # Get existing brands from DB
    existing_brands = database.get_all_brand_domains()
    
    # Detect new brands to onboard
    new_brands = [b for b in brands_env if b not in existing_brands]
    
    # =========================
    # Onboard new brands
    # =========================
    if new_brands:
        print(f"\n{'='*70}")
        print(f"[INFO] NEW BRANDS DETECTED: {len(new_brands)}")
        print(f"{'='*70}")
        for brand in new_brands:
            print(f"  - {brand}")
        
        print("\n[INFO] Starting onboarding process...")
        for brand in new_brands:
            try:
                onboarding.onboard_brand(brand)
                # Immediately run daily scrape logic for new brand
                brand_id = database.get_brand_id(brand)
                if brand_id:
                    daily_scrape_brand(brand, brand_id)
            except Exception as e:
                print(f"\n[WARNING] Onboarding failed for {brand}: {e}")
                import traceback
                traceback.print_exc()
    
    # Refresh the list of existing brands after onboarding
    existing_brands = database.get_all_brand_domains()
    
    # =========================
    # Daily scrape for all brands
    # =========================
    print(f"\n{'='*70}")
    print(f"DAILY SCRAPE: {len(existing_brands)} BRANDS")
    print(f"{'='*70}")
    
    for brand in existing_brands:
        try:
            brand_id = database.get_brand_id(brand)
            if not brand_id:
                continue
            daily_scrape_brand(brand, brand_id)
        except Exception as e:
            print(f"\n[WARNING] Error scraping {brand}: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*70)
    print("[COMPLETE] DAILY SCRAPE COMPLETE")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()