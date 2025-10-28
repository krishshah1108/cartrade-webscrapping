"""
main.py — now runs the full scrape pipeline:
1. Fetch all live events
2. Filter insurance events
3. Fetch auction details for filtered ones
"""

import logging
from scraper.events_scraper import fetch_live_events, filter_insurance_events
from scraper.auction_details_scraper import fetch_auction_details
from scraper.download_gj_images import download_gj_images
from scraper.download_gj_images import create_date_zip
from dotenv import load_dotenv
import os

def main():
    load_dotenv()
    name = os.getenv("SCRAPER_NAME", "User")
    date = os.getenv("SCRAPE_START_DATE", "Unknown")

    logging.info("👋 Hello %s, scraping started on %s", name, date)

    raw_file = fetch_live_events()
    if not raw_file:
        return logging.error("Failed to fetch main events.")

    filtered_file, bid_file = filter_insurance_events(raw_file)
    if not bid_file:
        return logging.error("No bid paths to process.")

    logging.info("Starting detailed auction scraping...")
    fetch_auction_details()
    # After fetching auction details
    download_gj_images()
    # After images are downloaded, create a zip archive of the date folder
    try:
        archive = create_date_zip(None)
        if archive:
            logging.info(f"Created archive: {archive}")
        else:
            logging.warning("create_date_zip did not create an archive")
    except Exception as e:
        logging.exception(f"Error while creating date archive: {e}")
    logging.info("Starting download of GJ vehicle images & metadata...")
    logging.info("🎯 All steps completed successfully.")

if __name__ == "__main__":
    main()
