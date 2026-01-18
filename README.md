# Trustpilot Scraper

A Python-based scraper for collecting and analyzing Trustpilot reviews with PostgreSQL/SQLite support.

## Features

- ✓ Full historical scraping with JWT authentication
- ✓ Daily incremental updates (last 30 days)
- ✓ PostgreSQL and SQLite support
- ✓ Automatic deduplication
- ✓ Weekly analytics snapshots
- ✓ Topic tagging and sentiment analysis
- ✓ AI-generated review summaries

## Prerequisites

- Python 3.8+
- PostgreSQL 12+ (or SQLite for local testing)
- pip

## Installation

1. **Clone/Download the project**
   ```bash
   cd trustpilot_scraper
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

## Database Setup

### Option 1: SQLite (Quick Testing)

Edit `.env`:
```bash
DATABASE_URL=sqlite:///./local.db
```

### Option 2: PostgreSQL (Production)

1. **Create PostgreSQL database**
   ```bash
   # Using psql
   psql -U postgres
   CREATE DATABASE trustpilot_db;
   CREATE USER trustpilot_user WITH PASSWORD 'your_password';
   GRANT ALL PRIVILEGES ON DATABASE trustpilot_db TO trustpilot_user;
   \q
   ```

2. **Update .env**
   ```bash
   DATABASE_URL=postgresql://trustpilot_user:your_password@localhost:5432/trustpilot_db
   ```

### Option 3: PostgreSQL with Docker

```bash
# Start PostgreSQL container
docker run --name trustpilot-postgres \
  -e POSTGRES_DB=trustpilot_db \
  -e POSTGRES_USER=trustpilot_user \
  -e POSTGRES_PASSWORD=your_password \
  -p 5432:5432 \
  -d postgres:15

# Update .env
DATABASE_URL=postgresql://trustpilot_user:your_password@localhost:5432/trustpilot_db
```

## Configuration (.env)

```bash
# Database (choose one)
DATABASE_URL=sqlite:///./local.db
# DATABASE_URL=postgresql://user:pass@localhost:5432/trustpilot_db

# Brands to scrape (comma-separated Trustpilot domains)
BRANDS=trustpilot.com,revolut.com

# Max pages per daily scrape (10 recommended)
MAX_PAGES=10

# JWT token for unlimited scraping (optional, for onboarding)
# Get from browser cookies when logged into Trustpilot
JWT_ACCESS_TOKEN=
```

## Testing

Run the test suite to verify your setup:

```bash
python test_db.py
```

This will:
- ✓ Test database connection
- ✓ Create tables
- ✓ Test basic CRUD operations

Expected output:
```
✓ ALL TESTS PASSED

You can now run:
  python onboarding.py <domain>  # Onboard a new brand
  python daily_scrape.py          # Run daily scrape
```

## Usage

### 1. Onboard a New Brand

Full historical scrape (requires JWT for unlimited pages):

```bash
# With JWT (unlimited pages)
python onboarding.py trustpilot.com

# Without JWT (limited to 10 pages)
python onboarding.py trustpilot.com
```

This will:
- Scrape all available reviews
- Store in database
- Calculate weekly snapshots

### 2. Daily Scrape

Updates existing brands with new reviews:

```bash
python daily_scrape.py
```

This will:
- Check for new brands in `.env` → auto-onboard them
- Scrape last 30 days for existing brands
- Update weekly snapshots
- Tag reviews with topics

### 3. Manual Scraping

```python
import scraper

# Scrape with filters
data = scraper.scrape_brand(
    'trustpilot.com',
    max_pages=5,              # Limit pages
    use_jwt=True,             # Use authentication
    filter_last_30_days=True, # Only recent reviews
    topic_filter='refund'     # Filter by topic
)

print(f"Reviews: {len(data['reviews'])}")
print(f"Rating: {data['company']['trust_score']}")
```

## Database Schema

### Tables

**brands**
- Basic company info (name, domain, trust score)
- AI summary
- Metadata (created_at, last_scraped_at)

**reviews**
- Full review data (text, rating, author)
- Reply information
- Topics (tagged)

**weekly_snapshots**
- Aggregated weekly metrics
- Sentiment breakdown
- Response time analytics

## Getting JWT Token (for unlimited scraping)

1. Log into Trustpilot in your browser
2. Open Developer Tools (F12)
3. Go to Application/Storage → Cookies
4. Find `jwt` cookie
5. Copy the value to `.env`:
   ```bash
   JWT_ACCESS_TOKEN=eyJhbGc...
   ```

## Troubleshooting

### PostgreSQL Connection Issues

```bash
# Test connection
psql postgresql://user:pass@localhost:5432/trustpilot_db

# Common fixes:
# 1. Check PostgreSQL is running
sudo systemctl status postgresql

# 2. Verify credentials
psql -U postgres -l

# 3. Check firewall/port
sudo ufw allow 5432/tcp
```

### SQLite "locked database"

```bash
# Stop any running processes
pkill -f daily_scrape.py

# Remove lock
rm local.db-journal
```

### Import errors

```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

## Performance Tips

1. **Use PostgreSQL for production** - Better concurrent writes
2. **Enable JWT** - Unlimited pages during onboarding
3. **Adjust MAX_PAGES** - Balance speed vs completeness
4. **Run daily scrapes off-peak** - Less rate limiting

## File Structure

```
trustpilot_scraper/
├── db/
│   ├── __init__.py       # DB initialization
│   ├── engine.py         # Connection handling
│   ├── schema.py         # Table definitions
│   └── queries.py        # CRUD operations
├── scraper.py            # Core scraping logic
├── onboarding.py         # New brand setup
├── daily_scrape.py       # Daily updates
├── tag_topics.py         # Topic tagging
├── test_db.py            # Test suite
├── tp_topics.json        # Topic translations
├── requirements.txt      # Dependencies
├── .env                  # Configuration (create from .env.example)
├── .gitignore           # Git ignore rules
└── README.md            # This file
```

## Notes

- Respects rate limits (1s delay between pages)
- Stores raw data (no modifications)
- Automatic deduplication by review ID
- Supports PostgreSQL and SQLite
- Weekly snapshots for analytics

## License

MIT License - See LICENSE file
