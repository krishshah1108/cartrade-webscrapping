# CarTrade & CarDekho Web Scraping Project

A comprehensive Python-based web scraping solution that automatically extracts vehicle auction data from two major Indian auction platforms: **CarTrade Exchange** and **CarDekho Auctions**. The project filters for insurance-related auctions, extracts vehicle details, downloads images, and organizes all data in a structured format.

---

## 📋 Table of Contents

1. [Project Overview](#project-overview)
2. [What This Project Does](#what-this-project-does)
3. [How It Works](#how-it-works)
4. [Project Architecture](#project-architecture)
5. [Installation & Setup](#installation--setup)
6. [Configuration](#configuration)
7. [Usage](#usage)
8. [Output Structure](#output-structure)
9. [Technical Details](#technical-details)
10. [Troubleshooting](#troubleshooting)
11. [Project Structure](#project-structure)

---

## 🎯 Project Overview

This project automates the collection of vehicle auction data from two major Indian auction platforms. It extracts insurance-related auction data, filters for Gujarat-registered vehicles, downloads images, and organizes everything in a structured format.

### **CarTrade Exchange** (cartradeexchange.com)

- **API-based scraping**: Uses POST requests to fetch live events
- **Event filtering**: Filters by category ID 5 (Insurance) and target date
- **Vehicle filtering**: Extracts only Gujarat (GJ) registered vehicles
- **Image download**: Downloads vehicle images and creates metadata files
- **Detail extraction**: Optionally fetches detailed vehicle information from detail pages

### **CarDekho Auctions** (auctions.cardekho.com)

- **API + Browser automation**: Uses POST API for dashboard data, Playwright for SPA pages
- **Business filtering**: Filters by "Insurance" business type and date from title
- **Vehicle filtering**: Extracts Gujarat (GJ) vehicles with "With Papers" RC status
- **Image extraction**: Handles JavaScript-rendered galleries to extract all images
- **Retry mechanism**: Automatically retries failed/timeout auctions
- **Status tracking**: Maintains detailed status for each auction

---

## 🔍 What This Project Does

### CarTrade Exchange Pipeline

1. **Event Fetching**: Retrieves all live auction events from CarTrade Exchange API
2. **Insurance Filtering**: Filters events by category ID 5 (Insurance) and target date
3. **Auction Details**: Fetches detailed information for each filtered auction
4. **Gujarat Filtering**: Extracts only vehicles registered in Gujarat (registration starting with "GJ")
5. **Image Download**: Downloads all vehicle images and saves metadata

### CarDekho Auctions Pipeline

1. **Dashboard Data**: Fetches all dashboard data via POST API request
2. **Insurance Filtering**: Filters auctions by:
   - Business type: "Insurance"
   - Date from title (e.g., "10Dec25" format)
3. **Vehicle Extraction**:
   - Loads auction detail pages using Playwright (handles AngularJS SPA)
   - Extracts vehicle links from rendered HTML
   - Filters vehicles by:
     - Registration: Gujarat (GJ) only
     - RC Status: "With Papers" only
4. **Image Extraction**:
   - Fetches individual vehicle detail pages
   - Clicks gallery to load all images
   - Extracts image URLs from multiple HTML attributes
5. **Retry Logic**: Automatically retries failed/timeout auctions up to 3 times
6. **Status Tracking**: Maintains status for each auction (complete, partial, failed, timeout, no_match)

---

## ⚙️ How It Works

### Step-by-Step Process

#### **CarTrade Exchange Flow:**

```
1. Fetch Live Events
   └─> API Request → downloads/cartrade_events_raw.json

2. Filter Insurance Events
   └─> Filter by category_id=5 and date
   └─> downloads/cartrade_events_insurance.json
   └─> downloads/cartrade_event_paths.json

3. Fetch Auction Details
   └─> For each event path, fetch auction details
   └─> downloads/cartrade_auction_details_full.json
   └─> Filter for GJ registrations
   └─> downloads/cartrade_vehicles_gujarat.json

4. Download Images & Metadata
   └─> For each GJ vehicle:
       ├─> Create folder: downloads/<DATE>/<REG_NO>/
       ├─> Download images to images/ folder
       └─> Save metadata.txt
```

#### **CarDekho Auctions Flow:**

```
1. Fetch Dashboard Data
   └─> POST to /web/getAllDashboardData
   └─> Extract Bearer token from cookie
   └─> downloads/cardekho_dashboard_data.json

2. Filter Insurance Business
   └─> Filter by business="Insurance"
   └─> Filter by date from title (e.g., "10Dec25")
   └─> downloads/cardekho_insurance_data.json
   └─> downloads/cardekho_auction_paths.json

3. Extract Vehicle Data
   └─> For each auction:
       ├─> Load page with Playwright (handles SPA)
       ├─> Scroll to load all vehicles (lazy loading)
       ├─> Extract vehicle links
       ├─> Filter: GJ + With Papers
       └─> For each vehicle:
           ├─> Fetch vehicle detail page
           ├─> Click gallery to load images
           ├─> Extract image URLs
           └─> Save to cardekho_auction_paths.json

4. Retry Logic
   └─> Retry timeout auctions (once)
   └─> Retry partial/failed auctions (3 times)
```

---

## 🏗️ Project Architecture

### Technology Stack

- **Python 3.10+**: Core programming language
- **Playwright**: Browser automation for JavaScript-rendered pages
- **BeautifulSoup4**: HTML parsing and extraction
- **Requests**: HTTP API requests
- **python-dotenv**: Environment variable management

### Key Components

1. **API Client**: Handles authenticated requests with cookie-based auth
2. **SPA Handler**: Uses Playwright to render AngularJS applications
3. **HTML Parser**: Extracts data using CSS selectors and regex
4. **Image Extractor**: Multiple fallback methods for image URL extraction
5. **Retry Mechanism**: Exponential backoff for network issues
6. **Status Tracker**: Monitors and reports auction processing status

---

## 📦 Installation & Setup

### Prerequisites

- Python 3.10 or higher
- pip (Python package manager)
- Internet connection
- Valid authentication cookies from both platforms

### Step 1: Clone/Download the Project

```powershell
# Navigate to your project directory
cd E:\cartrade-webscrapping
```

### Step 2: Install Python Dependencies

```powershell
python -m pip install -r requirements.txt
```

### Step 3: Install Playwright Browsers

Playwright requires browser binaries to be installed separately:

```powershell
playwright install chromium
```

### Step 4: Get Authentication Cookies

#### For CarTrade Exchange:

1. Open your browser and navigate to `https://cartradeexchange.com`
2. Log in to your account
3. Open Developer Tools (F12)
4. Go to Application/Storage → Cookies
5. Copy the entire cookie string
6. Paste it in `.env` as `CAR_TRADE_COOKIE`

#### For CarDekho Auctions:

1. Open your browser and navigate to `https://auctions.cardekho.com`
2. Log in to your account
3. Open Developer Tools (F12)
4. Go to Network tab
5. Make any request (e.g., refresh page)
6. Find a request to `auctions.cardekho.com`
7. Copy the Cookie header value (includes `connect.sid`, `globals`, etc.)
8. Paste it in `.env` as `CAR_DEKHO_COOKIE`

**Important**: Cookies expire after some time. You'll need to update them periodically.

### Step 5: Create `.env` File

Create a `.env` file in the project root:

```properties
SCRAPER_NAME=Your Name
SCRAPE_START_DATE=2025-12-10
CAR_TRADE_COOKIE=<paste your CarTrade cookie here>
CAR_DEKHO_COOKIE=<paste your CarDekho cookie here>
IMAGE_COUNT=30
```

---

## ⚙️ Configuration

### Environment Variables (`.env`)

| Variable            | Required | Description                                        | Example                        |
| ------------------- | -------- | -------------------------------------------------- | ------------------------------ |
| `SCRAPER_NAME`      | No       | Friendly name for logging                          | `Tech Krish`                   |
| `SCRAPE_START_DATE` | Yes      | Target date for filtering auctions (YYYY-MM-DD)    | `2025-12-10`                   |
| `CAR_TRADE_COOKIE`  | Yes\*    | CarTrade Exchange authentication cookie            | `session_id=abc123; user=...`  |
| `CAR_DEKHO_COOKIE`  | Yes\*    | CarDekho Auctions authentication cookie            | `connect.sid=...; globals=...` |
| `IMAGE_COUNT`       | No       | Max images to download per vehicle (CarTrade only) | `30`                           |

\*Required only if using the respective platform

### Date Format in CarDekho Titles

CarDekho auction titles contain dates in format: `dMMMyy` (e.g., "10Dec25" = December 10, 2025)

The scraper automatically:

- Parses dates from titles using regex
- Matches against `SCRAPE_START_DATE`
- Only processes auctions matching the target date

---

## 🚀 Usage

### Run Complete Pipeline

Run all scraping steps in sequence:

```powershell
python main.py
```

This will execute the complete pipeline:

**CarTrade Exchange:**

1. Fetch all live events from API
2. Filter insurance events (category ID 5) for target date
3. Extract bid paths for detailed scraping
4. Fetch detailed auction data for each event
5. Filter vehicles by Gujarat (GJ) registration
6. Download images and create metadata files

**CarDekho Auctions:**

1. Fetch dashboard data via POST API
2. Filter insurance business auctions by date
3. Extract vehicle links from auction pages (handles SPA)
4. Filter vehicles (GJ + With Papers)
5. Extract vehicle images from detail pages
6. Download images and create metadata files

**Final Step:**

- Create zip archive of all downloaded data

### Run Individual Steps

#### CarTrade Exchange

```powershell
# Step 1: Fetch live events
python -c "from scraper.events_scraper import fetch_live_events; fetch_live_events()"

# Step 2: Filter insurance events
python -c "from scraper.events_scraper import filter_insurance_events; filter_insurance_events('downloads/cartrade_events_raw.json')"

# Step 3: Fetch auction details
python -c "from scraper.auction_details_scraper import fetch_auction_details; fetch_auction_details()"

# Step 4: Download images
python -c "from scraper.download_gj_images import download_gj_images; download_gj_images()"
```

#### CarDekho Auctions

```powershell
# Step 1: Fetch dashboard data
python -c "from scraper.cardekho_events_scraper import fetch_cardekho_dashboard_data; fetch_cardekho_dashboard_data()"

# Step 2: Filter insurance business
python -c "from scraper.cardekho_events_scraper import filter_insurance_business; filter_insurance_business('downloads/cardekho_dashboard_data.json')"

# Step 3: Extract vehicle data and images
python -c "from scraper.cardekho_vehicle_scraper import update_auction_paths_with_vehicles; update_auction_paths_with_vehicles()"
```

---

## 📁 Output Structure

### JSON Files (`downloads/`)

#### CarTrade Exchange:

- `cartrade_events_raw.json` - All live events from API (raw data)
- `cartrade_events_insurance.json` - Filtered insurance events (category ID 5, matching date)
- `cartrade_event_paths.json` - Array of `{eventId, bidNowPath}` for fetching auction details
- `cartrade_auction_details_full.json` - Full auction details for all events (with API responses)
- `cartrade_vehicles_gujarat.json` - Only Gujarat-registered vehicles (GJ prefix)

#### CarDekho Auctions:

- `cardekho_dashboard_data.json` - Raw API response from dashboard
- `cardekho_insurance_data.json` - Filtered insurance business data
- `cardekho_auction_paths.json` - **Main output file** with:
  ```json
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
        "registration_number": "GJ06HD6695",
        "make_model": "Ford EcoSport 1.5 TITANIUM",
        "manufacturing_year": "2014",
        "location": "Vadodara",
        "rc_status": "With Papers",
        "vehicleimages": [
          "http://auctionscdn.cardekho.com/auctionuploads/177730/GJ06HD6695/A (1).JPG",
          ...
        ]
      }
    ]
  }
  ```
- `cardekho_failed_auctions.json` - Auctions that failed after all retries

### Image Folders (Both Platforms)

Both CarTrade and CarDekho save images to the same date-based folder structure:

```
downloads/
└── 2025-12-10/                    # Date from SCRAPE_START_DATE
    ├── GJ06HD6695/                # Registration number (sanitized)
    │   ├── images/
    │   │   ├── 1.jpg
    │   │   ├── 2.jpg
    │   │   └── ... (up to IMAGE_COUNT images)
    │   └── metadata.txt           # Human-readable vehicle details
    └── GJ12AB3456/
        └── ...
```

**Note**:

- CarTrade: Images are randomly selected from available images (up to `IMAGE_COUNT`)
- CarDekho: Images are randomly selected from `vehicleimages` array (up to `IMAGE_COUNT`)
- Both platforms skip folders that already exist with images and metadata

### Logs (`logs/`)

- `scraper.log` - Detailed execution log with timestamps, log levels, and messages

**Log Format:**

```
2025-12-10 14:30:45 | INFO | Processing 5 GJ vehicles for image download & metadata.
2025-12-10 14:30:46 | INFO |    [1/5] GJ05JQ3039: Downloading 30/45 images
2025-12-10 14:30:50 | INFO |    [1/5] GJ05JQ3039: Downloaded 30 images
2025-12-10 14:30:51 | WARNING |    [2/5] GJ03NK5261: No images found
```

**Logging Features:**

- Progress indicators: `[X/Y]` format for vehicle/auction counters
- Auction context: Shows which auction and vehicle is being processed
- Error details: Specific reasons for failures
- Summary statistics: Final counts and status

---

## 🔧 Technical Details

### Image Download Strategy

#### CarTrade Exchange:

- Downloads images from `imageUrls` array in auction data
- Randomly selects up to `IMAGE_COUNT` images (default: 30)
- Uses concurrent downloads (ThreadPoolExecutor with 10 workers)
- Skips already downloaded images
- Creates metadata from detail page if cookie is available

#### CarDekho Auctions:

- Downloads images from `vehicleimages` array in vehicle data
- Randomly selects up to `IMAGE_COUNT` images (default: 30)
- Uses concurrent downloads (ThreadPoolExecutor with 10 workers)
- Skips folders that already exist with images and metadata
- Creates metadata from vehicle JSON data

### Authentication

#### CarDekho Auctions:

The scraper extracts authentication headers from cookies:

1. **Bearer Token**: Extracted from `connect.sid` cookie

   - Format: `s:UD-B4qkcyWQQ-JmRTDmghe2EzMEn7fHb.xxxxx`
   - Session ID becomes Bearer token: `Authorization: Bearer UD-B4qkcyWQQ-JmRTDmghe2EzMEn7fHb`

2. **User Info**: Extracted from `globals` cookie (JSON)
   - `userid`: User ID
   - `parentuserid`: Parent user ID
   - `associateclient`: Associated client IDs

These are automatically added to API request headers.

### JavaScript Rendering (SPA Handling)

CarDekho uses AngularJS Single Page Application:

- Routes use hash fragments: `#/auctionDetail/...`
- Content is dynamically loaded via JavaScript
- **Solution**: Playwright renders the page and waits for content

**Process**:

1. Navigate to URL with Playwright
2. Wait for DOM content loaded
3. Wait for vehicle selectors to appear
4. Scroll to trigger lazy loading
5. Extract rendered HTML
6. Parse with BeautifulSoup

### Image Extraction

Multiple fallback methods ensure maximum image extraction:

1. **Primary**: `data-src-pop` attribute (gallery full-size images)
2. **Secondary**: `data-src` attribute
3. **Tertiary**: `data-thumb` attribute
4. **Fallback**: `img src` attribute

**Gallery Opening**:

- Attempts to click "View Photos" link
- Falls back to clicking main vehicle image
- Waits for gallery to load before extraction

### Retry Logic

#### Network Timeouts:

- **3 attempts** with exponential backoff (2s, 4s, 8s)
- Increased timeouts (90 seconds for navigation)
- Longer waits after page load (3 seconds)

#### Image Extraction:

- **2 retry attempts** if no images found
- 2-second delay between retries
- Detailed logging of failure reasons

#### Auction Retries:

1. **Timeout Auctions**: Retried once after all auctions complete
2. **Partial/Failed Auctions**: Retried 3 times at the end
   - Only auctions with status `partial` or `failed` are retried
   - Stops early if all auctions become `complete` or `no_match`

### Status Tracking (CarDekho Only)

Each auction in `cardekho_auction_paths.json` has a `status` field:

- **`complete`**: Expected vehicles = loaded vehicles AND all filtered vehicles have images
- **`partial`**: Filtered vehicles found, but not all have images or expected ≠ loaded
- **`timeout`**: Expected vehicles but found 0 (page didn't load)
- **`failed`**: Failed to fetch auction page after all retries
- **`no_match`**: No vehicles match filters (GJ + With Papers)

Each auction also has a `summary` field with human-readable status:

```json
{
  "status": "complete",
  "summary": "Status: COMPLETE - Expected: 22, Loaded: 22, Filtered: 5, With Data: 5, With Images: 5"
}
```

**Status Metrics:**

- `Expected`: Number of vehicles expected in auction (from API)
- `Loaded`: Number of vehicles successfully extracted from page
- `Filtered`: Number of vehicles matching filters (GJ + With Papers)
- `With Data`: Number of filtered vehicles with complete data
- `With Images`: Number of filtered vehicles with extracted images

### Date Filtering

#### CarTrade Exchange:

- Filters events by `eventEndDateTime` matching `SCRAPE_START_DATE`
- Date format in API: `"14-Oct-2025 14:06"`
- Only processes events ending on the target date

#### CarDekho Auctions:

- Auction titles contain dates in format: `dMMMyy`
- Example: "Salvage Auction Non Motor J 10Dec25"
- Parsed as: December 10, 2025
- Matched against `SCRAPE_START_DATE` from `.env`
- Uses regex pattern: `(\d{1,2})(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)(\d{2})`

---

## 🐛 Troubleshooting

### Common Issues

#### 1. "Invalid Request" Error (CarDekho)

**Symptom**: API returns `{"status": 500, "message": "Invalid Request."}`

**Causes**:

- Cookie expired (most common)
- Missing authentication headers
- Cookie format incorrect

**Solution**:

1. Get fresh cookie from browser
2. Ensure cookie includes `connect.sid` and `globals`
3. Check logs for header extraction status

#### 2. No Images Found

**Symptom**: Vehicles extracted but `vehicleimages` array is empty

**Possible Reasons** (logged in detail):

- HTML too short/invalid
- Gallery attributes found but no valid URLs
- View photos link found but gallery not opened
- No gallery attributes found in HTML

**Solution**:

- Check logs for specific reason
- Images may not be available for that vehicle
- Try manual retry of that specific auction

#### 3. Timeout Errors

**Symptom**: "Timeout: Expected X vehicles but found 0"

**Causes**:

- Slow network connection
- Page taking too long to load
- JavaScript not rendering properly

**Solution**:

- Automatic retry handles most cases
- Check `cardekho_failed_auctions.json` for persistent failures
- Increase timeout values in code if needed

#### 4. Empty Dashboard Data

**Symptom**: `cardekho_dashboard_data.json` is empty or has error

**Causes**:

- Cookie expired
- API structure changed
- Authentication failed

**Solution**:

1. Verify cookie is fresh
2. Check `cardekho_dashboard_data.json` content
3. Verify Bearer token extraction in logs

#### 5. No Insurance Auctions Found

**Symptom**: Filtering returns 0 auctions

**Causes**:

- No auctions match date filter
- Business type not "Insurance"
- Date format mismatch

**Solution**:

- Check `cardekho_dashboard_data.json` for available auctions
- Verify `SCRAPE_START_DATE` format (YYYY-MM-DD)
- Check if any auctions have `"business": "Insurance"`

#### 6. Playwright Not Installed

**Symptom**: `ImportError: cannot import name 'sync_playwright'`

**Solution**:

```powershell
pip install playwright
playwright install chromium
```

### Debugging Tips

1. **Check Logs**: `logs/scraper.log` contains detailed execution information
2. **Inspect JSON Files**: Check intermediate JSON files to see what data was extracted
3. **Test Individual Steps**: Run steps separately to isolate issues
4. **Verify Cookies**: Ensure cookies are fresh and complete
5. **Check Network**: Verify internet connection and site accessibility

---

## 📂 Project Structure

```
cartrade-webscrapping/
├── main.py                          # Main entry point, orchestrates pipeline
├── requirements.txt                 # Python dependencies
├── .env                            # Configuration (not in git)
├── README.md                       # This file
│
├── scraper/                        # Scraping modules
│   ├── events_scraper.py          # CarTrade: Fetch and filter events
│   ├── auction_details_scraper.py # CarTrade: Fetch auction details
│   ├── download_gj_images.py      # CarTrade: Download images and metadata
│   ├── cardekho_events_scraper.py # CarDekho: Fetch and filter dashboard data
│   └── cardekho_vehicle_scraper.py # CarDekho: Extract vehicle data and images
│
├── downloads/                      # Output directory
│   ├── cartrade_events_raw.json            # CarTrade: All live events (raw)
│   ├── cartrade_events_insurance.json      # CarTrade: Filtered insurance events
│   ├── cartrade_event_paths.json           # CarTrade: Event paths for detail fetching
│   ├── cartrade_auction_details_full.json  # CarTrade: Full auction details
│   ├── cartrade_vehicles_gujarat.json      # CarTrade: Gujarat vehicles only
│   ├── cardekho_dashboard_data.json        # CarDekho: Raw dashboard
│   ├── cardekho_insurance_data.json        # CarDekho: Filtered insurance
│   ├── cardekho_auction_paths.json         # CarDekho: Main output (vehicles + images)
│   ├── cardekho_failed_auctions.json       # CarDekho: Failed auctions
│   └── 2025-12-10/                # Date-based image folders (both platforms)
│       ├── GJ06HD6695/            # CarTrade vehicle folders
│       │   ├── images/
│       │   └── metadata.txt
│       └── GJ05JQ3039/            # CarDekho vehicle folders
│           ├── images/
│           └── metadata.txt
│
└── logs/                           # Log files
    └── scraper.log                # Execution log
```

---

## 🔐 Security Notes

1. **Never commit `.env` file**: Contains sensitive authentication cookies
2. **Cookies expire**: Update cookies periodically when they expire
3. **Rate limiting**: The scraper includes delays to avoid overwhelming servers
4. **Respect robots.txt**: Check website terms of service before scraping

---

## 📝 Notes

- **Both CarTrade and CarDekho scraping are enabled** in `main.py` by default
- The project uses **incremental saving** - data is saved after each auction/vehicle
- **Status tracking** helps identify which auctions need attention
- **Retry logic** automatically handles most transient failures
- **File naming convention**: All CarTrade files use `cartrade_` prefix, CarDekho files use `cardekho_` prefix
- **Shared date folder**: Both platforms save images to the same `downloads/<DATE>/` folder structure

---

## 🚧 Future Improvements

- [ ] Add unit tests for HTML extraction and filtering
- [ ] Add CLI flags to run specific stages
- [ ] Add database storage option
- [ ] Add email notifications for completion
- [ ] Add progress bars for long-running operations
- [ ] Add support for multiple date ranges
- [ ] Add data validation and quality checks

---

## 📄 License

This repository contains personal tooling—no license specified.

---

## 🤝 Support

For issues or questions:

1. Check the Troubleshooting section
2. Review logs in `logs/scraper.log`
3. Inspect intermediate JSON files in `downloads/`
4. Verify configuration in `.env`

---

**Last Updated**: December 2025
