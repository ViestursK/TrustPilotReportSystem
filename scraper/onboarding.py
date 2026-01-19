#!/usr/bin/env python3
"""
Onboarding new brands:
1. Scrape all reviews (unlimited pages, JWT if available)
2. Insert brand and reviews
3. Tag reviews with topics
4. Calculate weekly snapshots (all weeks including current)
"""

import sys
import os
# Add parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Now we can import from project root
from scraper.scraper import scrape_brand, get_top_mentions
from db import queries as database
from scraper.tag_topics import tag_reviews_with_topics
from datetime import datetime, timedelta

def onboard_brand(domain):
    """Onboard a new brand: scrape all reviews, tag topics, create weekly snapshots"""

    print("\n" + "="*70)
    print(f"ONBOARDING: {domain}")
    print("="*70)

    # 1️⃣ Full scrape (unlimited pages, JWT if available)
    brand_data = scrape_brand(domain, max_pages=None, use_jwt=True)
    if not brand_data:
        print(f"[ERROR] Failed to onboard {domain}")
        return

    reviews_list = brand_data['reviews']
    company_data = brand_data['company']
    top_mentions = company_data.get('top_mentions', [])

    # 2️⃣ Insert brand metadata
    brand_id = database.get_brand_id(domain)
    if brand_id:
        print(f"[INFO] Brand already exists (ID: {brand_id}), updating...")
        database.update_brand_metadata(brand_id, company_data)
    else:
        print(f"[INFO] Adding new brand...")
        brand_id = database.add_brand(domain, company_data)

    # 3️⃣ Insert all reviews (deduplicated)
    inserted, skipped = database.insert_reviews(brand_id, reviews_list)
    print(f"[INFO] Reviews inserted: {inserted}, skipped: {skipped}")

    # 4️⃣ Tag all reviews with topics
    if top_mentions:
        print(f"[INFO] Tagging reviews with {len(top_mentions)} topics...")
        tag_reviews_with_topics(domain, brand_id, top_mentions)
    else:
        print("[WARNING] No top mentions available for tagging")

    # 5️⃣ Calculate weekly snapshots for all weeks
    if reviews_list:
        first_review_date = min(
            datetime.fromisoformat(r['dates']['publishedDate'].replace('Z', ''))
            for r in reviews_list
        )
    else:
        first_review_date = datetime.now()

    today = datetime.now()
    week_monday = first_review_date - timedelta(days=first_review_date.weekday())
    current_week_monday = today - timedelta(days=today.weekday())

    weeks_created = 0
    print(f"\n[INFO] Creating weekly snapshots from {week_monday.date()} to {current_week_monday.date()}...")
    
    while week_monday <= current_week_monday:
        week_sunday = week_monday + timedelta(days=6, hours=23, minutes=59, seconds=59)
        week_key = week_monday.strftime("%Y-W%U")

        # Create snapshot for all weeks (including current)
        database.calculate_and_save_snapshot(
            brand_id,
            week_key,
            week_monday.isoformat(),
            week_sunday.isoformat(),
            top_mentions=top_mentions,
            ai_summary=company_data.get('ai_summary', {}).get('summary')
        )
        weeks_created += 1
        print(f"  ✓ Created snapshot for week {week_key}")

        week_monday += timedelta(days=7)

    print("\n" + "="*70)
    print("[COMPLETE] ONBOARDING COMPLETE!")
    print("="*70)
    print(f"Brand: {company_data['brand_name']}")
    print(f"Total Reviews: {len(reviews_list)}")
    print(f"Weeks Created: {weeks_created}")
    print(f"Top Mentions: {', '.join(top_mentions) if top_mentions else 'None'}")
    print("="*70 + "\n")

    return brand_id


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("\nUsage: python onboarding.py <domain>")
        print("Example: python onboarding.py ketogo.app\n")
        sys.exit(1)
    
    from db import init_db
    init_db()
    
    domain = sys.argv[1]
    onboard_brand(domain)