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
import re
import json
import random
import requests
import logging
import shutil
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

    if not date_folder:
        logging.error("SCRAPE_START_DATE not found in .env")
        return

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
        reg_no = re.sub(r"[^A-Za-z0-9]", "_", raw_reg.strip().upper())

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

        # Write metadata
        metadata_file = os.path.join(reg_folder, "metadata.txt")
        with open(metadata_file, "w", encoding="utf-8") as f:
            f.write(f"Yard Name: {auction.get('yardName','')}\n")
            f.write(f"Yard Location: {auction.get('yardLocation','')}\n")
            f.write(f"Contact Person Name: {auction.get('contactPersonName','')}\n")
            f.write(f"Contact Person Mobile: {auction.get('contactPersonMobile','')}\n")
            f.write(f"Item Title: {auction.get('itemTitle','')}\n")
            f.write(f"Registration Number: {raw_reg}\n")
            if both_invalid:
                f.write("Note: Both registrationNumber and sellerRef invalid. Fallback folder naming used.\n")
            elif fallback_used:
                f.write("Note: Used sellerRef as fallback for invalid registrationNumber.\n")

        logging.info(f"Saved metadata for {folder_name}")

    logging.info("=" * 60)
    logging.info("🎯 IMAGE DOWNLOAD SUMMARY")
    logging.info("=" * 60)
    logging.info("Summary: Fallback entries (regNo_auctionId) created only when both registrationNumber and sellerRef invalid.")
    logging.info(f"📊 Processed {valid_count} valid registrations out of {len(auctions)} total auctions")
    logging.info(f"📸 Total images downloaded: {total_images_downloaded}")
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
