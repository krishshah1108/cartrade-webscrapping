"""
cardekho_events_scraper.py
---------------------------
Fetches dashboard data from CarDekho auctions API,
saves raw JSON (cardekho_dashboard_data.json),
and filters insurance business data (cardekho_insurance_data.json).
"""

import os
import json
import logging
import re
import urllib.parse
import requests
from datetime import datetime
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

BASE_URL = "https://auctions.cardekho.com"

# Month abbreviations mapping
MONTH_ABBR = {
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
    'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
}


def parse_date_from_title(title):
    """
    Parse date from auction title.
    Title format: "Salvage Auction Non Motor J 10Dec25"
    Date format: dMMMyy (e.g., "10Dec25" = 10 December 2025)
    
    Args:
        title (str): Auction title
        
    Returns:
        datetime.date or None: Parsed date, or None if not found/invalid
    """
    if not title:
        return None
    
    # Regex pattern: 1-2 digits, 3 letter month, 2 digit year
    # Examples: "10Dec25", "5Jan25", "25Dec25"
    pattern = r'(\d{1,2})(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)(\d{2})'
    match = re.search(pattern, title, re.IGNORECASE)
    
    if not match:
        return None
    
    try:
        day = int(match.group(1))
        month_abbr = match.group(2).lower()
        year_2digit = int(match.group(3))
        
        # Convert 2-digit year to 4-digit (assuming 20xx for years 00-99)
        year = 2000 + year_2digit if year_2digit < 100 else year_2digit
        
        # Get month number
        month = MONTH_ABBR.get(month_abbr)
        if not month:
            return None
        
        # Create date object
        return datetime(year, month, day).date()
    except (ValueError, KeyError):
        return None


def extract_headers_from_cookie(cookie):
    """
    Extract additional headers from cookie string.
    Extracts Bearer token, user IDs, and associate client from cookies.
    
    Args:
        cookie (str): Cookie string
        
    Returns:
        dict: Additional headers dictionary with authorization, userid, parentuserid, associateclient
    """
    headers = {}
    
    # Extract Bearer token from connect.sid cookie
    # Format: connect.sid=s%3AUD-B4qkcyWQQ-JmRTDmghe2EzMEn7fHb.0g20rbI...
    # The session ID (UD-B4qkcyWQQ-JmRTDmghe2EzMEn7fHb) is the Bearer token
    connect_sid_match = re.search(r'connect\.sid=([^;]+)', cookie)
    if connect_sid_match:
        connect_sid_value = urllib.parse.unquote(connect_sid_match.group(1))
        # Extract session ID (format: s:UD-B4qkcyWQQ-JmRTDmghe2EzMEn7fHb.xxxxx)
        session_match = re.search(r's:([^.]+)', connect_sid_value)
        if session_match:
            bearer_token = session_match.group(1)
            headers["Authorization"] = f"Bearer {bearer_token}"
    
    # Extract user info from globals cookie (JSON)
    globals_match = re.search(r'globals=([^;]+)', cookie)
    if globals_match:
        try:
            globals_value = urllib.parse.unquote(globals_match.group(1))
            globals_data = json.loads(globals_value)
            
            if isinstance(globals_data, dict) and "currentUser" in globals_data:
                current_user = globals_data["currentUser"]
                
                # Extract userid
                user_id = current_user.get("user_id") or current_user.get("userId")
                if user_id:
                    headers["userid"] = str(user_id)
                
                # Extract parentuserid
                parent_id = current_user.get("parent_id") or current_user.get("parentId")
                if parent_id:
                    headers["parentuserid"] = str(parent_id)
                
                # Extract associateclient
                associate_client = current_user.get("associate_client") or current_user.get("associateClient")
                if associate_client:
                    headers["associateclient"] = str(associate_client)
        except (json.JSONDecodeError, KeyError) as e:
            logging.warning(f"⚠️  Could not parse globals cookie: {e}")
    
    return headers


def fetch_cardekho_dashboard_data():
    """
    Fetches dashboard data from CarDekho auctions API using POST request
    and saves it as downloads/cardekho_dashboard_data.json.
    
    Returns:
        str: Path to saved file, or None on error
    """
    load_dotenv()
    cookie = os.getenv("CAR_DEKHO_COOKIE")
    if not cookie:
        logging.error("CAR_DEKHO_COOKIE not found in .env file")
        return None

    # Extract headers from cookie (including auth headers)
    extracted_headers = extract_headers_from_cookie(cookie)
    
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Content-Type": "application/json;charset=UTF-8",
        "Cookie": cookie,
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/142.0.0.0 Safari/537.36"
        ),
        "Referer": f"{BASE_URL}/",
        "Origin": BASE_URL,
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "Sec-CH-UA": '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
        "Sec-CH-UA-Mobile": "?0",
        "Sec-CH-UA-Platform": '"Windows"'
    }
    
    # Add any extracted auth headers (authorization, userid, parentuserid, associateclient)
    headers.update(extracted_headers)
    
    # Log headers (without sensitive cookie data)
    logging.info(f"   Headers: Authorization={'✅' if 'Authorization' in headers else '❌'}, "
                 f"userid={headers.get('userid', '❌')}, "
                 f"parentuserid={headers.get('parentuserid', '❌')}, "
                 f"associateclient={headers.get('associateclient', '❌')}")

    # POST request to getAllDashboardData endpoint
    api_url = f"{BASE_URL}/web/getAllDashboardData"
    payload = {
        "business_id": "1,2,4,5"
    }
    
    logging.info("Fetching dashboard data from CarDekho API...")
    logging.info(f"   URL: {api_url}")
    logging.info(f"   Payload: {payload}")
    
    try:
        response = requests.post(api_url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        os.makedirs("downloads", exist_ok=True)
        filename = "downloads/cardekho_dashboard_data.json"
        
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        
        logging.info(f"✅ Saved dashboard data to {filename}")
        return filename
        
    except requests.exceptions.RequestException as e:
        logging.error(f"❌ Failed to fetch dashboard data: {e}")
        return None
    except Exception as e:
        logging.exception(f"❌ Unexpected error: {e}")
        return None


def filter_insurance_business(raw_file):
    """
    Filters insurance business data from dashboard data.
    Filters by "business": "Insurance" field and date from title (SCRAPE_START_DATE).
    Title date format: "10Dec25" (dMMMyy) in title like "Salvage Auction Non Motor J 10Dec25"
    Response structure has "auction_ids" and "response_of_live" arrays.
    Saves filtered data to downloads/cardekho_insurance_data.json
    and creates downloads/cardekho_auction_paths.json for vehicle scraping.
    
    Args:
        raw_file (str): Path to cardekho_dashboard_data.json
        
    Returns:
        str: Path to filtered file, or None on error
    """
    load_dotenv()
    target_date_str = os.getenv("SCRAPE_START_DATE")
    target_date = None
    
    if target_date_str:
        try:
            target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
            logging.info(f"📅 Filtering auctions by date: {target_date_str}")
        except ValueError:
            logging.warning(f"⚠️  Invalid SCRAPE_START_DATE format: {target_date_str}. Expected YYYY-MM-DD. Date filtering will be skipped.")
    else:
        logging.warning("⚠️  SCRAPE_START_DATE not found in .env. Date filtering will be skipped.")
    
    if not raw_file or not os.path.exists(raw_file):
        logging.error(f"Dashboard data file not found: {raw_file}")
        return None
    
    try:
        with open(raw_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Check if data is empty or invalid
        if not data:
            logging.warning("⚠️  Dashboard data is empty. Cookie may have expired or API structure changed.")
            return None
        
        # Check for error response
        if isinstance(data, dict) and data.get("status") and data.get("status") != 200:
            error_msg = data.get("message", "Unknown error")
            logging.error(f"❌ API returned error: {error_msg}")
            return None
        
        # Filter for "business": "Insurance" and date from title
        insurance_data = []
        auction_paths = []
        total_insurance = 0
        date_matched = 0
        
        # The response structure has "response_of_live" array
        # Each item in response_of_live has "business" field
        if isinstance(data, dict):
            # Check for response_of_live array
            response_of_live = data.get("response_of_live") or data.get("responseOfLive") or []
            
            if isinstance(response_of_live, list):
                for item in response_of_live:
                    if isinstance(item, dict):
                        # Filter by "business": "Insurance"
                        business = item.get("business") or item.get("Business")
                        if business and str(business).lower() == "insurance":
                            total_insurance += 1
                            
                            # Filter by date from title if target_date is set
                            title = item.get("title") or item.get("auctionTitle") or item.get("name") or ""
                            if target_date:
                                title_date = parse_date_from_title(title)
                                if title_date != target_date:
                                    # Skip this auction - date doesn't match
                                    continue
                                date_matched += 1
                            
                            insurance_data.append(item)
                            
                            # Create auction path entry
                            auction_path = {
                                "auction_id": item.get("auctionId") or item.get("auction_id") or item.get("id"),
                                "title": title,
                                "slug": item.get("slug") or item.get("auctionSlug") or item.get("url") or "",
                                "vehicle_count": item.get("vehicleCount") or item.get("totalVehicles") or item.get("count") or item.get("vehicle_count") or 0,
                                "vehicles": [],
                                "gj_vehicle_count": 0
                            }
                            
                            # Extract slug from title if not present
                            if not auction_path["slug"] and auction_path["title"]:
                                # Convert title to slug format (e.g., "Gujarat PSU and Surveyor Vehicle 05Dec25" -> "Gujarat-PSU-and-Surveyor-Vehicle-05Dec25")
                                slug = auction_path["title"].replace(" ", "-").replace("/", "-")
                                auction_path["slug"] = slug
                            
                            if auction_path["auction_id"]:
                                auction_paths.append(auction_path)
            
            # Also check if data itself is a list
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        business = item.get("business") or item.get("Business")
                        if business and str(business).lower() == "insurance":
                            total_insurance += 1
                            
                            # Filter by date from title if target_date is set
                            title = item.get("title") or item.get("auctionTitle") or item.get("name") or ""
                            if target_date:
                                title_date = parse_date_from_title(title)
                                if title_date != target_date:
                                    # Skip this auction - date doesn't match
                                    continue
                                date_matched += 1
                            
                            insurance_data.append(item)
                            
                            auction_path = {
                                "auction_id": item.get("auctionId") or item.get("auction_id") or item.get("id"),
                                "title": title,
                                "slug": item.get("slug") or item.get("auctionSlug") or item.get("url") or "",
                                "vehicle_count": item.get("vehicleCount") or item.get("totalVehicles") or item.get("count") or item.get("vehicle_count") or 0,
                                "vehicles": [],
                                "gj_vehicle_count": 0
                            }
                            
                            if not auction_path["slug"] and auction_path["title"]:
                                slug = auction_path["title"].replace(" ", "-").replace("/", "-")
                                auction_path["slug"] = slug
                            
                            if auction_path["auction_id"]:
                                auction_paths.append(auction_path)
        
        # Log filtering results
        if target_date:
            logging.info(f"📊 Filtering results: {total_insurance} insurance auctions found, {date_matched} matched date {target_date_str}")
        else:
            logging.info(f"📊 Filtering results: {total_insurance} insurance auctions found (no date filter)")
        
        # Save filtered data
        if insurance_data:
            insurance_filename = "downloads/cardekho_insurance_data.json"
            os.makedirs("downloads", exist_ok=True)
            
            with open(insurance_filename, "w", encoding="utf-8") as f:
                json.dump(insurance_data, f, indent=4, ensure_ascii=False)
            
            logging.info(f"✅ Filtered {len(insurance_data)} insurance business entries to {insurance_filename}")
            
            # Create auction_paths.json for vehicle scraping
            if auction_paths:
                paths_filename = "downloads/cardekho_auction_paths.json"
                with open(paths_filename, "w", encoding="utf-8") as f:
                    json.dump(auction_paths, f, indent=4, ensure_ascii=False)
                
                logging.info(f"✅ Created auction paths file: {paths_filename} ({len(auction_paths)} auctions)")
            
            return insurance_filename
        else:
            if target_date:
                logging.warning(f"⚠️  No insurance business data found matching date {target_date_str} (business: 'Insurance')")
            else:
                logging.warning("⚠️  No insurance business data found (business: 'Insurance') in dashboard data")
            logging.info("💡 The data structure may be different. Check downloads/cardekho_dashboard_data.json")
            # Log the structure for debugging
            if isinstance(data, dict):
                logging.info(f"   Available keys in data: {list(data.keys())[:10]}")
                if "response_of_live" in data:
                    logging.info(f"   response_of_live length: {len(data.get('response_of_live', []))}")
                    if len(data.get("response_of_live", [])) > 0:
                        first_item = data["response_of_live"][0]
                        if isinstance(first_item, dict):
                            logging.info(f"   First item keys: {list(first_item.keys())[:10]}")
                            logging.info(f"   First item business: {first_item.get('business')}")
                            logging.info(f"   First item title: {first_item.get('title')}")
            return None
            
    except json.JSONDecodeError as e:
        logging.error(f"❌ Error parsing JSON: {e}")
        return None
    except Exception as e:
        logging.exception(f"❌ Unexpected error: {e}")
        return None
