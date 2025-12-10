"""
auction_details_scraper.py
--------------------------
Loops through all bid paths, extracts pk1 from each auction page,
builds dynamic payloads, posts to /auctions-live/, and saves full responses.
Also filters data by registration number prefix ("GJ").
"""

import os
import re
import json
import time
import logging
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

BASE_PAGE_URL = "https://www.cartradeexchange.com"
POST_URL = "https://www.cartradeexchange.com/auctions-live/"


def setup_logger():
    os.makedirs("logs", exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler("logs/scraper.log", encoding="utf-8"),
            logging.StreamHandler()
        ],
        datefmt="%Y-%m-%d %H:%M:%S"
    )


def extract_pk1_from_html(html_text):
    """
    Extracts the param1 (pk1) value from the <Bidnowpopup> component.
    Example:
        <Bidnowpopup ... :param1="encoded_value" ... />
    """
    # Try regex first
    pk1_match = re.search(r':param1="([^"]+)"', html_text)
    if pk1_match:
        return pk1_match.group(1)

    # Fallback using BeautifulSoup if the HTML is rendered differently
    soup = BeautifulSoup(html_text, "html.parser")
    bid_popup = soup.find("bidnowpopup")
    if bid_popup:
        return bid_popup.get(":param1") or bid_popup.get("param1")

    return None


def fetch_auction_details():
    """
    Fetches detailed auction data for each bidNowPath,
    saves full JSON, and filtered GJ JSON.
    """
    load_dotenv()
    setup_logger()

    cookie = os.getenv("CAR_TRADE_COOKIE")
    if not cookie:
        raise ValueError("CAR_TRADE_COOKIE not found in .env")

    bid_path_file = "downloads/cartrade_event_paths.json"
    if not os.path.exists(bid_path_file):
        logging.error("Missing cartrade_event_paths.json — run previous stage first.")
        return

    with open(bid_path_file, "r", encoding="utf-8") as f:
        bid_paths = json.load(f)

    headers = {
        "Content-Type": "application/json",
        "Cookie": cookie,
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/117.0.0.0 Safari/537.36"
        ),
        "Referer": "https://www.cartradeexchange.com/Events-Live"
    }

    all_results = []
    gj_filtered = []

    total = len(bid_paths)
    logging.info(f"Found {total} auction bid paths to process...")

    for i, entry in enumerate(bid_paths, 1):
        event_id = entry.get("eventId")
        bid_path = entry.get("bidNowPath")

        if not event_id or not bid_path:
            logging.warning("Skipping invalid entry: %s", entry)
            continue

        full_url = BASE_PAGE_URL + bid_path
        logging.info(f"[{i}/{total}] Fetching HTML for event {event_id}...")

        try:
            # Step 1: Fetch auction page
            page_resp = requests.get(full_url, headers=headers, timeout=20)
            page_resp.raise_for_status()

            # Step 2: Extract pk1 from page HTML
            pk1 = extract_pk1_from_html(page_resp.text)
            if not pk1:
                logging.warning(f"Could not extract pk1 for event {event_id}")
                continue

            # Step 3: Build dynamic payload
            pk2 = "10" + str(event_id)
            payload = {
                "vue_action": "getAuctionEvents_new",
                "pk1": pk1,
                "pk2": pk2,
                "show": "active",
                "vue_event_id": event_id
            }

            logging.info(f"Posting auction-live request for event {event_id}...")
            post_resp = requests.post(POST_URL, json=payload, headers=headers, timeout=25)
            post_resp.raise_for_status()

            data = post_resp.json()

            # Determine the number of auction items
            auction_list = data.get("auctionList", [])
            auction_count = len(auction_list)

            logging.info(f"✅ Success for event {event_id} | Received {auction_count} auction items")

            all_results.append({
                "eventId": event_id,
                "pk1": pk1,
                "pk2": pk2,
                "auctionCount": auction_count,
                "response": data
            })

            # Step 4: Filter for GJ registration numbers
            for auction in auction_list:
                reg_no = auction.get("registrationNumber", "")
                if reg_no.startswith("GJ"):
                    gj_filtered.append(auction)

            # Be polite with requests
            time.sleep(2)

        except requests.exceptions.RequestException as e:
            logging.error(f"Network error or cookie expired for {event_id}: {e}")
        except Exception as e:
            logging.exception(f"Unexpected error for {event_id}: {e}")

    # Save outputs
    os.makedirs("downloads", exist_ok=True)

    all_file = "downloads/cartrade_auction_details_full.json"
    with open(all_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=4, ensure_ascii=False)

    gj_file = "downloads/cartrade_vehicles_gujarat.json"
    with open(gj_file, "w", encoding="utf-8") as f:
        json.dump(gj_filtered, f, indent=4, ensure_ascii=False)

    logging.info(f"💾 Saved {len(all_results)} full auction responses → {all_file}")
    logging.info(f"💾 Saved {len(gj_filtered)} filtered GJ auctions → {gj_file}")
    logging.info("🎯 Auction detail scraping completed successfully.")
