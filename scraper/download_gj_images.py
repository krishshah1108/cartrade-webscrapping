"""
download_gj_images.py
---------------------
Download images and metadata for GJ vehicles.
- Concurrent image downloading (threads)
- Number of images configurable via .env (IMAGE_COUNT)
- Logs missing, duplicate, and fallback registration numbers with auctionId
- If both registrationNumber and sellerRef invalid, still downloads under folder regNo_auctionId
"""

import os
import re as _re
import json
import random
import requests
import logging
import shutil
import time
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed


def download_image(url, save_path, reg_no):
    """Download a single image with logging."""
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        with open(save_path, "wb") as f:
            f.write(resp.content)
        logging.info(f"✅ Downloaded [{reg_no}]: {os.path.basename(save_path)}")
    except Exception as e:
        logging.error(f"❌ Failed to download [{reg_no}] {url}: {e}")


def extract_js_variables(html_content):
    """Extract JavaScript variables from HTML content."""
    details = {}
    
    # Patterns to extract specific variables
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
    
    for key, pattern in patterns.items():
        match = _re.search(pattern, html_content)
        if match:
            value = match.group(1).strip()
            if value:  # Only add non-empty values
                details[key] = value
    
    return details


def fetch_detail_page(detail_link, cookie):
    """Fetch detail page HTML content."""
    base_url = "https://www.cartradeexchange.com"
    full_url = base_url + detail_link
    
    headers = {
        'Cookie': cookie,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36',
        'Referer': 'https://www.cartradeexchange.com/Events-Live'
    }
    
    try:
        response = requests.get(full_url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.text
    except Exception as e:
        logging.error(f"Error fetching detail page {full_url}: {e}")
        return None


def download_gj_images():
    """Main function to download images and generate metadata for GJ vehicles."""
    load_dotenv()  # Load SCRAPE_START_DATE & IMAGE_COUNT

    if not logging.getLogger().hasHandlers():
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

    date_folder = os.getenv("SCRAPE_START_DATE")
    image_count = int(os.getenv("IMAGE_COUNT", 30))
    cookie = os.getenv("COOKIE", "")

    if not date_folder:
        logging.error("SCRAPE_START_DATE not found in .env")
        return

    if not cookie:
        logging.warning("COOKIE not found in .env - detail page scraping will be skipped")

    base_download_folder = os.path.join("downloads", date_folder)
    os.makedirs(base_download_folder, exist_ok=True)

    gj_file = os.path.join("downloads", "auction_details_GJ.json")
    if not os.path.exists(gj_file):
        logging.error(f"{gj_file} not found. Run previous scraper first.")
        return

    with open(gj_file, "r", encoding="utf-8") as f:
        auctions = json.load(f)

    logging.info(f"Processing {len(auctions)} GJ vehicles for image download & metadata.")
    seen_registrations = set()
    valid_count = 0
    total_images_downloaded = 0
    metadata_enhanced = 0

    for auction in auctions:
        raw_reg = auction.get("registrationNumber")
        auction_id = auction.get("auctionId", "?")
        sellerRef = auction.get("sellerRef", "?")
        fallback_used = False
        both_invalid = False

        # Handle missing or invalid registrationNumber
        if not raw_reg:
            logging.warning(f"[WARN] Missing registrationNumber for auctionId={auction_id}")
            raw_reg = sellerRef if sellerRef else "UNKNOWN"
            fallback_used = True

        if len(raw_reg) < 6:
            logging.warning(f"[WARN] Found auctionId={auction_id} invalid registrationNumber={raw_reg}")
            if len(sellerRef) > 6 and sellerRef.startswith("GJ"):
                logging.info(f"  Using sellerRef={sellerRef} instead of registrationNumber")
                raw_reg = sellerRef
                fallback_used = True
            else:
                logging.warning(f"[WARN] Both registrationNumber and sellerRef invalid for auctionId={auction_id}")
                both_invalid = True
                fallback_used = True
                raw_reg = raw_reg or "UNKNOWN"

        # Sanitize registration number
        reg_no = _re.sub(r"[^A-Za-z0-9]", "_", raw_reg.strip().upper())

        # Folder naming logic
        if both_invalid:
            folder_name = f"{reg_no}_{auction_id}"
        else:
            folder_name = reg_no

        # Skip duplicates
        if folder_name in seen_registrations:
            logging.warning(f"[WARN] Skipped duplicate folder={folder_name} auctionId={auction_id}")
            continue
        seen_registrations.add(folder_name)

        valid_count += 1
        reg_folder = os.path.join(base_download_folder, folder_name)
        images_folder = os.path.join(reg_folder, "images")
        os.makedirs(images_folder, exist_ok=True)

        # Get image URLs
        image_urls = auction.get("imageUrls", [])
        if not image_urls:
            logging.warning(f"No images found for {folder_name}")
            continue

        # Selection logic
        if len(image_urls) <= image_count:
            to_download = image_urls
            logging.info(f"{auction_id} | {folder_name} | Found {len(image_urls)} images (≤ {image_count}), downloading all")
        else:
            to_download = random.sample(image_urls, image_count)
            logging.info(f"{auction_id} | {folder_name} | Found {len(image_urls)} images (> {image_count}), selecting {image_count}")

        # Download concurrently
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            images_downloaded = 0
            for idx, img_url in enumerate(to_download, 1):
                ext = os.path.splitext(img_url)[1].split("?")[0] or ".jpg"
                save_path = os.path.join(images_folder, f"{idx}{ext}")

                if os.path.exists(save_path):
                    logging.info(f"⏭️ Image already exists [{folder_name}], skipping: {os.path.basename(save_path)}")
                    continue

                futures.append(executor.submit(download_image, img_url, save_path, folder_name))
                images_downloaded += 1

            for future in as_completed(futures):
                future.result()

            total_images_downloaded += images_downloaded
            logging.info(f"📸 Downloaded {images_downloaded} unique images for {folder_name}")

        # Extract detailed metadata from detail page if cookie is available
        detailed_info = {}
        if cookie and auction.get('detailLink'):
            detail_link = auction.get('detailLink')
            logging.info(f"Fetching detailed metadata for {folder_name}...")
            
            html_content = fetch_detail_page(detail_link, cookie)
            if html_content:
                detailed_info = extract_js_variables(html_content)
                if detailed_info:
                    logging.info(f"Extracted {len(detailed_info)} detailed fields for {folder_name}")
                    metadata_enhanced += 1
                else:
                    logging.warning(f"No detailed info extracted for {folder_name}")
            else:
                logging.warning(f"Failed to fetch detail page for {folder_name}")
            
            # Add delay between detail page requests
            time.sleep(2)
        
        # Add Title and itemTitle from JSON data to detailed_info (clean HTML tags)
        if auction.get('Title'):
            # Remove HTML tags from Title
            clean_title = _re.sub(r'<[^>]+>', '', auction.get('Title'))
            detailed_info['title'] = clean_title.strip()
        if auction.get('itemTitle'):
            # Remove HTML tags from itemTitle
            clean_item_title = _re.sub(r'<[^>]+>', '', auction.get('itemTitle'))
            detailed_info['item_title'] = clean_item_title.strip()

        # Write metadata
        metadata_file = os.path.join(reg_folder, "metadata.txt")
        with open(metadata_file, "w", encoding="utf-8") as f:
            # Write only the specific fields requested          
            # Add Title and itemTitle first
            if 'title' in detailed_info:
                f.write(f"Title: {detailed_info['title']}\n")
            if 'item_title' in detailed_info:
                f.write(f"Item Title: {detailed_info['item_title']}\n")
            
            # Add specific fields from detailed scraping
            if detailed_info:
                # Map our extracted keys to readable labels for only the requested fields
                label_mapping = {
                    'power_steering': 'Power Steering',
                    'fuel_type': 'Fuel Type',
                    'state': 'State',
                    'city': 'City',
                    'yard_location': 'Yard Location',
                    'yard_name': 'Yard Name',
                    'payment_terms': 'Payment Terms',
                    'rc_book_available': 'RC Book Available',
                    'seller_reference': 'Seller Reference',
                    'cte_contact_person': 'CTE Contact Person',
                    'cte_contact_phone': 'CTE Contact Phone',
                    'sunroof': 'Sun Roof',
                    'manufacturing_year': 'Manufacturing Year',
                }
                
                # Track which fields we've written to avoid duplicates
                written_fields = set()
                
                for key, value in detailed_info.items():
                    if key in label_mapping and key not in written_fields:
                        f.write(f"{label_mapping[key]}: {value}\n")
                        written_fields.add(key)
            
            # Add registration number from JSON
            f.write(f"Registration Number: {raw_reg}\n")

        logging.info(f"Saved metadata for {folder_name}")

    logging.info("=" * 60)
    logging.info("🎯 IMAGE DOWNLOAD & METADATA ENHANCEMENT SUMMARY")
    logging.info("=" * 60)
    logging.info("Summary: Fallback entries (regNo_auctionId) created only when both registrationNumber and sellerRef invalid.")
    logging.info(f"📊 Processed {valid_count} valid registrations out of {len(auctions)} total auctions")
    logging.info(f"📸 Total images downloaded: {total_images_downloaded}")
    if cookie:
        logging.info(f"🔍 Metadata enhanced for {metadata_enhanced} vehicles")
    else:
        logging.info("⚠️  Metadata enhancement skipped (no COOKIE found)")
    logging.info("✅ All GJ auctions processed successfully!")
    logging.info("=" * 60)


def create_date_zip(date_folder: str | None = None) -> str | None:
    """Create a zip archive of downloads/<date_folder>.

    If date_folder is None the function will read SCRAPE_START_DATE from .env.
    Returns the path to the created zip file, or None on error.
    """
    try:
        if not date_folder:
            load_dotenv()
            date_folder = os.getenv("SCRAPE_START_DATE")

        if not date_folder:
            logging.error("create_date_zip: SCRAPE_START_DATE not set; cannot create zip")
            return None

        src_dir = os.path.join("downloads", date_folder)
        if not os.path.exists(src_dir):
            logging.error(f"create_date_zip: source folder does not exist: {src_dir}")
            return None

        # Destination zip path: downloads/<date_folder>.zip (shutil will append .zip)
        base_name = os.path.join("downloads", date_folder)

        # If an existing zip exists, overwrite it by removing first
        zip_path = base_name + ".zip"
        if os.path.exists(zip_path):
            try:
                os.remove(zip_path)
            except Exception as e:
                logging.warning(f"Could not remove existing zip {zip_path}: {e}")

        logging.info(f"Creating zip archive for {src_dir} -> {zip_path} ...")
        # shutil.make_archive returns the actual archive path
        archive = shutil.make_archive(base_name, 'zip', root_dir=src_dir)
        logging.info(f"Created archive: {archive}")
        return archive
    except Exception as e:
        logging.exception(f"Failed to create date zip: {e}")
        return None
