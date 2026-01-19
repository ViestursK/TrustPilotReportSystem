# db/queries.py

import json
from datetime import datetime
from sqlalchemy import text
from db.engine import get_engine

engine = get_engine()

from sqlalchemy import text
from db.engine import get_engine

engine = get_engine()

def get_brand_id(domain: str) -> int | None:
    with engine.begin() as conn:
        row = conn.execute(
            text("""
                SELECT id
                FROM brands
                WHERE domain = :domain
            """),
            {"domain": domain}
        ).fetchone()

        return row.id if row else None

from sqlalchemy import text
from db.engine import get_engine

engine = get_engine()


def get_snapshots_for_brand(brand_id: int, limit: int = 10):
    """
    Return latest weekly snapshots for a brand.
    """
    with engine.begin() as conn:
        rows = conn.execute(
            text("""
                SELECT
                    id,
                    brand_id,
                    week_key,
                    week_start,
                    week_end,
                    review_count,
                    avg_rating,
                    positive_count,
                    neutral_count,
                    negative_count,
                    organic_count,
                    verified_count,
                    invited_count,
                    avg_response_time_hours,
                    top_mentions,
                    language_counts,
                    mentions_sentiment,
                    ai_summary,
                    created_at
                FROM weekly_snapshots
                WHERE brand_id = :brand_id
                ORDER BY week_start DESC
                LIMIT :limit
            """),
            {
                "brand_id": brand_id,
                "limit": limit
            }
        ).mappings().all()

        # Convert RowMapping → dict (CLI expects JSON-serializable objects)
        return [dict(row) for row in rows]


def calculate_and_save_snapshot(
    brand_id: int,
    week_key: str,
    week_start,
    week_end,
    top_mentions=None,
    ai_summary=None
):
    top_mentions = top_mentions or []
    ai_summary = ai_summary or ""

    with engine.begin() as conn:
        rows = conn.execute(
            text("""
                SELECT
                    rating,
                    language,
                    source,
                    topics
                FROM reviews
                WHERE brand_id = :brand_id
                  AND published_date >= :week_start
                  AND published_date <= :week_end
            """),
            {
                "brand_id": brand_id,
                "week_start": week_start,
                "week_end": week_end,
            }
        ).fetchall()

        review_count = len(rows)
        avg_rating = sum(r.rating for r in rows) / review_count if review_count else 0

        positive_count = sum(1 for r in rows if r.rating >= 4)
        neutral_count = sum(1 for r in rows if r.rating == 3)
        negative_count = sum(1 for r in rows if r.rating <= 2)

        invited_count = sum(1 for r in rows if r.source and "invited" in r.source.lower())
        verified_count = sum(1 for r in rows if r.source and "verified" in r.source.lower())
        organic_count = review_count - invited_count - verified_count

        # ---------- LANGUAGE COUNTS ----------
        language_counts = {}
        for r in rows:
            if r.language:
                language_counts[r.language] = language_counts.get(r.language, 0) + 1

        # ---------- TOPIC SENTIMENT ----------
        mentions_sentiment = {}

        for r in rows:
            if not r.topics:
                continue

            try:
                topics = json.loads(r.topics)
            except Exception:
                continue

            for topic in topics:
                if topic not in mentions_sentiment:
                    mentions_sentiment[topic] = {
                        "positive": 0,
                        "neutral": 0,
                        "negative": 0,
                    }

                if r.rating >= 4:
                    mentions_sentiment[topic]["positive"] += 1
                elif r.rating == 3:
                    mentions_sentiment[topic]["neutral"] += 1
                else:
                    mentions_sentiment[topic]["negative"] += 1

        conn.execute(
            text("""
                INSERT INTO weekly_snapshots (
                    brand_id,
                    week_key,
                    week_start,
                    week_end,
                    review_count,
                    avg_rating,
                    positive_count,
                    neutral_count,
                    negative_count,
                    organic_count,
                    verified_count,
                    invited_count,
                    avg_response_time_hours,
                    top_mentions,
                    language_counts,
                    mentions_sentiment,
                    ai_summary,
                    created_at
                )
                VALUES (
                    :brand_id,
                    :week_key,
                    :week_start,
                    :week_end,
                    :review_count,
                    :avg_rating,
                    :positive_count,
                    :neutral_count,
                    :negative_count,
                    :organic_count,
                    :verified_count,
                    :invited_count,
                    0,
                    :top_mentions,
                    :language_counts,
                    :mentions_sentiment,
                    :ai_summary,
                    :created_at
                )
                ON CONFLICT (brand_id, week_key)
                DO UPDATE SET
                    review_count = EXCLUDED.review_count,
                    avg_rating = EXCLUDED.avg_rating,
                    positive_count = EXCLUDED.positive_count,
                    neutral_count = EXCLUDED.neutral_count,
                    negative_count = EXCLUDED.negative_count,
                    organic_count = EXCLUDED.organic_count,
                    verified_count = EXCLUDED.verified_count,
                    invited_count = EXCLUDED.invited_count,
                    top_mentions = EXCLUDED.top_mentions,
                    language_counts = EXCLUDED.language_counts,
                    mentions_sentiment = EXCLUDED.mentions_sentiment,
                    ai_summary = EXCLUDED.ai_summary,
                    created_at = EXCLUDED.created_at
            """),
            {
                "brand_id": brand_id,
                "week_key": week_key,
                "week_start": week_start,
                "week_end": week_end,
                "review_count": review_count,
                "avg_rating": avg_rating,
                "positive_count": positive_count,
                "neutral_count": neutral_count,
                "negative_count": negative_count,
                "organic_count": organic_count,
                "verified_count": verified_count,
                "invited_count": invited_count,
                "top_mentions": json.dumps(top_mentions),
                "language_counts": json.dumps(language_counts),
                "mentions_sentiment": json.dumps(mentions_sentiment),
                "ai_summary": ai_summary,
                "created_at": datetime.utcnow(),
            }
        )

        print(f"[INFO] Weekly snapshot saved for brand_id {brand_id}, week {week_key}")

# Add these functions to db/queries.py

def get_all_brand_domains():
    """Get list of all brand domains in database"""
    with engine.begin() as conn:
        rows = conn.execute(
            text("SELECT domain FROM brands")
        ).fetchall()
        return [row[0] for row in rows]

def add_brand(domain: str, company_data: dict) -> int:
    """Add new brand to database"""
    with engine.begin() as conn:
        result = conn.execute(
            text("""
                INSERT INTO brands (
                    domain, business_id, brand_name, trust_score, stars,
                    total_reviews, past_week_reviews, website, is_claimed,
                    categories, ai_summary_text, ai_summary_updated_at,
                    ai_summary_language, ai_summary_model_version, created_at
                )
                VALUES (
                    :domain, :business_id, :brand_name, :trust_score, :stars,
                    :total_reviews, :past_week_reviews, :website, :is_claimed,
                    :categories, :ai_summary_text, :ai_summary_updated_at,
                    :ai_summary_language, :ai_summary_model_version, :created_at
                )
                RETURNING id
            """),
            {
                "domain": domain,
                "business_id": company_data['business_id'],
                "brand_name": company_data['brand_name'],
                "trust_score": company_data.get('trust_score'),
                "stars": company_data.get('stars'),
                "total_reviews": company_data.get('total_reviews'),
                "past_week_reviews": company_data.get('past_week_reviews', 0),
                "website": company_data.get('website'),
                "is_claimed": company_data.get('is_claimed', False),
                "categories": json.dumps(company_data.get('categories', [])),
                "ai_summary_text": company_data.get('ai_summary', {}).get('summary'),
                "ai_summary_updated_at": company_data.get('ai_summary', {}).get('updated_at'),
                "ai_summary_language": company_data.get('ai_summary', {}).get('language'),
                "ai_summary_model_version": company_data.get('ai_summary', {}).get('model_version'),
                "created_at": datetime.utcnow()
            }
        )
        return result.fetchone()[0]

def update_brand_metadata(brand_id: int, company_data: dict):
    """Update brand metadata"""
    with engine.begin() as conn:
        conn.execute(
            text("""
                UPDATE brands SET
                    trust_score = :trust_score,
                    stars = :stars,
                    total_reviews = :total_reviews,
                    past_week_reviews = :past_week_reviews,
                    last_scraped_at = :last_scraped_at
                WHERE id = :brand_id
            """),
            {
                "brand_id": brand_id,
                "trust_score": company_data.get('trust_score'),
                "stars": company_data.get('stars'),
                "total_reviews": company_data.get('total_reviews'),
                "past_week_reviews": company_data.get('past_week_reviews', 0),
                "last_scraped_at": datetime.utcnow()
            }
        )

def get_latest_review_id(brand_id: int) -> str | None:
    """Get most recent review ID for a brand"""
    with engine.begin() as conn:
        row = conn.execute(
            text("""
                SELECT id FROM reviews
                WHERE brand_id = :brand_id
                ORDER BY published_date DESC
                LIMIT 1
            """),
            {"brand_id": brand_id}
        ).fetchone()
        return row[0] if row else None

def insert_reviews(brand_id: int, reviews_list: list) -> tuple[int, int]:
    """Insert reviews with deduplication. Returns (inserted, skipped)"""
    inserted = 0
    skipped = 0
    
    with engine.begin() as conn:
        for review in reviews_list:
            try:
                conn.execute(
                    text("""
                        INSERT INTO reviews (
                            id, brand_id, rating, text, title, author_name,
                            author_id, published_date, language, source,
                            is_verified, likes, scraped_at
                        )
                        VALUES (
                            :id, :brand_id, :rating, :text, :title, :author_name,
                            :author_id, :published_date, :language, :source,
                            :is_verified, :likes, :scraped_at
                        )
                        ON CONFLICT (id) DO NOTHING
                    """),
                    {
                        "id": review['id'],
                        "brand_id": brand_id,
                        "rating": review['rating'],
                        "text": review.get('text'),
                        "title": review.get('title'),
                        "author_name": review.get('consumer', {}).get('displayName'),
                        "author_id": review.get('consumer', {}).get('id'),
                        "published_date": review['dates']['publishedDate'],
                        "language": review.get('language'),
                        "source": review.get('source'),
                        "is_verified": review.get('isVerified', False),
                        "likes": review.get('likes', 0),
                        "scraped_at": datetime.utcnow()
                    }
                )
                inserted += 1
            except:
                skipped += 1
                
    return inserted, skipped

def get_reviews_for_week(brand_id: int, week_start: str, week_end: str) -> list:
    """Get all reviews for a specific week"""
    with engine.begin() as conn:
        rows = conn.execute(
            text("""
                SELECT id, text, title FROM reviews
                WHERE brand_id = :brand_id
                  AND published_date >= :week_start
                  AND published_date <= :week_end
            """),
            {
                "brand_id": brand_id,
                "week_start": week_start,
                "week_end": week_end
            }
        ).mappings().all()
        return [dict(row) for row in rows]

def get_brand_info(brand_id: int) -> dict | None:
    """Get brand information"""
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT * FROM brands WHERE id = :brand_id"),
            {"brand_id": brand_id}
        ).mappings().fetchone()
        return dict(row) if row else None