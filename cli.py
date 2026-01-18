#!/usr/bin/env python3
"""
CLI tool to manage brands and view weekly snapshots
"""

import sys
import json
from db.engine import get_engine
from db.schema import brands, reviews, weekly_snapshots
from db import queries as db
from sqlalchemy import delete, select
from dotenv import load_dotenv

load_dotenv()


def list_brands():
    """List all brands in database"""
    engine = get_engine()
    with engine.begin() as conn:
        result = conn.execute(
            select(brands.c.id, brands.c.domain, brands.c.brand_name, brands.c.total_reviews)
            .order_by(brands.c.id)
        )

        print("\n" + "="*70)
        print("BRANDS IN DATABASE")
        print("="*70)
        print(f"{'ID':<5} {'Domain':<30} {'Name':<20} {'Reviews':<10}")
        print("-"*70)

        for row in result:
            print(f"{row[0]:<5} {row[1]:<30} {row[2]:<20} {row[3]:<10}")

        print("="*70 + "\n")


def remove_brand(domain):
    """Remove a brand and all its data"""
    engine = get_engine()

    with engine.begin() as conn:
        result = conn.execute(
            select(brands.c.id, brands.c.brand_name).where(brands.c.domain == domain)
        ).first()

        if not result:
            print(f"\n❌ Brand '{domain}' not found in database\n")
            return

        brand_id, brand_name = result[0], result[1]

        # Confirm deletion
        print(f"\n⚠️  WARNING: You are about to delete:")
        print(f"   Brand: {brand_name}")
        print(f"   Domain: {domain}")
        print(f"   ID: {brand_id}")
        print("\n   This will also delete:")
        print("   - All reviews for this brand")
        print("   - All weekly snapshots")

        confirm = input("\n   Type 'yes' to confirm deletion: ")
        if confirm.lower() != 'yes':
            print("\n✅ Deletion cancelled\n")
            return

        print("\n   Deleting data...")
        conn.execute(delete(weekly_snapshots).where(weekly_snapshots.c.brand_id == brand_id))
        print("   ✓ Deleted weekly snapshots")
        conn.execute(delete(reviews).where(reviews.c.brand_id == brand_id))
        print("   ✓ Deleted reviews")
        conn.execute(delete(brands).where(brands.c.id == brand_id))
        print("   ✓ Deleted brand")

        print(f"\n✅ Successfully removed '{domain}' from database\n")


def show_snapshots(domain, limit=8, pretty=True):
    """Show weekly snapshots for a brand in JSON format"""
    brand_id = db.get_brand_id(domain)
    if not brand_id:
        print(f"\n❌ Brand '{domain}' not found in database\n")
        return

    snapshots = db.get_snapshots_for_brand(brand_id, limit=limit)

    if not snapshots:
        print(f"\nℹ️ No snapshots found for '{domain}'\n")
        return

    if pretty:
        print(json.dumps(snapshots, indent=4, default=str))
    else:
        print(json.dumps(snapshots, default=str))


def show_help():
    print("""
Usage: python manage_brands.py [command] [domain]

Commands:
  list                 List all brands in database
  remove <domain>      Remove a brand and all its data
  snapshots <domain>   Show weekly snapshots for a brand (pretty JSON)
  help                 Show this help message

Examples:
  python manage_brands.py list
  python manage_brands.py remove test-company.com
  python manage_brands.py snapshots ketogo.app
""")


def main():
    if len(sys.argv) < 2:
        show_help()
        return 1

    command = sys.argv[1].lower()

    if command == 'list':
        list_brands()
    elif command == 'remove':
        if len(sys.argv) < 3:
            print("\n❌ Error: Please provide a domain to remove\n")
            return 1
        remove_brand(sys.argv[2])
    elif command == 'snapshots':
        if len(sys.argv) < 3:
            print("\n❌ Error: Please provide a domain to view snapshots\n")
            return 1
        show_snapshots(sys.argv[2])
    elif command == 'help':
        show_help()
    else:
        print(f"\n❌ Unknown command: {command}\n")
        show_help()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
