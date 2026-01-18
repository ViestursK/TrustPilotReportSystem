from sqlalchemy import select, insert, update, func, and_, or_
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from datetime import datetime
import json
from db.engine import get_engine
from db.schema import brands, reviews, weekly_snapshots

engine = get_engine()

# ---------- BRAND ----------

def add_brand(domain, company_data, logo_base64=None):
    ai_summary = company_data.get('ai_summary', {})
    
    with engine.begin() as conn:
        result = conn.execute(
            insert(brands).values(
                domain=domain,
                business_id=company_data['business_id'],
                brand_name=company_data['brand_name'],
                trust_score=company_data['trust_score'],
                stars=company_data.get('stars', company_data['trust_score']),
                total_reviews=company_data['total_reviews'],
                past_week_reviews=company_data.get('past_week_reviews', 0),
                logo_base64=logo_base64,
                website=company_data.get('website', ''),
                is_claimed=company_data.get('is_claimed', False),
                categories=json.dumps(company_data.get('categories', [])),
                ai_summary_text=ai_summary.get('summary') if ai_summary else None,
                ai_summary_updated_at=ai_summary.get('updatedAt') or ai_summary.get('updated_at') if ai_summary else None,
                ai_summary_language=ai_summary.get('lang') or ai_summary.get('language') if ai_summary else None,
                ai_summary_model_version=ai_summary.get('modelVersion') or ai_summary.get('model_version') if ai_summary else None,
                created_at=datetime.now(),
            )
        )
        return result.inserted_primary_key[0]

def get_all_brand_domains():
    with engine.begin() as conn:
        return [r[0] for r in conn.execute(select(brands.c.domain))]

def get_brand_id(domain):
    with engine.begin() as conn:
        return conn.execute(
            select(brands.c.id).where(brands.c.domain == domain)
        ).scalar()

def update_brand_metadata(brand_id, company_data):
    ai_summary = company_data.get('ai_summary', {})
    
    with engine.begin() as conn:
        conn.execute(
            update(brands)
            .where(brands.c.id == brand_id)
            .values(
                trust_score=company_data['trust_score'],
                stars=company_data.get('stars', company_data['trust_score']),
                total_reviews=company_data['total_reviews'],
                past_week_reviews=company_data.get('past_week_reviews', 0),
                ai_summary_text=ai_summary.get('summary') if ai_summary else None,
                ai_summary_updated_at=ai_summary.get('updatedAt') or ai_summary.get('updated_at') if ai_summary else None,
                ai_summary_language=ai_summary.get('lang') or ai_summary.get('language') if ai_summary else None,
                ai_summary_model_version=ai_summary.get('modelVersion') or ai_summary.get('model_version') if ai_summary else None,
                last_scraped_at=datetime.now(),
            )
        )

def get_brand_info(brand_id):
    with engine.begin() as conn:
        result = conn.execute(
            select(brands).where(brands.c.id == brand_id)
        ).first()
        return dict(result._mapping) if result else None

# ---------- REVIEWS ----------

def get_latest_review_id(brand_id):
    with engine.begin() as conn:
        return conn.execute(
            select(reviews.c.id)
            .where(reviews.c.brand_id == brand_id)
            .order_by(reviews.c.published_date.desc())
            .limit(1)
        ).scalar()

def insert_reviews(brand_id, review_list):
    inserted, skipped = 0, 0
    
    with engine.begin() as conn:
        for review in review_list:
            try:
                consumer = review.get('consumer', {})
                reply = review.get('reply')
                labels_merged = review.get('labels', {}).get('merged')
                
                conn.execute(
                    insert(reviews).values(
                        id=review['id'],
                        brand_id=brand_id,
                        rating=review['rating'],
                        text=review.get('text', ''),
                        title=review.get('title', ''),
                        author_name=consumer.get('displayName', ''),
                        author_id=consumer.get('id', ''),
                        author_image_url=consumer.get('imageUrl', ''),
                        author_review_count=consumer.get('numberOfReviews', 0),
                        author_country_code=consumer.get('countryCode', ''),
                        author_has_image=consumer.get('hasImage', False),
                        published_date=datetime.fromisoformat(review['dates']['publishedDate'].replace('Z', '')),
                        updated_date=datetime.fromisoformat(review['dates']['updatedDate'].replace('Z', '')) if review['dates'].get('updatedDate') else None,
                        experienced_date=datetime.fromisoformat(review['dates']['experiencedDate'].replace('Z', '')) if review['dates'].get('experiencedDate') else None,
                        language=review.get('language', ''),
                        source=review.get('source', ''),
                        is_verified=review.get('labels', {}).get('verification', {}).get('isVerified', False),
                        likes=review.get('likes', 0),
                        reply_message=reply.get('message') if reply else None,
                        reply_date=datetime.fromisoformat(reply['publishedDate'].replace('Z', '')) if reply and reply.get('publishedDate') else None,
                        labels_merged=json.dumps(labels_merged) if labels_merged else None,
                        topics=None,
                        scraped_at=datetime.now(),
                    )
                )
                inserted += 1
            except Exception:
                skipped += 1
    
    return inserted, skipped

def get_reviews_for_week(brand_id, week_start, week_end):
    with engine.begin() as conn:
        results = conn.execute(
            select(reviews)
            .where(
                and_(
                    reviews.c.brand_id == brand_id,
                    reviews.c.published_date >= datetime.fromisoformat(week_start),
                    reviews.c.published_date <= datetime.fromisoformat(week_end)
                )
            )
            .order_by(reviews.c.published_date.desc())
        ).fetchall()
        return [dict(r._mapping) for r in results]

def get_all_reviews_for_brand(brand_id):
    with engine.begin() as conn:
        results = conn.execute(
            select(reviews)
            .where(reviews.c.brand_id == brand_id)
            .order_by(reviews.c.published_date.desc())
        ).fetchall()
        return [dict(r._mapping) for r in results]

# ---------- SNAPSHOTS ----------

def calculate_and_save_snapshot(
    brand_id,
    week_key,
    week_start,
    week_end,
    top_mentions=None,
    ai_summary=None,
):
    week_start_dt = datetime.fromisoformat(week_start) if isinstance(week_start, str) else week_start
    week_end_dt = datetime.fromisoformat(week_end) if isinstance(week_end, str) else week_end
    
    with engine.begin() as conn:
        # Get all reviews for the week
        review_results = conn.execute(
            select(reviews)
            .where(
                and_(
                    reviews.c.brand_id == brand_id,
                    reviews.c.published_date >= week_start_dt,
                    reviews.c.published_date <= week_end_dt
                )
            )
        ).fetchall()
        
        review_data = [dict(r._mapping) for r in review_results]
        
        if not review_data:
            return
        
        # Calculate stats
        review_count = len(review_data)
        avg_rating = sum(r['rating'] for r in review_data) / review_count
        positive = sum(1 for r in review_data if r['rating'] >= 4)
        neutral = sum(1 for r in review_data if r['rating'] == 3)
        negative = sum(1 for r in review_data if r['rating'] <= 2)
        organic = sum(1 for r in review_data if r['source'] == 'Organic')
        verified = sum(1 for r in review_data if r['is_verified'])
        invited = review_count - organic - verified
        
        # Calculate avg response time
        reviews_with_replies = [r for r in review_data if r.get('reply_message') and r.get('reply_date')]
        avg_response_time_hours = None
        
        if reviews_with_replies:
            response_times = []
            for r in reviews_with_replies:
                try:
                    diff_hours = (r['reply_date'] - r['published_date']).total_seconds() / 3600
                    if diff_hours >= 0:
                        response_times.append(diff_hours)
                except:
                    continue
            
            if response_times:
                avg_response_time_hours = sum(response_times) / len(response_times)
        
        # Insert or replace
        stmt = sqlite_insert(weekly_snapshots).values(
            brand_id=brand_id,
            week_key=week_key,
            week_start=week_start_dt,
            week_end=week_end_dt,
            review_count=review_count,
            avg_rating=avg_rating,
            positive_count=positive,
            neutral_count=neutral,
            negative_count=negative,
            organic_count=organic,
            verified_count=verified,
            invited_count=invited,
            avg_response_time_hours=avg_response_time_hours,
            top_mentions=json.dumps(top_mentions) if top_mentions else None,
            ai_summary=ai_summary,
            created_at=datetime.now(),
        )
        
        stmt = stmt.on_conflict_do_update(
            index_elements=['brand_id', 'week_key'],
            set_={
                'review_count': review_count,
                'avg_rating': avg_rating,
                'positive_count': positive,
                'neutral_count': neutral,
                'negative_count': negative,
                'organic_count': organic,
                'verified_count': verified,
                'invited_count': invited,
                'avg_response_time_hours': avg_response_time_hours,
                'top_mentions': json.dumps(top_mentions) if top_mentions else None,
                'ai_summary': ai_summary,
            }
        )
        
        conn.execute(stmt)

def get_snapshots_for_brand(brand_id, limit=8):
    with engine.begin() as conn:
        results = conn.execute(
            select(weekly_snapshots)
            .where(weekly_snapshots.c.brand_id == brand_id)
            .order_by(weekly_snapshots.c.week_start.desc())
            .limit(limit)
        ).fetchall()
        return [dict(r._mapping) for r in results]

def get_topics_by_sentiment(brand_id, week_start, week_end):
    week_start_dt = datetime.fromisoformat(week_start) if isinstance(week_start, str) else week_start
    week_end_dt = datetime.fromisoformat(week_end) if isinstance(week_end, str) else week_end
    
    with engine.begin() as conn:
        results = conn.execute(
            select(reviews.c.rating, reviews.c.topics)
            .where(
                and_(
                    reviews.c.brand_id == brand_id,
                    reviews.c.published_date >= week_start_dt,
                    reviews.c.published_date <= week_end_dt,
                    reviews.c.topics.isnot(None)
                )
            )
        ).fetchall()
        
        positive_topics = {}
        negative_topics = {}
        
        for rating, topics_json in results:
            if not topics_json:
                continue
            
            topics_list = json.loads(topics_json)
            
            for topic in topics_list:
                if rating >= 4:
                    positive_topics[topic] = positive_topics.get(topic, 0) + 1
                elif rating <= 2:
                    negative_topics[topic] = negative_topics.get(topic, 0) + 1
        
        positive_sorted = [{'topic': t, 'count': c} for t, c in sorted(positive_topics.items(), key=lambda x: x[1], reverse=True)]
        negative_sorted = [{'topic': t, 'count': c} for t, c in sorted(negative_topics.items(), key=lambda x: x[1], reverse=True)]
        
        return {
            'positive': positive_sorted,
            'negative': negative_sorted
        }