#!/usr/bin/env python3
"""
Tag reviews with topics using multilingual keyword matching
"""

import json
from sqlalchemy import update, text
from db.engine import get_engine
from db.schema import reviews

def tag_reviews_with_topics(domain, brand_id, top_mentions, reviews_list=None):
    """
    Tag reviews with topics based on text matching.
    
    Parameters:
    - domain: brand domain (for logging)
    - brand_id: the brand's database ID
    - top_mentions: list of topic names in English
    - reviews_list: optional list of reviews (dicts) to tag instead of fetching all
      Each dict should have keys: 'id', 'text', 'title'
    """
    if not top_mentions:
        print("  [INFO] No top mentions to tag")
        return
    
    print(f"  [INFO] Tagging reviews with {len(top_mentions)} topics...")
    
    engine = get_engine()
    
    with engine.begin() as conn:
        # Use provided reviews list or fetch all from DB
        if reviews_list is not None:
            review_rows = [(r['id'], r.get('text', ''), r.get('title', '')) for r in reviews_list]
        else:
            result = conn.execute(
                text(f"SELECT id, text, title FROM reviews WHERE brand_id = {brand_id}")
            )
            review_rows = [(r[0], r[1], r[2]) for r in result]
        
        tagged_count = 0
        
        for review_id, text_content, title in review_rows:
            full_text = f"{title or ''} {text_content or ''}".lower()
            if not full_text.strip():
                continue
            
            matched_topics = []
            for topic in top_mentions:
                if topic.lower() in full_text:
                    matched_topics.append(topic)
            
            if matched_topics:
                conn.execute(
                    update(reviews)
                    .where(reviews.c.id == review_id)
                    .values(topics=json.dumps(matched_topics))
                )
                tagged_count += 1
        
        print(f"  [SUCCESS] Tagged {tagged_count} reviews with topics")