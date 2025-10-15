"""
download_gj_images.py
---------------------
Download images and metadata for GJ vehicles.
- Concurrent image downloading (threads)
- Number of images configurable via .env (IMAGE_COUNT)
- Logs missing or duplicate registration numbers with auctionId
"""

import os
import re
import json
import random
import requests
import logging
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

        # Missing registration number
        if not raw_reg:
            logging.warning(f"[WARN] Skipped auctionId={auction_id} missing registrationNumber")
            continue
        if len(raw_reg) < 6:
            logging.warning(f"[WARN] Found auctionId={auction_id} invalid registrationNumber={raw_reg}")
            if len(sellerRef) > 6 and sellerRef.startswith("GJ"):
                logging.info(f"  Using sellerRef={sellerRef} instead")
                raw_reg = sellerRef
            else:
                logging.warning(f"[WARN] Skipped auctionId={auction_id} invalid sellerRef={sellerRef} too")
                continue

        # Sanitize registration number
        reg_no = re.sub(r"[^A-Za-z0-9]", "_", raw_reg.strip().upper())

        # Duplicate registration number
        if reg_no in seen_registrations:
            logging.warning(f"[WARN] Skipped duplicate registrationNumber={reg_no} auctionId={auction_id}")
            continue
        seen_registrations.add(reg_no)

        valid_count += 1
        reg_folder = os.path.join(base_download_folder, reg_no)
        images_folder = os.path.join(reg_folder, "images")
        os.makedirs(images_folder, exist_ok=True)

        # Get all image URLs from imageUrls array
        image_urls = auction.get("imageUrls", [])
        if not image_urls:
            logging.warning(f"No images found for {reg_no}")
            continue

        # Simple logic: if <= image_count, download all; if > image_count, randomly select image_count
        if len(image_urls) <= image_count:
            to_download = image_urls  # Download all available images
            logging.info(f"{auction_id} | {reg_no} | Found {len(image_urls)} images (≤ {image_count}), downloading all")
        else:
            # Randomly select image_count images from available images
            to_download = random.sample(image_urls, image_count)
            logging.info(f"{auction_id} | {reg_no} | Found {len(image_urls)} images (> {image_count}), randomly selecting {image_count} unique URLs")
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            images_downloaded = 0
            for idx, img_url in enumerate(to_download, 1):
                ext = os.path.splitext(img_url)[1].split("?")[0] or ".jpg"
                save_path = os.path.join(images_folder, f"{idx}{ext}")
                
                # Skip if image already exists (prevent re-downloading)
                if os.path.exists(save_path):
                    logging.info(f"⏭️ Image already exists [{reg_no}], skipping: {os.path.basename(save_path)}")
                    continue
                    
                futures.append(executor.submit(download_image, img_url, save_path, reg_no))
                images_downloaded += 1
            
            for future in as_completed(futures):
                future.result()
            
            total_images_downloaded += images_downloaded
            logging.info(f"📸 Downloaded {images_downloaded} unique images for {reg_no}")

        metadata_file = os.path.join(reg_folder, "metadata.txt")
        os.makedirs(reg_folder, exist_ok=True)  # Ensure directory exists
        with open(metadata_file, "w", encoding="utf-8") as f:
            f.write(f"Yard Name: {auction.get('yardName','')}\n")
            f.write(f"Yard Location: {auction.get('yardLocation','')}\n")
            f.write(f"Contact Person Name: {auction.get('contactPersonName','')}\n")
            f.write(f"Contact Person Mobile: {auction.get('contactPersonMobile','')}\n")
            f.write(f"Item Title: {auction.get('itemTitle','')}\n")
            f.write(f"Registration Number: {raw_reg}\n")

        logging.info(f"Saved metadata for {reg_no}")

    logging.info("=" * 60)
    logging.info("🎯 IMAGE DOWNLOAD SUMMARY")
    logging.info("=" * 60)
    logging.info(f"📊 Processed {valid_count} valid registrations out of {len(auctions)} total auctions")
    logging.info(f"📸 Total images downloaded: {total_images_downloaded}")
    logging.info("✅ All GJ auctions processed successfully!")
    logging.info("=" * 60)

