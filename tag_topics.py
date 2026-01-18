#!/usr/bin/env python3
"""
Tag reviews with topics using multilingual keyword matching
"""

import json
from sqlalchemy import update
from db.engine import get_engine
from db.schema import reviews

def tag_reviews_with_topics(domain, brand_id, top_mentions):
    """
    Tag reviews with topics based on text matching
    top_mentions: list of topic names in English (from get_top_mentions)
    """
    if not top_mentions:
        print("  [INFO] No top mentions to tag")
        return
    
    print(f"  [INFO] Tagging reviews with {len(top_mentions)} topics...")
    
    engine = get_engine()
    
    with engine.begin() as conn:
        # Get all reviews for this brand
        result = conn.execute(
            f"SELECT id, text, title FROM reviews WHERE brand_id = {brand_id}"
        )
        
        tagged_count = 0
        
        for review_id, text, title in result:
            full_text = f"{title or ''} {text or ''}".lower()
            
            if not full_text.strip():
                continue
            
            matched_topics = []
            
            # Simple keyword matching
            for topic in top_mentions:
                topic_lower = topic.lower()
                if topic_lower in full_text:
                    matched_topics.append(topic)
            
            if matched_topics:
                conn.execute(
                    update(reviews)
                    .where(reviews.c.id == review_id)
                    .values(topics=json.dumps(matched_topics))
                )
                tagged_count += 1
        
        print(f"  [SUCCESS] Tagged {tagged_count} reviews with topics")
