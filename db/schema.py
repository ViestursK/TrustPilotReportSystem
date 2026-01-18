from sqlalchemy import (
    MetaData, Table, Column,
    Index, Integer, String, Text,
    DateTime, Float, Boolean, ForeignKey
)

metadata = MetaData()

brands = Table(
    "brands",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("domain", String, unique=True, nullable=False),
    Column("business_id", String, nullable=False),
    Column("brand_name", String, nullable=False),
    Column("trust_score", Float),
    Column("stars", Integer),
    Column("total_reviews", Integer),
    Column("past_week_reviews", Integer),
    Column("logo_base64", Text),
    Column("website", String),
    Column("is_claimed", Boolean),
    Column("categories", Text),  # JSON string
    Column("ai_summary_text", Text),
    Column("ai_summary_updated_at", String),
    Column("ai_summary_language", String),
    Column("ai_summary_model_version", String),
    Column("created_at", DateTime, nullable=False),
    Column("last_scraped_at", DateTime),
)

reviews = Table(
    "reviews",
    metadata,
    Column("id", String, primary_key=True),
    Column("brand_id", Integer, ForeignKey("brands.id"), nullable=False),
    Column("rating", Integer, nullable=False),
    Column("text", Text),
    Column("title", String),
    Column("author_name", String),
    Column("author_id", String),
    Column("author_image_url", String),
    Column("author_review_count", Integer),
    Column("author_country_code", String),
    Column("author_has_image", Boolean),
    Column("published_date", DateTime, nullable=False),
    Column("updated_date", DateTime),
    Column("experienced_date", DateTime),
    Column("language", String),
    Column("source", String),
    Column("is_verified", Boolean),
    Column("likes", Integer, default=0),
    Column("reply_message", Text),
    Column("reply_date", DateTime),
    Column("labels_merged", Text),  # JSON string
    Column("topics", Text),  # JSON array string
    Column("scraped_at", DateTime, nullable=False),
)

weekly_snapshots = Table(
    "weekly_snapshots",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("brand_id", Integer, ForeignKey("brands.id"), nullable=False),
    Column("week_key", String, nullable=False),
    Column("week_start", DateTime, nullable=False),
    Column("week_end", DateTime, nullable=False),
    Column("review_count", Integer),
    Column("avg_rating", Float),
    Column("positive_count", Integer),
    Column("neutral_count", Integer),
    Column("negative_count", Integer),
    Column("organic_count", Integer),
    Column("verified_count", Integer),
    Column("invited_count", Integer),
    Column("avg_response_time_hours", Float),
    Column("top_mentions", Text),  # JSON array string
    Column("ai_summary", Text),
    Column("created_at", DateTime, nullable=False),
)

Index('idx_reviews_brand', reviews.c.brand_id)
Index('idx_reviews_date', reviews.c.published_date)
Index('idx_snapshots_brand', weekly_snapshots.c.brand_id)
Index('idx_snapshots_week_key', weekly_snapshots.c.brand_id, weekly_snapshots.c.week_key, unique=True)
