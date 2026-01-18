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
