#!/usr/bin/env python3
"""
Onboarding new brands:
1. Scrape all reviews (unlimited pages, JWT if available)
2. Insert brand and reviews
3. Tag reviews with topics
4. Calculate weekly snapshots (historical weeks only)
"""

import scraper
from db import queries as database
import tag_topics
from datetime import datetime, timedelta

def onboard_brand(domain):
    """Onboard a new brand: scrape all reviews, tag topics, create weekly snapshots"""

    print("\n" + "="*70)
    print(f"ONBOARDING: {domain}")
    print("="*70)

    # 1️⃣ Full scrape (unlimited pages, JWT if available)
    brand_data = scraper.scrape_brand(domain, max_pages=None, use_jwt=True)
    if not brand_data:
        print(f"[ERROR] Failed to onboard {domain}")
        return

    reviews_list = brand_data['reviews']
    company_data = brand_data['company']
    top_mentions = company_data.get('top_mentions', [])

    # 2️⃣ Insert brand metadata
    brand_id = database.add_brand(domain, company_data)

    # 3️⃣ Insert all reviews (deduplicated)
    inserted, skipped = database.insert_reviews(brand_id, reviews_list)
    print(f"[INFO] Reviews inserted: {inserted}, skipped: {skipped}")

    # 4️⃣ Tag all reviews with topics
    if top_mentions:
        tag_topics.tag_reviews_with_topics(domain, brand_id, top_mentions)

    # 5️⃣ Calculate weekly snapshots for historical weeks
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
    while week_monday <= current_week_monday:
        week_sunday = week_monday + timedelta(days=6, hours=23, minutes=59, seconds=59)
        week_key = week_monday.strftime("%Y-W%U")

        # Skip current week snapshot (daily scrape will handle it)
        if week_monday != current_week_monday:
            database.calculate_and_save_snapshot(
                brand_id,
                week_key,
                week_monday.isoformat(),
                week_sunday.isoformat(),
                top_mentions=None,  # snapshot reads topics from reviews
                ai_summary=company_data.get('ai_summary', {}).get('summary')
            )
            weeks_created += 1

        week_monday += timedelta(days=7)

    print("\n[COMPLETE] ONBOARDING COMPLETE!")
    print(f"Brand: {company_data['brand_name']}")
    print(f"Total Reviews: {len(reviews_list)}")
    print(f"Weeks Created: {weeks_created}")

    return brand_id
