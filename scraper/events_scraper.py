"""
events_scraper.py
-----------------
Fetches live auction events from cartradeexchange.com,
saves raw JSON (auction_data.json),
filters insurance events (catId=5) for SCRAPE_START_DATE,
saves filtered results (auction_data_filtered.json),
and extracts eventId + bidNowPath (bid_paths.json).
"""

import os
import json
import logging
from datetime import datetime
import requests
from dotenv import load_dotenv

# === Logging Setup ===
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

BASE_URL = "https://www.cartradeexchange.com/Events-Live/"


def fetch_live_events():
    """Fetches live events and saves them as downloads/auction_data.json."""
    load_dotenv()
    cookie = os.getenv("COOKIE")
    if not cookie:
        raise ValueError("COOKIE not found in .env file")

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

    payload = {
        "vue_action": "getEvents",
        "vue_token": "",
        "category": "ALL",
        "eventType": "live",
        "limit": 500,
        "offset": 0,
        "filVtype": [],
        "filLoc": []
    }

    logging.info("Sending request to fetch live events...")
    try:
        response = requests.post(BASE_URL, json=payload, headers=headers, timeout=20)
        response.raise_for_status()

        data = response.json()
        events = data.get("events", [])
        if not events:
            logging.warning("No events found or login may have expired.")
            return None

        os.makedirs("downloads", exist_ok=True)
        filename = "downloads/auction_data.json"

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(events, f, indent=4, ensure_ascii=False)

        logging.info(f"Saved {len(events)} events to {filename}")
        return filename

    except requests.exceptions.RequestException as e:
        logging.error(f"Network error: {e}")
    except ValueError as e:
        logging.error(f"Parsing error: {e}")
    except Exception as e:
        logging.exception(f"Unexpected error: {e}")

    return None


def filter_insurance_events(raw_file):
    """
    Filters only insurance events (catId=5) for SCRAPE_START_DATE from .env
    and saves them to downloads/auction_data_filtered.json.
    Also extracts [eventId, bidNowPath] into downloads/bid_paths.json.
    """
    load_dotenv()
    target_date_str = os.getenv("SCRAPE_START_DATE")

    if not target_date_str:
        raise ValueError("SCRAPE_START_DATE not found in .env file")

    try:
        target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("SCRAPE_START_DATE must be in YYYY-MM-DD format (e.g., 2025-10-14)")

    if not os.path.exists(raw_file):
        logging.error(f"Raw JSON file not found: {raw_file}")
        return None

    logging.info("Filtering events for category ID 5 and date %s", target_date)

    with open(raw_file, "r", encoding="utf-8") as f:
        events = json.load(f)

    filtered = []
    bid_path_data = []

    for ev in events:
        try:
            if ev.get("catId") != "5":
                continue

            # Parse event date string like "14-Oct-2025 14:06"
            end_str = ev.get("eventEndDateTime")
            end_date = datetime.strptime(end_str, "%d-%b-%Y %H:%M").date()

            if end_date == target_date:
                filtered.append(ev)
                event_id = ev.get("eventId")
                bid_path = ev.get("bidNowPath")
                if event_id and bid_path:
                    bid_path_data.append({
                        "eventId": str(event_id),
                        "bidNowPath": str(bid_path)
                    })
        except Exception as e:
            logging.warning(f"Skipping event due to parsing issue: {e}")
            continue

    os.makedirs("downloads", exist_ok=True)

    # Save filtered full data
    filtered_file = "downloads/auction_data_filtered.json"
    with open(filtered_file, "w", encoding="utf-8") as f:
        json.dump(filtered, f, indent=4, ensure_ascii=False)

    # Save compact bid path array
    bid_file = "downloads/bid_paths.json"
    with open(bid_file, "w", encoding="utf-8") as f:
        json.dump(bid_path_data, f, indent=4, ensure_ascii=False)

    logging.info(f"Filtered {len(filtered)} insurance events for {target_date}.")
    logging.info(f"Saved filtered data to {filtered_file}")
    logging.info(f"Saved bid path data to {bid_file}")

    return filtered_file, bid_file
