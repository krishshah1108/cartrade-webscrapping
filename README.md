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
12. [Regenerating the Project](#regenerating-the-project)

---

## 🎯 Project Overview

This project automates the collection of vehicle auction data from two major Indian auction platforms: **CarTrade Exchange** and **CarDekho Auctions**. It extracts insurance-related auction data, filters for Gujarat-registered vehicles, downloads images, and organizes everything in a structured format.

### Key Features

- **CarTrade Exchange**: API-based scraping with POST requests, filters by category ID 5 (Insurance) and date, extracts GJ vehicles, downloads images
- **CarDekho Auctions**: API + Playwright for SPA handling, filters by "Insurance" business and date from title, extracts GJ vehicles with "With Papers" RC status, smart retry logic
- **Image Management**: Concurrent downloads, metadata creation, skip already processed vehicles
- **Data Organization**: Date-based folder structure, JSON intermediate files, final zip archive

---

## ⚙️ How It Works

### Pipeline Flow

**CarTrade**: Fetch events → Filter insurance → Extract auction details → Filter GJ vehicles → Download images & metadata

**CarDekho**: Fetch dashboard → Filter insurance by date → Extract vehicles (Playwright) → Filter GJ + With Papers → Extract images → Smart retry → Download images & metadata

**Final Step**: Create zip archive of all downloaded data

---

## 🏗️ Technology Stack

- **Python 3.10+**, **Playwright** (browser automation), **BeautifulSoup4** (HTML parsing), **Requests** (HTTP), **python-dotenv** (config)

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

**Date Format**: CarDekho titles use `dMMMyy` format (e.g., "10Dec25" = December 10, 2025). The scraper automatically parses and matches against `SCRAPE_START_DATE`.

---

## 🚀 Usage

### Run Complete Pipeline

Run all scraping steps in sequence:

```powershell
python main.py
```

This executes the complete pipeline for both platforms and creates a zip archive at the end.

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

- `scraper.log` - Detailed execution log with timestamps and progress indicators

**Log Format**: CarTrade uses `[X/Y]` format, CarDekho uses `[Auction: X/Y] | [Vehicle: A/B]` format. All logs include context, retry status, and emojis (✅ ⚠️ ❌ 🔄 🌐 📸 🖼️ 💾).

---

## 🔧 Technical Details

### Key Features

- **Image Downloads**: Concurrent (10 workers), random selection up to `IMAGE_COUNT`, skip existing
- **Authentication**: CarDekho extracts Bearer token from `connect.sid` cookie and user info from `globals` cookie
- **SPA Handling**: Playwright renders AngularJS pages, waits for selectors, scrolls for lazy loading
- **Image Extraction**: Multiple fallback methods (`data-src-pop`, `data-src`, `data-thumb`, `img src`), opens gallery automatically
- **Retry Logic**: 3 attempts everywhere with exponential backoff; smart retry preserves successful vehicles, only retries failed ones
- **Status Tracking**: `complete`, `partial`, `timeout`, `failed`, `no_match` with detailed metrics and summary
- **Date Filtering**: CarTrade uses `eventEndDateTime`, CarDekho parses `dMMMyy` format from titles

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

---

## 🔄 Regenerating the Project

If you need to regenerate this entire project from scratch, use the `PROMPT.md` file. This file contains a comprehensive prompt with all project details, specifications, and implementation requirements that can be used with AI assistants (like Cursor AI, ChatGPT, Claude, etc.) to recreate the project with 100% accuracy.

**To use PROMPT.md:**

1. Open `PROMPT.md` in your editor
2. Copy the entire contents
3. Paste into your AI assistant with the system role
4. The AI will generate all files according to the specifications

The prompt includes:

- Complete file structure
- Detailed function specifications
- Exact API endpoints and payloads
- Logging format requirements
- Retry logic specifications
- Data structure definitions
- Error handling requirements
- All technical implementation details

---

**Last Updated**: December 2025
