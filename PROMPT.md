# Complete Project Generation Prompt

## System Role

You are a senior full-stack Python developer with 10+ years of experience in web scraping, API integration, browser automation, and data processing. You specialize in building robust, production-ready scraping solutions with comprehensive error handling, retry mechanisms, and detailed logging.

## Project Overview

Create a comprehensive Python-based web scraping solution that extracts vehicle auction data from two major Indian auction platforms: **CarTrade Exchange** (cartradeexchange.com) and **CarDekho Auctions** (auctions.cardekho.com). The project must filter for insurance-related auctions, extract vehicle details, download images, and organize all data in a structured format.

---

## Project Requirements

### Core Functionality

1. **CarTrade Exchange Scraping**:

   - Fetch live auction events via POST API
   - Filter by category ID 5 (Insurance) and target date
   - Extract vehicle details for Gujarat-registered vehicles (GJ prefix)
   - Download vehicle images and create metadata files

2. **CarDekho Auctions Scraping**:

   - Fetch dashboard data via POST API with authentication
   - Filter by "Insurance" business type and date from title
   - Extract vehicle details using Playwright (handles AngularJS SPA)
   - Filter vehicles: Gujarat (GJ) registration + "With Papers" RC status
   - Extract vehicle images from galleries
   - Implement smart retry logic that preserves successful vehicles
   - Create "complete" versions of partial auctions

3. **Image Download & Metadata**:

   - Download images concurrently using ThreadPoolExecutor
   - Create human-readable metadata.txt files
   - Skip already processed vehicles
   - Randomly select images (up to IMAGE_COUNT from .env)

4. **Zip Archive Creation**:
   - Create zip archive of all downloaded data at the end

---

## Project Structure

```
cartrade-webscrapping/
├── main.py                          # Main entry point
├── requirements.txt                 # Python dependencies
├── .env                            # Environment variables (not in git)
├── .gitignore                      # Git ignore file
├── README.md                       # Project documentation
├── PROMPT.md                       # This file
│
├── scraper/                        # Scraping modules
│   ├── events_scraper.py          # CarTrade: Fetch and filter events
│   ├── auction_details_scraper.py # CarTrade: Fetch auction details
│   ├── download_gj_images.py      # CarTrade: Download images and metadata
│   ├── cardekho_events_scraper.py # CarDekho: Fetch and filter dashboard data
│   └── cardekho_vehicle_scraper.py # CarDekho: Extract vehicle data and images
│
├── downloads/                      # Output directory (created automatically)
│   ├── cartrade_events_raw.json
│   ├── cartrade_events_insurance.json
│   ├── cartrade_event_paths.json
│   ├── cartrade_auction_details_full.json
│   ├── cartrade_vehicles_gujarat.json
│   ├── cardekho_dashboard_data.json
│   ├── cardekho_insurance_data.json
│   ├── cardekho_auction_paths.json
│   ├── cardekho_failed_auctions.json
│   └── <SCRAPE_START_DATE>/       # Date-based folders
│       └── <REG_NO>/
│           ├── images/
│           └── metadata.txt
│
└── logs/                           # Log files (created automatically)
    └── scraper.log
```

---

## Environment Variables (.env)

Create a `.env` file with the following variables:

```properties
SCRAPER_NAME=Your Name
SCRAPE_START_DATE=2025-12-10
CAR_TRADE_COOKIE=<paste your CarTrade cookie here>
CAR_DEKHO_COOKIE=<paste your CarDekho cookie here>
IMAGE_COUNT=30
```

**Variable Details:**

- `SCRAPER_NAME`: Optional, friendly name for logging
- `SCRAPE_START_DATE`: Required, format YYYY-MM-DD (e.g., "2025-12-10")
- `CAR_TRADE_COOKIE`: Required for CarTrade scraping, full cookie string from browser
- `CAR_DEKHO_COOKIE`: Required for CarDekho scraping, includes `connect.sid` and `globals` cookies
- `IMAGE_COUNT`: Optional, default 30, max images to download per vehicle

---

## Dependencies (requirements.txt)

```txt
python-dotenv>=1.0.0
requests>=2.31.0
beautifulsoup4>=4.12.2
playwright>=1.40.0
```

**Additional Setup:**

- After installing dependencies, run: `playwright install chromium`

---

## .gitignore

Create a `.gitignore` file with:

```
downloads/
logs/
.env
*.pyc
__pycache__/
```

---

## Constants and Base URLs

**CarTrade Exchange:**

- `BASE_URL = "https://www.cartradeexchange.com/Events-Live/"`
- `BASE_PAGE_URL = "https://www.cartradeexchange.com"`
- `POST_URL = "https://www.cartradeexchange.com/auctions-live/"`

**CarDekho Auctions:**

- `BASE_URL = "https://auctions.cardekho.com"`
- API Endpoint: `https://auctions.cardekho.com/web/getAllDashboardData`

---

## File-by-File Implementation Details

### 1. main.py

**Purpose**: Orchestrates the complete scraping pipeline

**Structure:**

```python
"""
main.py — Full scraping pipeline:
CarTrade:
1. Fetch all live events
2. Filter insurance events
3. Fetch auction details for filtered ones
4. Download GJ images and metadata

CarDekho:
1. Fetch dashboard data
2. Filter insurance business data
3. Extract vehicle data and images
4. Download images and create metadata

Both:
5. Create zip archive
"""

import logging
from scraper.events_scraper import fetch_live_events, filter_insurance_events
from scraper.auction_details_scraper import fetch_auction_details
from scraper.download_gj_images import download_gj_images, create_date_zip
from scraper.cardekho_events_scraper import fetch_cardekho_dashboard_data, filter_insurance_business
from scraper.cardekho_vehicle_scraper import update_auction_paths_with_vehicles, download_cardekho_images
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
    download_gj_images()

    logging.info("✅ CarTrade scraping completed successfully!")

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
    else:
        logging.info("✅ CarDekho filtering completed successfully!")

    # Step 3: Extract vehicle links from auction pages
    if cardekho_filtered_file:
        if not update_auction_paths_with_vehicles():
            logging.warning("⚠️  Vehicle link extraction had errors, but continuing...")
        else:
            logging.info("✅ CarDekho vehicle link extraction completed successfully!")

    # Step 4: Download images and create metadata
    logging.info("")
    logging.info("=" * 60)
    logging.info("📥 DOWNLOADING CARDEKHO IMAGES AND CREATING METADATA")
    logging.info("=" * 60)

    if not download_cardekho_images():
        logging.warning("⚠️  CarDekho image download had errors, but continuing...")
    else:
        logging.info("✅ CarDekho image download completed successfully!")

    # Step 5: Create zip archive (for both CarTrade and CarDekho)
    logging.info("")
    logging.info("=" * 60)
    logging.info("📦 CREATING ZIP ARCHIVE")
    logging.info("=" * 60)

    try:
        archive = create_date_zip(None)
        if archive:
            logging.info(f"✅ Created archive: {archive}")
        else:
            logging.warning("⚠️  create_date_zip did not create an archive")
    except Exception as e:
        logging.exception(f"💥 Error while creating date archive: {e}")

    logging.info("")
    logging.info("=" * 60)
    logging.info("🎯 All steps completed successfully!")
    logging.info("=" * 60)

    return True

if __name__ == "__main__":
    main()
```

**Key Points:**

- Sets up logging first
- Executes CarTrade pipeline, then CarDekho pipeline
- Creates zip archive at the end
- Handles errors gracefully without stopping entire pipeline

---

### 2. scraper/events_scraper.py

**Purpose**: Fetch and filter CarTrade Exchange events

**Functions:**

#### `fetch_live_events()`

- **URL**: `https://www.cartradeexchange.com/Events-Live/`
- **Method**: POST
- **Headers**:
  - `Content-Type: application/json`
  - `Cookie: <CAR_TRADE_COOKIE>`
  - `User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36`
  - `Referer: https://www.cartradeexchange.com/Events-Live`
- **Payload**:
  ```json
  {
    "vue_action": "getEvents",
    "vue_token": "",
    "category": "ALL",
    "eventType": "live",
    "limit": 500,
    "offset": 0,
    "filVtype": [],
    "filLoc": []
  }
  ```
- **Response**: JSON with `events` array
- **Output**: Saves to `downloads/cartrade_events_raw.json`
- **Returns**: File path string or None

#### `filter_insurance_events(raw_file)`

- **Input**: Path to `cartrade_events_raw.json`
- **Filter Criteria**:
  - `catId == "5"` (Insurance category)
  - `eventEndDateTime` matches `SCRAPE_START_DATE` from .env
  - Date format in API: `"14-Oct-2025 14:06"` → parse to date
- **Output Files**:
  - `downloads/cartrade_events_insurance.json` - Full filtered event data
  - `downloads/cartrade_event_paths.json` - Array of `{eventId, bidNowPath}`
- **Returns**: Tuple `(filtered_file_path, bid_file_path)` or `(None, None)`

**Logging Format:**

- Use standard logging with timestamps
- Format: `"%(asctime)s | %(levelname)s | %(message)s"`
- Date format: `"%Y-%m-%d %H:%M:%S"`

---

### 3. scraper/auction_details_scraper.py

**Purpose**: Fetch detailed auction data for each event

**Functions:**

#### `extract_pk1_from_html(html_text)`

- Extracts `pk1` parameter from `<Bidnowpopup>` component
- **Regex Pattern**: `:param1="([^"]+)"`
- Search for `<Bidnowpopup>` tag and extract `:param1` attribute value
- Returns: pk1 string or None

#### `fetch_auction_details()`

- **Input**: Reads `downloads/cartrade_event_paths.json`
- **Process**:
  1. For each `{eventId, bidNowPath}`:
     - Fetch auction page: `BASE_PAGE_URL + bidNowPath`
     - Extract `pk1` from HTML
     - Build payload: `{vue_action: "getAuctionEvents_new", pk1: <extracted>, pk2: "10" + eventId, show: "active", vue_event_id: eventId}`
     - POST to `https://www.cartradeexchange.com/auctions-live/`
     - Extract `auctionList` from response
     - Filter vehicles with registration starting with "GJ"
- **Output Files**:
  - `downloads/cartrade_auction_details_full.json` - Full responses with metadata
  - `downloads/cartrade_vehicles_gujarat.json` - Only GJ vehicles
- **Logging**: Show progress `[X/Y]` for each event
- **Delays**: 2 seconds between requests

---

### 4. scraper/download_gj_images.py

**Purpose**: Download images and create metadata for CarTrade vehicles

**Functions:**

#### `download_image(url, save_path, reg_no)`

- Downloads single image using requests
- Timeout: 15 seconds
- Returns: `True` on success, `False` on failure
- **No logging on success** (for speed)
- **Logs only failures**: `logging.error(f"   ❌ Failed to download [{reg_no}]: {str(e)[:50]}")`

#### `extract_js_variables(html_content)`

- Extracts JavaScript variables from HTML using regex patterns
- **Exact Regex Patterns Dictionary:**
  ```python
  patterns = {
      'power_steering': r'auction_pw_steering:"([^"]*)"',
      'fuel_type': r'auction_fuel:"([^"]*)"',
      'state': r'auction_state:"([^"]*)"',
      'city': r'auction_city:"([^"]*)"',
      'yard_location': r'auction_yard_location:"([^"]*)"',
      'yard_name': r'auction_yard_name:"([^"]*)"',
      'payment_terms': r'auction_payment_terms:"([^"]*)"',
      'rc_book_available': r'auction_rcbook_available:"([^"]*)"',
      'seller_reference': r'auction_seller_reference:"([^"]*)"',
      'cte_contact_person': r'auction_cte_contact_person_name:"([^"]*)"',
      'cte_contact_phone': r'auction_cte_contact_person_phone:"([^"]*)"',
      'sunroof': r'auction_sunroof:"([^"]*)"',
      'odometer': r'auction_odometer:"([^"]*)"',
      'color': r'auction_color:"([^"]*)"',
      'shape': r'auction_shape:"([^"]*)"',
      'ageing': r'auction_ageing:"([^"]*)"',
      'delivery_dates': r'auction_delivery_dates:"([^"]*)"',
      'fuel_endorsement': r'auction_fuel_endors:"([^"]*)"',
      'registration_type': r'auction_regtype:"([^"]*)"',
      'registration_number': r'auction_regno:"([^"]*)"',
      'manufacturing_year': r'auction_mfgymd:"([^"]*)"',
      'registration_date': r'auction_reg_date:"([^"]*)"',
      'owner_count': r'auction_owner:"([^"]*)"',
      'insurance_type': r'auction_insurance:"([^"]*)"',
      'insurance_expiry': r'auction_ins_exp:"([^"]*)"',
      'claim_bonus': r'auction_claim_bonus:"([^"]*)"',
      'claim_percent': r'auction_claim_percent:"([^"]*)"',
      'hypothecation': r'auction_hypo:"([^"]*)"',
      'climate_control': r'auction_climate:"([^"]*)"',
      'door_count': r'auction_doorcount:"([^"]*)"',
      'gearbox': r'auction_gearbox:"([^"]*)"',
      'hypo_amount': r'auction_hypo_amount:"([^"]*)"',
      'bank_name': r'auction_bank_name:"([^"]*)"',
      'loan_paid_off': r'auction_loan_off:"([^"]*)"',
      'noc_available': r'auction_noc:"([^"]*)"',
      'chassis_number': r'auction_chass_no:"([^"]*)"',
      'engine_number': r'auction_eng_no:"([^"]*)"',
      'vehicle_condition': r'vehicle_condition:"([^"]*)"',
      'fitness_validity': r'fitness_validity:"([^"]*)"',
      'client_contact_person': r'client_contact_person_name:"([^"]*)"',
      'client_contact_mobile': r'client_contact_person_mobile:"([^"]*)"',
      'buyer_fee_note': r'buyer_fee_note:"([^"]*)"',
      'rto_fine': r'rto_fine:"([^"]*)"',
      'repo_date': r'repo_date:"([^"]*)"',
      'parking_days': r'parking_days:"([^"]*)"',
      'parking_rate': r'parking_rate:"([^"]*)"',
      'parking_charges_approx': r'parking_charges_approx:"([^"]*)"',
  }
  ```
- Returns: Dictionary of extracted variables (only non-empty values)

#### `fetch_detail_page(detail_link, cookie)`

- Fetches detail page HTML
- URL: `https://www.cartradeexchange.com` + `detailLink`
- Returns: HTML string or None

#### `download_gj_images()`

- **Input**: Reads `downloads/cartrade_vehicles_gujarat.json`
- **Process**:
  1. For each vehicle:
     - Sanitize registration number (remove special chars, uppercase)
     - Create folder: `downloads/<SCRAPE_START_DATE>/<REG_NO>/images/`
     - Skip if folder exists with images and metadata.txt
     - Get `imageUrls` array from vehicle data
     - Randomly select up to `IMAGE_COUNT` images (or all if fewer)
     - Download images concurrently using ThreadPoolExecutor (10 workers)
     - Fetch detail page if cookie available and extract JS variables
     - Create `metadata.txt` with vehicle details
- **Logging Format**:

  ```
  Processing X GJ vehicles for image download & metadata.

     [1/X] GJ05JQ3039: Downloading 30/45 images
     [1/X] GJ05JQ3039: Downloaded 30 images
  ```

- **Summary** (at end):
  ```
  CARTRADE IMAGE DOWNLOAD SUMMARY
     • Processed: X/Y vehicles
     • Images downloaded: Z
     • Metadata enhanced: W vehicles
  ```
- **ThreadPoolExecutor**: Use exactly 10 workers for concurrent downloads
- **Timeout**: 15 seconds per image download
- **Error Handling**: Log failures but continue processing other images
- **Image Selection**: Use `random.sample()` to randomly select up to `IMAGE_COUNT` images from available images
- **Skip Logic**: Check if folder exists AND contains `images/` subfolder with files AND `metadata.txt` exists

#### `create_date_zip(date_folder)`

- Creates zip archive of `downloads/<SCRAPE_START_DATE>/` folder
- Output: `downloads/<SCRAPE_START_DATE>.zip`
- Returns: Archive path or None

---

### 5. scraper/cardekho_events_scraper.py

**Purpose**: Fetch and filter CarDekho dashboard data

**Functions:**

#### `parse_date_from_title(title)`

- Parses date from auction title
- Format: `dMMMyy` (e.g., "10Dec25" = December 10, 2025)
- **Regex Pattern**: `(\d{1,2})(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)(\d{2})`
- **Month Mapping**: `{'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6, 'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12}`
- Convert 2-digit year to 4-digit (assume 2000-2099 range)
- Returns: `datetime.date` or None

#### `extract_headers_from_cookie(cookie)`

- Extracts authentication headers from cookie string
- **Bearer Token**: From `connect.sid` cookie
  - **Regex Pattern**: `connect\.sid=s%3A([^.]+)` or `connect\.sid=s:([^.]+)`
  - Extract session ID (URL decode if needed: `urllib.parse.unquote`)
  - Set header: `Authorization: Bearer <SESSION_ID>`
- **User Info**: From `globals` cookie (JSON)
  - **Regex Pattern**: `globals=([^;]+)`
  - URL decode: `urllib.parse.unquote(globals_match.group(1))`
  - Parse JSON: `json.loads(globals_value)`
  - Extract from `currentUser` dict:
    - `userid` or `userId` → `userid` header (convert to string)
    - `parent_id` or `parentId` → `parentuserid` header (convert to string)
    - `associate_client` or `associateClient` → `associateclient` header (convert to string)
- Handle JSON decode errors gracefully (log warning, continue)
- Returns: Dictionary with headers (may be empty if extraction fails)

#### `fetch_cardekho_dashboard_data()`

- **URL**: `https://auctions.cardekho.com/web/getAllDashboardData`
- **Method**: POST
- **Headers**:
  - `Accept: application/json, text/plain, */*`
  - `Content-Type: application/json;charset=UTF-8`
  - `Cookie: <CAR_DEKHO_COOKIE>`
  - `User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36`
  - Plus extracted headers: `Authorization`, `userid`, `parentuserid`, `associateclient`
- **Payload**:
  ```json
  {
    "business_id": "1,2,4,5"
  }
  ```
- **Output**: Saves to `downloads/cardekho_dashboard_data.json`
- **Returns**: File path or None

#### `filter_insurance_business(raw_file)`

- **Input**: Path to `cardekho_dashboard_data.json`
- **Response Structure**:
  - Has `auction_ids` array
  - Has `response_of_live` array (contains auction objects)
- **Filter Criteria**:
  1. Filter `response_of_live` array where `"business": "Insurance"`
  2. Parse date from `title` field using `parse_date_from_title()`
  3. Match against `SCRAPE_START_DATE` from .env
- **Output Files**:
  - `downloads/cardekho_insurance_data.json` - Filtered insurance data
  - `downloads/cardekho_auction_paths.json` - Array of auction objects with:
    ```json
    {
      "auction_id": "177730",
      "title": "Exclusive Bajaj Salvage Auction 10Dec25",
      "slug": "Exclusive-Bajaj-Salvage-Auction-10Dec25",
      "vehicle_count": 22
    }
    ```
- **Returns**: Path to `cardekho_auction_paths.json` or None

---

### 6. scraper/cardekho_vehicle_scraper.py

**Purpose**: Extract vehicle data and images from CarDekho auctions

**Functions:**

#### `get_headers(cookie)`

- Builds request headers with authentication
- Uses `extract_headers_from_cookie()` to get auth headers
- Returns: Headers dictionary

#### `fetch_auction_detail_page(slug, auction_id, cookie, max_retries=3)`

- **URL**: `https://auctions.cardekho.com/#/auctionDetail/<slug>`
- **Method**: Playwright (handles AngularJS SPA)
- **Process**:
  1. Launch Chromium browser (headless=True)
  2. Create context with User-Agent: `"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"`
  3. Parse cookies from cookie string (split by `;`, extract name=value pairs)
  4. Add cookies to context: `{'name': name, 'value': value, 'domain': 'auctions.cardekho.com', 'path': '/'}`
  5. Navigate to URL with `wait_until='domcontentloaded'`, timeout=90000 (90 seconds)
  6. Wait 3 seconds: `page.wait_for_timeout(3000)`
  7. Wait for selector: `tr[id^="auction_item_"]` (timeout 20000 = 20 seconds)
  8. Scroll page: `page.evaluate("window.scrollTo(0, document.body.scrollHeight)")`
  9. Wait for `networkidle` state: `page.wait_for_load_state('networkidle')`
  10. Extract HTML content: `page.content()`
  11. Close browser
- **Retry Logic**: 3 attempts with exponential backoff (sleep 2^attempt seconds: 2s, 4s, 8s)
- **Error Handling**: Catch `PlaywrightTimeoutError` and general exceptions, log with attempt number
- **Returns**: HTML string or None

#### `fetch_vehicle_detail_page(vehicle_link, vid, item_id, cookie, max_retries=3, auction_idx=None, total_auctions=None, vehicle_idx=None, total_vehicles=None, reg=None)`

- **URL**: `https://auctions.cardekho.com#/auction/vehicleDetail/<vid>/<item_id>`
- **Method**: Playwright
- **Process**:
  1. Navigate to vehicle detail page
  2. Wait for content (15 seconds timeout)
  3. Try to click "View Photos" link or main image to open gallery
  4. Wait for gallery to load (5 seconds)
  5. Extract HTML
  6. Extract image URLs using `extract_image_urls_from_html()`
- **Logging**: Include `[Auction: X/Y] | [Vehicle: A/B]` context if provided
- **Returns**: Tuple `(HTML, list_of_image_urls)` or `(None, [])`

#### `extract_image_urls_from_html(html_content)`

- Extracts image URLs using multiple methods (in order):
  1. `data-src-pop` attribute (gallery full-size)
  2. `data-src` attribute
  3. `data-thumb` attribute
  4. `img src` attribute (fallback)
- **Filter**: Only URLs containing `auctionscdn.cardekho.com/auctionuploads/`
- **Clean**: Remove query parameters (split on `?`)
- **Deduplicate**: Use set to avoid duplicates
- **Sort**: Return sorted list
- Returns: List of image URLs

#### `extract_vehicle_links_from_auction_html(html_content)`

- Extracts vehicle data from auction listing page
- **Method 1**: Find `tr` elements with `id="auction_item_XXXXX"`
  - Extract `item_id` from ID
  - Find `a` tag with `href="#/auction/vehicleDetail/<vid>/<item_id>"`
  - Extract `vid` and `item_id`
  - Extract vehicle details from `li` elements:
    - `title="Registration Number"` → `registration_number`
    - `title="Mfg Year"` → `manufacturing_year` (extract only 4-digit year, remove month names and newlines)
    - `title="Location"` → `location`
    - `title="RC Available"` → `rc_status`
    - `title="Transmission"` → `transmission`
    - `title="Ownership"` → `ownership`
    - `title="Fuel Type"` → `fuel_type`
    - `title="Yard Name"` → `yard_name`
    - `title="Yard Location"` → `yard_location`
- **Method 2**: Fallback - find all `a` tags with `href="#/auction/vehicleDetail/..."`
- Returns: List of vehicle dictionaries

#### `update_auction_paths_with_vehicles()`

- **Input**: Reads `downloads/cardekho_auction_paths.json`
- **Error Handling**: If file doesn't exist or is empty, log error and return False
- **Process**:
  1. For each auction:
     - Fetch auction detail page using Playwright
     - Extract vehicle links
     - Filter: Registration starts with "GJ" AND RC status contains "With Papers" (case-insensitive)
     - For each filtered vehicle:
       - Fetch vehicle detail page
       - Extract image URLs (3 retry attempts)
       - Append `vehicleimages` array to vehicle dict
     - Calculate status metrics
     - Update auction with vehicles and status
     - **Incremental Saving**: Save JSON file immediately after each auction
  2. Retry timeout auctions (3 attempts):
     - Reload auction page if expected ≠ loaded
     - Extract and process vehicles
  3. Smart retry for partial/failed auctions (3 attempts):
     - Identify successful vehicles (have both data AND images)
     - Only retry failed vehicles
     - Preserve successful vehicles
     - Only reload if expected ≠ loaded
  4. Create complete versions:
     - For partial auctions, create "complete" version with only vehicles that have both data AND images
     - Append to end of auctions list
- **Status Calculation**:
  - `complete`: Expected == Loaded AND all filtered vehicles have images
  - `partial`: Filtered vehicles found but not all have images OR expected ≠ loaded
  - `timeout`: Expected > 0 but Loaded == 0
  - `failed`: Failed to fetch auction page
  - `no_match`: No vehicles match filters
- **Summary Format**: `"Status: <STATUS> - Expected: X, Loaded: Y, Filtered: Z, With Data: A, With Images: B"`
- **Logging Format**:

  ```
  EXTRACTING CARDEKHO VEHICLE DATA
     • Filter: Gujarat (GJ) registration + 'With Papers' RC status

     • Processing X auction(s)

     [Auction: 1/X] Auction Title (ID: 12345)
        Expected: 22 vehicles
        [Auction: 1/X] 🌐 Loading auction page...
        [Auction: 1/X] ✅ Loaded: 22 vehicles
        [Auction: 1/X] Filtered: 5 vehicles (GJ + With Papers)
        [Auction: 1/X] 📸 Extracting images (5 vehicles)...
        [Auction: 1/X] | [Vehicle: 1/5] GJ05JQ3039 (VID: ABC123)
        [Auction: 1/X] | [Vehicle: 1/5] 🖼️ Gallery opened: Found 304 images
        [Auction: 1/X] ✅ Status: COMPLETE | Filtered: 5 | With Images: 5/5
        [Auction: 1/X] 💾 Saved
  ```

- **Returns**: True on success, False on error

#### `download_cardekho_images()`

- **Input**: Reads `downloads/cardekho_auction_paths.json`
- **Error Handling**: If file doesn't exist or is empty, log error and return False
- **Filter**: Only process auctions with `status: "complete"` (skip partial, failed, timeout, no_match)
- **Process**:
  1. For each complete auction:
     - For each vehicle:
       - Create folder: `downloads/<SCRAPE_START_DATE>/<REG_NO>/images/`
       - **Skip Logic**: Check if folder exists AND contains `images/` subfolder with files AND `metadata.txt` exists
       - Get `vehicleimages` array
       - Randomly select up to `IMAGE_COUNT` images using `random.sample()`
       - Download concurrently (ThreadPoolExecutor, 10 workers)
       - Create `metadata.txt` with key-value format (one per line: `"Key: Value\n"`):
         - Title: `make_model`
         - Registration Number: `registration_number`
         - Manufacturing Year: `manufacturing_year`
         - Location: `location`
         - RC Status: `rc_status`
         - Transmission: `transmission`
         - Ownership: `ownership`
         - Fuel Type: `fuel_type`
         - Yard Name: `yard_name`
         - Yard Location: `yard_location`
- **Logging Format**:

  ```
  DOWNLOADING CARDEKHO VEHICLE IMAGES AND METADATA
     • Complete auctions: X

     Auction 1/X: Auction Title (ID: 12345, Y vehicles)
        [1/Y] GJ05JQ3039: Downloading 30/45 images
        [1/Y] GJ05JQ3039: Downloaded 30 images
  ```

- **Returns**: True on success, False on error

---

## Logging Requirements

### Logging Configuration

All files must set up logging with:

```python
import logging
import os

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
```

### Logging Format Standards

**CarTrade Logs:**

- Use `[X/Y]` format for vehicle counters
- Example: `[1/5] GJ05JQ3039: Downloading 30/45 images`

**CarDekho Logs:**

- **MUST** use `[Auction: X/Y] | [Vehicle: A/B]` format for ALL logs
- Every log line should include auction and vehicle context when applicable
- Example: `[Auction: 4/22] | [Vehicle: 1/5] GJ05JQ3039 (VID: ABC123)`

### Emoji Usage

- ✅ Success/Complete
- ⚠️ Warning/Retry
- ❌ Error/Failure
- 🔄 Retry/Reload
- 🌐 Loading page
- 📸 Extracting images
- 🖼️ Gallery/Images
- 💾 Saved
- 📊 Summary/Statistics

### Logging Best Practices

- **No verbose logging during downloads** (only log failures)
- **Show progress clearly** with counters
- **Include context** in every log (which auction, which vehicle)
- **Log retry attempts** with attempt numbers
- **Log success/failure** status clearly

---

## Retry Logic Requirements

### Uniform 3 Retry Attempts

**All retry mechanisms must use exactly 3 attempts:**

1. **Auction Page Fetching**: 3 attempts with exponential backoff (2s, 4s, 8s)
2. **Vehicle Detail Page Fetching**: 3 attempts with exponential backoff
3. **Image Extraction**: 3 attempts per vehicle
4. **Timeout Auctions**: 3 retry rounds
5. **Partial/Failed Auctions**: 3 retry rounds

### Smart Retry Logic (CarDekho Partial/Failed Auctions)

**Critical Requirements:**

1. **Preserve Successful Vehicles**:

   - Identify vehicles with both `registration_number` + `make_model` (data) AND `vehicleimages` array with length > 0 (images)
   - These are "successful" and must NOT be retried
   - Track using `vid_item_id` key format

2. **Only Retry Failed Vehicles**:

   - Track which vehicles failed (missing data or images)
   - Only retry those specific vehicles
   - Use `vid_item_id` keys to track: `f"{vid}_{item_id}"`

3. **Conditional Reload**:

   - Only reload auction page if `expected != loaded`
   - If `expected == loaded`, only retry failed vehicles without reloading

4. **Merge Strategy**:

   - Keep all successful vehicles
   - Add retried vehicles (only if they're in failed list or new)
   - Don't duplicate vehicles

5. **Complete Version Creation**:
   - After all retries, if auction status is still "partial"
   - Create a new auction object with:
     - Same data as original
     - `vehicles`: Only vehicles with both data AND images
     - `status`: "complete"
     - `title`: Original title + " (Complete Version)"
   - Append to end of auctions list
   - This ensures no data loss for successfully processed vehicles

---

## Data Structures

### CarTrade JSON Files

**cartrade_events_raw.json**: Array of event objects

```json
[
  {
    "eventId": "12345",
    "catId": "5",
    "eventEndDateTime": "14-Oct-2025 14:06",
    "bidNowPath": "/auction/...",
    ...
  }
]
```

**cartrade_event_paths.json**: Array of path objects

```json
[
  {
    "eventId": "12345",
    "bidNowPath": "/auction/..."
  }
]
```

**cartrade_vehicles_gujarat.json**: Array of vehicle objects

```json
[
  {
    "registrationNumber": "GJ05JQ3039",
    "imageUrls": ["http://..."],
    "detailLink": "/auction/...",
    ...
  }
]
```

### CarDekho JSON Files

**cardekho_auction_paths.json**: Array of auction objects

```json
[
  {
    "auction_id": "177730",
    "title": "Exclusive Bajaj Salvage Auction 10Dec25",
    "slug": "Exclusive-Bajaj-Salvage-Auction-10Dec25",
    "vehicle_count": 22,
    "gj_vehicle_count": 5,
    "status": "complete",
    "summary": "Status: COMPLETE - Expected: 22, Loaded: 22, Filtered: 5, With Data: 5, With Images: 5",
    "vehicles": [
      {
        "vid": "WI8PGRAM",
        "item_id": "6663609",
        "vehicle_link": "#/auction/vehicleDetail/WI8PGRAM/6663609",
        "registration_number": "GJ06HD6695",
        "make_model": "Ford EcoSport 1.5 TITANIUM",
        "manufacturing_year": "2014",
        "location": "Vadodara",
        "rc_status": "With Papers",
        "transmission": "Manual",
        "ownership": "1st Owner",
        "fuel_type": "Diesel",
        "yard_name": "Yard Name",
        "yard_location": "Yard Location",
        "vehicleimages": [
          "http://auctionscdn.cardekho.com/auctionuploads/177730/GJ06HD6695/A (1).JPG",
          ...
        ]
      }
    ]
  }
]
```

---

## Manufacturing Year Extraction

**Critical**: Manufacturing year must be cleaned properly:

- **Input examples**: `"2024"`, `"Jul \n2024"`, `"2024\n"`, `"Jul 2024"`
- **Process**:
  1. Strip whitespace
  2. Remove newlines: `re.sub(r'\n+', ' ', text)`
  3. Normalize whitespace: `re.sub(r'\s+', ' ', text)`
  4. Extract only 4-digit year: `re.search(r'(\d{4})', text)`
  5. If found, use the year; otherwise use cleaned text
- **Output**: Only the 4-digit year (e.g., `"2024"`)

---

## Image URL Handling

**CarDekho Image URLs:**

- Extract as-is from HTML (no URL encoding)
- Remove query parameters: `url.split('?')[0]`
- Filter: Only URLs containing `auctionscdn.cardekho.com/auctionuploads/`
- Deduplicate using set

**Image Download:**

- Use `requests.get()` with timeout 15 seconds
- Stream download for large files
- Headers: Include `User-Agent` and `Referer: https://auctions.cardekho.com/`
- Handle errors gracefully (log and continue)

---

## File Naming Conventions

**CarTrade Files** (prefix: `cartrade_`):

- `cartrade_events_raw.json`
- `cartrade_events_insurance.json`
- `cartrade_event_paths.json`
- `cartrade_auction_details_full.json`
- `cartrade_vehicles_gujarat.json`

**CarDekho Files** (prefix: `cardekho_`):

- `cardekho_dashboard_data.json`
- `cardekho_insurance_data.json`
- `cardekho_auction_paths.json`
- `cardekho_failed_auctions.json`

**Folder Structure**:

- `downloads/<SCRAPE_START_DATE>/<REG_NO>/images/`
- Registration numbers sanitized: Remove special chars using `re.sub(r"[^A-Za-z0-9]", "_", raw_reg.strip().upper())`
- Example: `GJ05JQ3039` → folder name `GJ05JQ3039`
- If both registrationNumber and sellerRef are invalid, use format: `<sanitized_reg>_<auction_id>`

---

## Error Handling

### Network Errors

- Retry with exponential backoff (3 attempts)
- Log specific error messages with context: `logging.error(f"   ❌ Failed: {str(e)[:50]}")`
- Continue processing other items (don't stop entire pipeline)

### Timeout Errors

- Track timeout auctions for retry (mark with status "timeout")
- Increase timeout values (90 seconds for navigation, 20 seconds for selectors)
- Wait longer after page load (3 seconds)
- Log: `"⚠️  Navigation timeout (attempt X/3) for auction Y, will retry..."`

### Missing Data

- Log warnings with context: `logging.warning(f"[WARN] Missing registrationNumber for auctionId={auction_id}")`
- Continue processing (use fallback values if available)
- Mark auctions/vehicles with appropriate status

### Playwright Errors

- Handle `PlaywrightTimeoutError` specifically (import from `playwright.sync_api`)
- Retry with exponential backoff
- Log detailed error messages with attempt numbers
- Always close browser in finally block or use context manager

### File I/O Errors

- Check if directories exist before writing: `os.makedirs(path, exist_ok=True)`
- Handle JSON decode errors gracefully: `try/except json.JSONDecodeError`
- Log file errors: `logging.error(f"Failed to read/write {filename}: {e}")`

---

## Performance Optimizations

1. **Concurrent Downloads**: Use ThreadPoolExecutor (10 workers) for image downloads
2. **Incremental Saving**: Save JSON files after each auction/vehicle (use `json.dump()` with `indent=4, ensure_ascii=False`)
3. **Skip Already Processed**: Check if folder exists with images and metadata before processing
4. **Minimal Logging During Downloads**: Only log failures, not successes (for speed)
5. **Efficient HTML Parsing**: Use BeautifulSoup with `'html.parser'` parser
6. **Request Timeouts**: 20 seconds for GET requests, 25 seconds for POST requests, 90 seconds for Playwright navigation
7. **Delays**: 2 seconds between CarTrade auction detail requests

---

## Testing Requirements

The generated code must:

1. Handle missing cookies gracefully
2. Handle network timeouts
3. Handle empty responses
4. Handle malformed JSON
5. Handle missing environment variables
6. Handle file I/O errors
7. Preserve data on partial failures
8. Create complete versions correctly

---

## Code Quality Standards

1. **Type Hints**: Use type hints where appropriate
2. **Docstrings**: Include docstrings for all functions
3. **Error Messages**: Clear, actionable error messages
4. **Code Comments**: Comment complex logic
5. **Consistent Formatting**: Follow PEP 8
6. **No Hardcoded Values**: Use environment variables
7. **Modular Design**: Separate concerns into functions
8. **DRY Principle**: Avoid code duplication

---

## Critical Implementation Details

### CarDekho Authentication

- Extract Bearer token from `connect.sid` cookie
- Extract user info from `globals` cookie (JSON)
- Add all extracted headers to API requests

### CarDekho SPA Handling

- Use Playwright for all page navigation
- Wait for `domcontentloaded` state
- Wait for specific selectors (timeout 20 seconds)
- Scroll to trigger lazy loading
- Wait for `networkidle` state

### Image Gallery Opening

- Try clicking "View Photos" link first
- Fallback to clicking main vehicle image
- Wait for gallery to appear (5 seconds)
- Wait additional 2 seconds for images to load

### Status Calculation Logic

```python
if auction_html is None:
    status = "failed"
elif loaded_vehicles == 0 and expected_vehicles > 0:
    status = "timeout"
elif expected_vehicles == loaded_vehicles and filtered_count > 0 and vehicles_with_images_count == filtered_count:
    status = "complete"
elif filtered_count > 0 and vehicles_with_images_count == filtered_count:
    status = "complete"  # All filtered have images
elif filtered_count > 0:
    status = "partial"
else:
    status = "no_match"
```

### Manufacturing Year Cleaning

```python
year_text = year_li.get_text(strip=True)
year_text = re.sub(r'\s+', ' ', year_text)  # Normalize whitespace
year_text = re.sub(r'\n+', ' ', year_text)  # Remove newlines
year_match = re.search(r'(\d{4})', year_text)
if year_match:
    vehicle_data['manufacturing_year'] = year_match.group(1)
else:
    vehicle_data['manufacturing_year'] = year_text.strip()
```

---

## Expected Output Examples

### Log Output (CarDekho)

```
EXTRACTING CARDEKHO VEHICLE DATA
   • Filter: Gujarat (GJ) registration + 'With Papers' RC status

   • Processing 22 auction(s)

   [Auction: 1/22] Exclusive Bajaj Salvage Auction 10Dec25 (ID: 177730)
      Expected: 22 vehicles
      [Auction: 1/22] 🌐 Loading auction page...
      [Auction: 1/22] ✅ Loaded: 22 vehicles
      [Auction: 1/22] Filtered: 5 vehicles (GJ + With Papers)
      [Auction: 1/22] 📸 Extracting images (5 vehicles)...
      [Auction: 1/22] | [Vehicle: 1/5] GJ05JQ3039 (VID: ABC123)
      [Auction: 1/22] | [Vehicle: 1/5] 🖼️ Gallery opened: Found 304 images
      [Auction: 1/22] | [Vehicle: 2/5] GJ03NK5261 (VID: XYZ789)
      [Auction: 1/22] | [Vehicle: 2/5] 🖼️ Gallery opened: Found 156 images
      [Auction: 1/22] ✅ Status: COMPLETE | Filtered: 5 | With Images: 5/5
      [Auction: 1/22] 💾 Saved
```

### Metadata.txt Format

```
Title: Ford EcoSport 1.5 TITANIUM
Registration Number: GJ06HD6695
Manufacturing Year: 2014
Location: Vadodara
RC Status: With Papers
Transmission: Manual
Ownership: 1st Owner
Fuel Type: Diesel
Yard Name: Yard Name
Yard Location: Yard Location
```

---

## Final Checklist

Before considering the project complete, ensure:

- [ ] All file names use correct prefixes (`cartrade_` and `cardekho_`)
- [ ] Environment variable is `CAR_TRADE_COOKIE` (not `COOKIE`)
- [ ] All retry mechanisms use exactly 3 attempts
- [ ] Smart retry logic preserves successful vehicles
- [ ] Complete versions are created for partial auctions
- [ ] All CarDekho logs include `[Auction: X/Y] | [Vehicle: A/B]` format
- [ ] Manufacturing year extraction removes months and newlines
- [ ] Image URLs are extracted as-is (no encoding)
- [ ] Logging is minimal during downloads (only failures)
- [ ] Incremental saving after each auction/vehicle
- [ ] Proper error handling with context
- [ ] All functions have docstrings
- [ ] Code follows PEP 8 style guide
- [ ] All imports are at the top
- [ ] No hardcoded paths or values
- [ ] Proper folder structure creation
- [ ] Zip archive created at the end

---

## Generation Instructions

When generating this project:

1. **Create all files** in the exact structure specified
2. **Implement all functions** with the exact logic described
3. **Use the exact logging formats** provided
4. **Follow the retry logic** specifications precisely
5. **Include all error handling** as described
6. **Test edge cases** (missing data, timeouts, etc.)
7. **Ensure code is production-ready** with proper error handling
8. **Add comprehensive comments** for complex logic
9. **Follow Python best practices** throughout
10. **Ensure 100% accuracy** to the specifications

---

**END OF PROMPT**

This prompt contains all the information needed to regenerate the complete project with 100% accuracy. Follow every detail precisely to ensure the generated code works exactly as intended.
