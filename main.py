"""
main.py — now runs the full scrape pipeline:
CarTrade:
1. Fetch all live events
2. Filter insurance events
3. Fetch auction details for filtered ones
4. Download GJ images and metadata

CarDekho:
1. Fetch dashboard data
2. Filter insurance business data
"""

import logging
from scraper.events_scraper import fetch_live_events, filter_insurance_events
from scraper.auction_details_scraper import fetch_auction_details
from scraper.download_gj_images import download_gj_images
from scraper.download_gj_images import create_date_zip
from scraper.cardekho_events_scraper import fetch_cardekho_dashboard_data, filter_insurance_business
from scraper.cardekho_vehicle_scraper import update_auction_paths_with_vehicles
from dotenv import load_dotenv
import os

def main():
    load_dotenv()
    name = os.getenv("SCRAPER_NAME", "User")
    date = os.getenv("SCRAPE_START_DATE", "Unknown")

    logging.info("=" * 60)
    logging.info("🚀 Web Scraping Pipeline Starting")
    logging.info("=" * 60)
    logging.info("👋 Hello %s, scraping started on %s", name, date)

    # ========== CarTrade Scraping ==========
    # COMMENTED OUT FOR TESTING - CarDekho only
    # Uncomment below to enable CarTrade scraping
    """
    logging.info("")
    logging.info("=" * 60)
    logging.info("📊 CARTRADE SCRAPING")
    logging.info("=" * 60)

    raw_file = fetch_live_events()
    if not raw_file:
        logging.error("❌ Failed to fetch main events.")
        return False

    filtered_file, bid_file = filter_insurance_events(raw_file)
    if not bid_file:
        logging.error("❌ No bid paths to process.")
        return False

    logging.info("Starting detailed auction scraping...")
    fetch_auction_details()
    # After fetching auction details
    download_gj_images()
    # After images are downloaded, create a zip archive of the date folder
    try:
        archive = create_date_zip(None)
        if archive:
            logging.info(f"✅ Created archive: {archive}")
        else:
            logging.warning("⚠️  create_date_zip did not create an archive")
    except Exception as e:
        logging.exception(f"💥 Error while creating date archive: {e}")
    
    logging.info("✅ CarTrade scraping completed successfully!")
    """

    # ========== CarDekho Scraping ==========
    logging.info("")
    logging.info("=" * 60)
    logging.info("📊 CARDEKHO SCRAPING")
    logging.info("=" * 60)

    cardekho_raw_file = fetch_cardekho_dashboard_data()
    if not cardekho_raw_file:
        logging.error("❌ Failed to fetch CarDekho dashboard data.")
        return False

    cardekho_filtered_file = filter_insurance_business(cardekho_raw_file)
    if not cardekho_filtered_file:
        logging.warning("⚠️  No insurance business data found or filtering failed.")
        # Don't return False here, as this might be expected if structure is different
    else:
        logging.info("✅ CarDekho filtering completed successfully!")
    
    # Step 3a: Extract vehicle links from auction pages
    if cardekho_filtered_file:
        if not update_auction_paths_with_vehicles():
            logging.warning("⚠️  Vehicle link extraction had errors, but continuing...")
        else:
            logging.info("✅ CarDekho vehicle link extraction completed successfully!")

    logging.info("")
    logging.info("=" * 60)
    logging.info("🎯 All steps completed successfully!")
    logging.info("=" * 60)
    
    return True

if __name__ == "__main__":
    main()
