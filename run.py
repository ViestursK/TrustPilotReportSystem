#!/usr/bin/env python3
"""Main orchestrator for Trustpilot monitoring"""
import sys

def show_help():
    print("""
Usage: python run.py [command]

Commands:
  onboard <domain>     Onboard new brand
  scrape               Run daily scrape
  report <domain>      Generate report for brand
  brands               List all brands
  test                 Run database tests
    """)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        show_help()
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "onboard":
        from scraper.onboarding import onboard_brand
        onboard_brand(sys.argv[2])
    elif cmd == "scrape":
        from scraper.daily_scrape import main
        main()
    elif cmd == "report":
        from report_generator.generator import generate_report
        generate_report(sys.argv[2])
    # ... etc