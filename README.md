# CarTrade Webscrapping

A small Python-based scraper that fetches live auction events from cartradeexchange.com, filters insurance events, retrieves auction details, filters vehicles registered in Gujarat (GJ...), and downloads images + metadata for those vehicles.

## What this project does

- Fetches live auction events and saves raw JSON to `downloads/auction_data.json`.
- Filters insurance auctions (category ID 5) for the configured scrape date and writes:
  - `downloads/auction_data_filtered.json` (full event objects)
  - `downloads/bid_paths.json` (array of `{ eventId, bidNowPath }`)
- For each bid path, fetches auction details and saves:
  - `downloads/auction_details.json` (full responses per event)
  - `downloads/auction_details_GJ.json` (all auction items whose registration starts with "GJ")
- Downloads images and writes per-registration folders under `downloads/<SCRAPE_START_DATE>/<REG_NO>/images/` and a `metadata.txt` for each vehicle.

## Repo layout

- `main.py` — orchestrates the full pipeline (fetch events → filter → fetch details → download images)
- `requirements.txt` — Python dependencies
- `.env` — configuration (not committed to version control in general; included here for convenience in the workspace)
- `scraper/` — scraping modules:
  - `events_scraper.py` — fetches and filters events
  - `auction_details_scraper.py` — fetches auction details and filters for GJ registrations
  - `download_gj_images.py` — downloads images and metadata for GJ vehicles
- `downloads/` — output JSON and image folders
- `logs/` — logs produced by the scrapers

## Requirements

- Python 3.10+ recommended
- Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

## Configuration (`.env`)

Create a `.env` file in the project root with these keys:

- `SCRAPER_NAME` — friendly name for logging (optional)
- `SCRAPE_START_DATE` — target date to filter events (format: `YYYY-MM-DD`)
- `COOKIE` — authentication cookie string copied from your browser for cartradeexchange.com
- `IMAGE_COUNT` — (optional) number of images to download per vehicle (default 30)

Example `.env`:

```properties
SCRAPER_NAME=Tech Krish
SCRAPE_START_DATE=2025-10-17
COOKIE=<paste your cookie here>
IMAGE_COUNT=30
```

Security note: Keep `COOKIE` secret. Do not commit `.env` to git.

## Usage

- Run the whole pipeline (recommended):

```powershell
python .\main.py
```

- Or run individual stages:

```powershell
# Fetch live events and save downloads/auction_data.json
python -c "from scraper.events_scraper import fetch_live_events; print(fetch_live_events())"

# Filter insurance events
python -c "from scraper.events_scraper import filter_insurance_events; filter_insurance_events('downloads/auction_data.json')"

# Fetch auction details (requires downloads/bid_paths.json)
python -c "from scraper.auction_details_scraper import fetch_auction_details; fetch_auction_details()"

# Download GJ images (requires downloads/auction_details_GJ.json)
python -c "from scraper.download_gj_images import download_gj_images; download_gj_images()"
```

Note: Running `main.py` will call each of the above in sequence.

## Outputs

- JSON files under `downloads/`:
  - `auction_data.json`
  - `auction_data_filtered.json`
  - `bid_paths.json`
  - `auction_details.json`
  - `auction_details_GJ.json`
- Images and metadata under `downloads/<SCRAPE_START_DATE>/<REG_NO>/`
- Logs in `logs/scraper.log`

## Troubleshooting

- Empty or missing outputs:
  - Ensure `COOKIE` in `.env` is valid (login/auth cookie may expire). The scrapers read the `COOKIE` value from environment via `python-dotenv`.
- Parsing errors extracting `pk1` or registration numbers:
  - The site markup may have changed. See `scraper/auction_details_scraper.py` where `extract_pk1_from_html()` tries a regex and falls back to BeautifulSoup.
- Network errors or rate-limiting:
  - The scrapers use modest timeouts and a 2s sleep between requests. You may increase timeouts or add longer delays if you see 429 or similar errors.
- Image download failures:
  - `download_gj_images.py` logs failed downloads and continues. Check `logs/scraper.log` for per-URL failures.

## Testing and quality

- The project doesn't include unit tests yet. If you want, I can add a couple of small tests for HTML extraction and the events filter.

## Next improvements (optional)

- Add unit tests for `extract_pk1_from_html` and `filter_insurance_events`.
- Add CLI entrypoint and flags to run specific stages and override `.env` settings.
- Add retry/backoff for network requests and better error classification.
- Persist run metadata (timestamp, counts) to a CSV or DB for reporting.

## License

This repository contains personal tooling—no license specified.

---

If you'd like, I can also add a small test file and a simple usage script that runs each step with clearer progress output. Let me know which improvements you'd like next.