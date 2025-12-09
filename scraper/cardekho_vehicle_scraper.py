"""
cardekho_vehicle_scraper.py
----------------------------
Scrapes vehicle details from CarDekho auction pages:
1. Fetches auction detail pages from filtered insurance data
2. Extracts vehicle links (VID and item_id) from each auction page
3. Fetches individual vehicle detail pages
4. Extracts vehicle metadata and saves to downloads/car_dekho/<REG_NO>/metadata.txt
"""

import os
import json
import re
import logging
import requests
import time
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from scraper.cardekho_events_scraper import extract_headers_from_cookie

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


def get_headers(cookie):
    """Get request headers with authentication."""
    extracted_headers = extract_headers_from_cookie(cookie)
    
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Origin": "https://auctions.cardekho.com",
        "Cookie": cookie,
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/142.0.0.0 Safari/537.36"
        ),
        "Referer": "https://auctions.cardekho.com/",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Ch-Ua": '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"'
    }
    
    headers.update(extracted_headers)
    return headers


def fetch_auction_detail_page(slug, auction_id, cookie, max_retries=3):
    """
    Fetch auction detail page HTML using Playwright to render JavaScript.
    
    Since this is an SPA with # routes, we need to render JavaScript to get the vehicle data.
    Implements retry logic with exponential backoff for network issues.
    
    Args:
        slug (str): Auction slug (e.g., "Gujarat-PSU-and-Surveyor-Vehicle-05Dec25")
        auction_id (str): Auction ID (e.g., "176639")
        cookie (str): Authentication cookie
        max_retries (int): Maximum number of retry attempts (default: 3)
        
    Returns:
        str: HTML content or None on error
    """
    url = f"{BASE_URL}/#/auctionDetail/{slug}"
    timeout_ms = 90000  # 90 seconds timeout
    
    for attempt in range(1, max_retries + 1):
        try:
            from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
            
            if attempt > 1:
                # Exponential backoff: 2^attempt seconds (2s, 4s, 8s)
                backoff_time = 2 ** attempt
                logging.info(f"   🔄 Retry {attempt}/{max_retries} (waiting {backoff_time}s)...")
                time.sleep(backoff_time)
            
            logging.info(f"   🌐 Loading page: {url} (Attempt {attempt}/{max_retries})")
            
            with sync_playwright() as p:
                # Launch browser in headless mode
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"
                )
                
                # Set cookies
                if cookie:
                    cookies_list = []
                    for cookie_pair in cookie.split(';'):
                        cookie_pair = cookie_pair.strip()
                        if '=' in cookie_pair:
                            name, value = cookie_pair.split('=', 1)
                            cookies_list.append({
                                'name': name.strip(),
                                'value': value.strip(),
                                'domain': 'auctions.cardekho.com',
                                'path': '/'
                            })
                    if cookies_list:
                        context.add_cookies(cookies_list)
                
                # Create a new page
                page = context.new_page()
                
                # Set extra headers
                headers = get_headers(cookie)
                page.set_extra_http_headers({
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Referer': f'{BASE_URL}/',
                })
                
                # Navigate to the page with increased timeout
                try:
                    page.goto(url, wait_until='domcontentloaded', timeout=timeout_ms)
                    # Wait longer after navigation for content to load
                    page.wait_for_timeout(3000)  # 3 seconds wait after navigation
                except PlaywrightTimeoutError as e:
                    browser.close()
                    if attempt < max_retries:
                        logging.warning(f"   ⚠️  Navigation timeout (attempt {attempt}/{max_retries}), will retry...")
                        continue
                    else:
                        logging.error(f"   ❌ Navigation timeout after {max_retries} attempts: {e}")
                        return None
                
                # Wait for vehicle content to load
                try:
                    page.wait_for_selector('a[href*="#/auction/vehicleDetail/"], tr[id*="auction_item_"]', timeout=20000)
                except PlaywrightTimeoutError:
                    pass  # Continue anyway
                
                # Wait longer for AngularJS to finish rendering
                page.wait_for_timeout(3000)  # Increased from 2000ms to 3000ms
                
                # Handle infinite scroll - scroll down to load all vehicles
                previous_count = 0
                current_count = len(page.query_selector_all('tr[id^="auction_item_"]'))
                scroll_attempts = 0
                max_scroll_attempts = 50
                
                # If no vehicles found initially, try scrolling to trigger lazy loading
                if current_count == 0:
                    for scroll_retry in range(5):  # Try scrolling 5 times
                        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        page.wait_for_timeout(3000)  # Longer wait for lazy loading
                        current_count = len(page.query_selector_all('tr[id^="auction_item_"]'))
                        if current_count > 0:
                            break
                
                # Scroll to load all vehicles (lazy loading)
                while scroll_attempts < max_scroll_attempts:
                    previous_count = current_count
                    
                    # Scroll to bottom to trigger loadMore()
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    page.wait_for_timeout(2000)
                    
                    # Check if new vehicles loaded
                    current_count = len(page.query_selector_all('tr[id^="auction_item_"]'))
                    
                    if current_count == previous_count:
                        break
                    else:
                        scroll_attempts += 1
                
                # Get the rendered HTML after all scrolling
                html = page.content()
                
                # Close browser properly - wait for any pending tasks
                try:
                    page.wait_for_timeout(1000)  # Give time for any pending tasks
                except:
                    pass
                
                browser.close()
            
            # Check if we got meaningful content
            has_vehicles = 'auction_item_' in html
            has_vehicle_detail_links = '#/auction/vehicleDetail/' in html
            has_ng_repeat = 'ng-repeat' in html and 'auctionDetail' in html
            
            if has_vehicles or has_vehicle_detail_links or has_ng_repeat:
                if attempt > 1:
                    logging.info(f"   ✅ Page loaded on retry {attempt}")
                return html
            else:
                if attempt < max_retries:
                    continue
                else:
                    return html  # Return anyway, might have data in different format
            
        except ImportError:
            logging.error("   ❌ Playwright not installed. Install it with: pip install playwright")
            logging.error("   💡 Then install browsers: playwright install chromium")
            return None
        except PlaywrightTimeoutError as e:
            if attempt < max_retries:
                continue
            else:
                logging.error(f"   ❌ Timeout after {max_retries} attempts")
                return None
        except Exception as e:
            if attempt < max_retries:
                continue
            else:
                logging.error(f"   ❌ Playwright error after {max_retries} attempts: {e}")
                import traceback
                logging.debug(traceback.format_exc())
                return None
    
    # If we get here, all retries failed
    logging.error(f"   ❌ Failed to fetch auction page after {max_retries} attempts")
    return None


def fetch_vehicle_detail_page(vehicle_link, vid, item_id, cookie, max_retries=3):
    """
    Fetch individual vehicle detail page HTML using Playwright.
    Extracts image URLs from the vehicle detail page.
    
    Args:
        vehicle_link (str): Vehicle detail link (e.g., "#/auction/vehicleDetail/H5G9T7GA/6629538")
        vid (str): Vehicle ID
        item_id (str): Item ID
        cookie (str): Authentication cookie
        max_retries (int): Maximum number of retry attempts (default: 3)
        
    Returns:
        tuple: (HTML content, list of image URLs) or (None, []) on error
    """
    # Ensure proper URL construction (vehicle_link might start with # or /)
    # For SPA routes with #, we need BASE_URL/#/path
    if vehicle_link.startswith('#'):
        # Ensure BASE_URL ends with / before adding # route
        base = BASE_URL.rstrip('/')
        url = f"{base}{vehicle_link}"
    elif vehicle_link.startswith('/'):
        url = f"{BASE_URL}{vehicle_link}"
    else:
        url = f"{BASE_URL}/{vehicle_link}"
    timeout_ms = 90000  # 90 seconds timeout
    
    for attempt in range(1, max_retries + 1):
        try:
            from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
            
            if attempt > 1:
                # Exponential backoff
                backoff_time = 2 ** attempt
                time.sleep(backoff_time)
            
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"
                )
                
                # Set cookies
                if cookie:
                    cookies_list = []
                    for cookie_pair in cookie.split(';'):
                        cookie_pair = cookie_pair.strip()
                        if '=' in cookie_pair:
                            name, value = cookie_pair.split('=', 1)
                            cookies_list.append({
                                'name': name.strip(),
                                'value': value.strip(),
                                'domain': 'auctions.cardekho.com',
                                'path': '/'
                            })
                    if cookies_list:
                        context.add_cookies(cookies_list)
                
                page = context.new_page()
                
                # Set extra headers
                headers = get_headers(cookie)
                page.set_extra_http_headers({
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Referer': f'{BASE_URL}/',
                })
                
                # Navigate to the page
                try:
                    page.goto(url, wait_until='domcontentloaded', timeout=timeout_ms)
                    page.wait_for_timeout(3000)  # Wait for content to load
                except PlaywrightTimeoutError as e:
                    browser.close()
                    if attempt < max_retries:
                        logging.warning(f"   ⚠️  Navigation timeout (attempt {attempt}/{max_retries}) for vehicle {vid}, will retry...")
                        continue
                    else:
                        logging.error(f"   ❌ Navigation timeout after {max_retries} attempts for vehicle {vid}: {e}")
                        return None, []
                
                # Wait for page content to load
                try:
                    page.wait_for_selector('img, .viewphoto, [ng-click*="viewPhotos"]', timeout=15000)
                except PlaywrightTimeoutError:
                    pass  # Continue anyway
                
                # Wait a bit for page to fully render
                page.wait_for_timeout(2000)
                
                # Try to click on "viewPhotos" link or main image to open gallery
                gallery_opened = False
                try:
                    # Look for "Click to view all photos" link
                    view_photos_link = page.query_selector('a.viewphoto, a[ng-click*="viewPhotos"], .viewphoto')
                    if view_photos_link:
                        view_photos_link.click()
                        # Wait for gallery to appear
                        try:
                            page.wait_for_selector('#imageGallery, .gallery, [data-src-pop]', timeout=5000)
                        except:
                            pass
                        page.wait_for_timeout(2000)  # Additional wait for images to load
                        gallery_opened = True
                    else:
                        # Try clicking on the main vehicle image
                        main_image = page.query_selector('img.vdp_img, img[ng-click*="viewPhotos"]')
                        if main_image:
                            main_image.click()
                            # Wait for gallery to appear
                            try:
                                page.wait_for_selector('#imageGallery, .gallery, [data-src-pop]', timeout=5000)
                            except:
                                pass
                            page.wait_for_timeout(2000)  # Additional wait for images to load
                            gallery_opened = True
                except Exception as e:
                    pass  # Gallery click failed, continue with HTML extraction
                
                # Get the rendered HTML (after gallery is opened if possible)
                html = page.content()
                
                # Extract image URLs from HTML using multiple methods
                image_urls = extract_image_urls_from_html(html)
                
                # Log gallery click result
                if gallery_opened:
                    if len(image_urls) > 0:
                        retry_text = f" (retry {attempt})" if attempt > 1 else ""
                        logging.info(f"   🖼️  Gallery opened{retry_text}: Found {len(image_urls)} image(s)")
                    else:
                        retry_text = f" (retry {attempt}/{max_retries})" if attempt < max_retries else f" (after {max_retries} attempts)"
                        logging.warning(f"   🖼️  Gallery opened{retry_text}: No images found")
                else:
                    if len(image_urls) > 0:
                        retry_text = f" (retry {attempt})" if attempt > 1 else ""
                        logging.info(f"   🖼️  Gallery not opened{retry_text}: Found {len(image_urls)} image(s) from HTML")
                    else:
                        retry_text = f" (retry {attempt}/{max_retries})" if attempt < max_retries else f" (after {max_retries} attempts)"
                        logging.warning(f"   🖼️  Gallery not opened{retry_text}: No images found")
                
                browser.close()
                
                return html, image_urls
                
        except PlaywrightTimeoutError as e:
            if attempt < max_retries:
                continue
            else:
                logging.error(f"   ❌ Timeout after {max_retries} attempts for {vid}")
                return None, []
        except Exception as e:
            if attempt < max_retries:
                continue
            else:
                logging.error(f"   ❌ Error after {max_retries} attempts for {vid}: {str(e)[:50]}")
                return None, []
    
    # If we get here, all retries failed
    logging.error(f"   ❌ Failed to fetch vehicle {vid} detail page after {max_retries} attempts")
    return None, []


def extract_image_urls_from_html(html_content):
    """
    Extract vehicle image URLs from HTML using multiple methods.
    Checks data-src-pop, data-src, data-thumb, and src attributes.
    Only extracts images from auctionscdn.cardekho.com/auctionuploads/
    
    Args:
        html_content (str): HTML content of vehicle detail page
        
    Returns:
        list: List of vehicle image URLs (full-size, no query params)
    """
    image_urls = []
    seen_urls = set()
    
    if not html_content:
        return image_urls
    
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Method 1: Extract from data-src-pop attributes (gallery full-size images)
        gallery_items = soup.find_all(attrs={'data-src-pop': True})
        for item in gallery_items:
            src = item.get('data-src-pop')
            if src and 'auctionscdn.cardekho.com/auctionuploads/' in src:
                clean_url = src.split('?')[0]
                if clean_url not in seen_urls:
                    image_urls.append(clean_url)
                    seen_urls.add(clean_url)
        
        # Method 2: Extract from data-src attributes
        data_src_items = soup.find_all(attrs={'data-src': True})
        for item in data_src_items:
            src = item.get('data-src')
            if src and 'auctionscdn.cardekho.com/auctionuploads/' in src:
                clean_url = src.split('?')[0]
                if clean_url not in seen_urls:
                    image_urls.append(clean_url)
                    seen_urls.add(clean_url)
        
        # Method 3: Extract from data-thumb attributes
        data_thumb_items = soup.find_all(attrs={'data-thumb': True})
        for item in data_thumb_items:
            src = item.get('data-thumb')
            if src and 'auctionscdn.cardekho.com/auctionuploads/' in src:
                clean_url = src.split('?')[0]
                if clean_url not in seen_urls:
                    image_urls.append(clean_url)
                    seen_urls.add(clean_url)
        
        # Method 4: Extract from img src attributes (fallback)
        img_tags = soup.find_all('img')
        for img in img_tags:
            src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
            if src and 'auctionscdn.cardekho.com/auctionuploads/' in src:
                clean_url = src.split('?')[0]
                if clean_url not in seen_urls:
                    image_urls.append(clean_url)
                    seen_urls.add(clean_url)
        
        # Sort to ensure consistent order
        image_urls.sort()
        
    except Exception as e:
        logging.warning(f"   ⚠️  Error extracting images from HTML: {e}")
    
    return image_urls


def extract_vehicle_links_from_auction_page(html_content):
    """
    Extract vehicle links (VID and item_id) from auction detail page HTML.
    
    Args:
        html_content (str): HTML content of auction detail page
        
    Returns:
        list: List of dicts with 'vid' and 'item_id' keys
    """
    vehicles = []
    
    if not html_content:
        return vehicles
    
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Method 1: Look for tr elements with id="auction_item_XXXXX"
        # Pattern: <tr id="auction_item_6629539">
        auction_items = soup.find_all('tr', id=re.compile(r'auction_item_\d+'))
        
        for item in auction_items:
            item_id_match = re.search(r'auction_item_(\d+)', item.get('id', ''))
            if not item_id_match:
                continue
            
            item_id = item_id_match.group(1)
            vid = None
            
            # Find VID in this row - look for div with class containing "title"
            vid_div = item.find('div', class_=re.compile(r'title'))
            if vid_div:
                vid_text = vid_div.get_text()
                vid_match = re.search(r'VID:\s*([A-Z0-9]+)', vid_text)
                if vid_match:
                    vid = vid_match.group(1)
            
            # Alternative: Extract from vehicle detail link
            if not vid:
                vehicle_link = item.find('a', href=re.compile(r'#/auction/vehicleDetail/'))
                if vehicle_link:
                    href = vehicle_link.get('href', '')
                    match = re.search(r'#/auction/vehicleDetail/([^/]+)/', href)
                    if match:
                        vid = match.group(1)
            
            if vid and item_id:
                # Check if we already have this vehicle
                if not any(v['item_id'] == item_id for v in vehicles):
                    vehicles.append({
                        'vid': vid,
                        'item_id': item_id
                    })
                    logging.debug(f"Found vehicle: VID={vid}, item_id={item_id}")
        
        # Method 2: Find all vehicle detail links (fallback)
        if not vehicles:
            vehicle_links = soup.find_all('a', href=re.compile(r'#/auction/vehicleDetail/'))
            
            for link in vehicle_links:
                href = link.get('href', '')
                match = re.search(r'#/auction/vehicleDetail/([^/]+)/(\d+)', href)
                if match:
                    vid = match.group(1)
                    item_id = match.group(2)
                    
                    if not any(v['item_id'] == item_id for v in vehicles):
                        vehicles.append({
                            'vid': vid,
                            'item_id': item_id
                        })
                        logging.debug(f"Found vehicle from link: VID={vid}, item_id={item_id}")
        
        logging.info(f"Extracted {len(vehicles)} vehicles from auction page")
        return vehicles
        
    except Exception as e:
        logging.error(f"Error extracting vehicle links: {e}")
        import traceback
        logging.error(traceback.format_exc())
        return vehicles


def extract_vehicle_details_from_listing(tr_element):
    """
    Extract vehicle details directly from auction listing page table row.
    This is more efficient than fetching individual vehicle pages.
    
    Args:
        tr_element: BeautifulSoup tr element containing vehicle data
        
    Returns:
        dict: Vehicle details or None on error
    """
    try:
        details = {}
        
        # Extract Make/Model from h2 title
        # Pattern: <h2><a href="#/auction/vehicleDetail/PRERKE4Z/6629539" title="Mahindra Bolero B6 (O) BS-VI">
        title_h2 = tr_element.find('h2')
        if title_h2:
            title_link = title_h2.find('a')
            if title_link:
                details['make_model'] = title_link.get_text().strip()
        
        # Extract Registration Number
        # Pattern: <li title="Registration Number" class="ng-binding">GJ34H5655</li>
        reg_li = tr_element.find('li', title="Registration Number")
        if reg_li:
            details['registration'] = reg_li.get_text().strip()
        
        # Extract Manufacturing Year
        # Pattern: <li title="Mfg Year" class="ng-binding"><span class="bullet"></span> 2022</li>
        year_li = tr_element.find('li', title="Mfg Year")
        if year_li:
            year_text = year_li.get_text().strip()
            year_match = re.search(r'(\d{4})', year_text)
            if year_match:
                details['year'] = year_match.group(1)
        
        # Extract Location
        # Pattern: <li title="Location" class="ng-binding"><span class="bullet"></span>Vadodara</li>
        location_li = tr_element.find('li', title="Location")
        if location_li:
            location_text = location_li.get_text().strip()
            location_text = re.sub(r'^[•\s]+', '', location_text)
            details['location'] = location_text
        
        # Extract Paper Status (Scrap/Without Paper)
        # Pattern: <li title="Scrap/Without Paper" class="with_rc ng-scope"><span class="bullet"></span>Without Paper</li>
        paper_li = tr_element.find('li', title="Scrap/Without Paper")
        if paper_li:
            paper_text = paper_li.get_text().strip()
            paper_text = re.sub(r'^[•\s]+', '', paper_text)
            details['paper_status'] = paper_text
        
        # Extract RC Status
        # Pattern: <li title="RC Available" class="ng-binding">RC: Without Papers</li>
        rc_li = tr_element.find('li', title="RC Available")
        if rc_li:
            rc_text = rc_li.get_text().strip()
            details['rc_status'] = rc_text.replace('RC:', '').strip()
        
        # Extract Transmission
        # Pattern: <li title="Transmission" class="ng-binding"><span class="bullet"></span>Manual</li>
        trans_li = tr_element.find('li', title="Transmission")
        if trans_li:
            trans_text = trans_li.get_text().strip()
            trans_text = re.sub(r'^[•\s]+', '', trans_text)
            details['transmission'] = trans_text
        
        # Extract Ownership
        # Pattern: <li title="Ownership" class="listsect ng-binding"><span class="bullet"></span>1st Owner</li>
        owner_li = tr_element.find('li', title="Ownership")
        if owner_li:
            owner_text = owner_li.get_text().strip()
            owner_text = re.sub(r'^[•\s]+', '', owner_text)
            details['ownership'] = owner_text
        
        # Extract Fuel Type
        # Pattern: <li title="Fuel Type" class="ng-binding"><span class="bullet"></span>Diesel</li>
        fuel_li = tr_element.find('li', title="Fuel Type")
        if fuel_li:
            fuel_text = fuel_li.get_text().strip()
            fuel_text = re.sub(r'^[•\s]+', '', fuel_text)
            details['fuel_type'] = fuel_text
        
        return details if details.get('registration') else None
        
    except Exception as e:
        logging.error(f"Error extracting vehicle details from listing: {e}")
        return None


def extract_vehicle_details(html_content):
    """
    Extract vehicle details from vehicle detail page HTML (fallback method).
    
    Args:
        html_content (str): HTML content of vehicle detail page
        
    Returns:
        dict: Vehicle details or None on error
    """
    if not html_content:
        return None
    
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        details = {}
        
        # Extract Make/Model from h2 title
        title_h2 = soup.find('h2', class_=re.compile(r'title_vdp|title'))
        if title_h2:
            title_link = title_h2.find('a')
            if title_link:
                details['make_model'] = title_link.get_text().strip()
            else:
                details['make_model'] = title_h2.get_text().strip()
        
        # Extract Registration Number
        reg_li = soup.find('li', title="Registration Number")
        if reg_li:
            details['registration'] = reg_li.get_text().strip()
        else:
            reg_div = soup.find('div', class_='specdesc', string=re.compile(r'GJ\d+[A-Z]?\d+[A-Z]?'))
            if reg_div:
                details['registration'] = reg_div.get_text().strip()
        
        # Extract Manufacturing Year
        year_li = soup.find('li', title="Mfg Year")
        if year_li:
            year_text = year_li.get_text().strip()
            year_match = re.search(r'(\d{4})', year_text)
            if year_match:
                details['year'] = year_match.group(1)
        
        # Extract Location
        location_li = soup.find('li', title="Location")
        if location_li:
            location_text = location_li.get_text().strip()
            location_text = re.sub(r'^[•\s]+', '', location_text)
            details['location'] = location_text
        
        # Extract Paper Status
        paper_li = soup.find('li', title="Scrap/Without Paper")
        if paper_li:
            paper_text = paper_li.get_text().strip()
            paper_text = re.sub(r'^[•\s]+', '', paper_text)
            details['paper_status'] = paper_text
        
        # Extract RC Status
        rc_li = soup.find('li', title="RC Available")
        if rc_li:
            rc_text = rc_li.get_text().strip()
            details['rc_status'] = rc_text.replace('RC:', '').strip()
        
        # Extract Transmission
        trans_li = soup.find('li', title="Transmission")
        if trans_li:
            trans_text = trans_li.get_text().strip()
            trans_text = re.sub(r'^[•\s]+', '', trans_text)
            details['transmission'] = trans_text
        
        # Extract Ownership
        owner_li = soup.find('li', title="Ownership")
        if owner_li:
            owner_text = owner_li.get_text().strip()
            owner_text = re.sub(r'^[•\s]+', '', owner_text)
            details['ownership'] = owner_text
        
        # Extract Fuel Type
        fuel_li = soup.find('li', title="Fuel Type")
        if fuel_li:
            fuel_text = fuel_li.get_text().strip()
            fuel_text = re.sub(r'^[•\s]+', '', fuel_text)
            details['fuel_type'] = fuel_text
        
        return details if details.get('registration') else None
        
    except Exception as e:
        logging.error(f"Error extracting vehicle details: {e}")
        return None


def extract_vehicle_links_from_auction_html(html_content):
    """
    Extract vehicle links and details from auction detail page HTML.
    Looks for: <a href="#/auction/vehicleDetail/PLA86RQU/6629629">
    Also extracts vehicle details from the listing page (registration, year, location, etc.)
    
    Args:
        html_content (str): HTML content of auction detail page
        
    Returns:
        list: List of dicts with 'vid', 'item_id', 'vehicle_link', and vehicle details
    """
    vehicles = []
    
    if not html_content:
        return vehicles
    
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Method 1: Find tr elements with id="auction_item_XXXXX" (most reliable)
        # This gives us both the link and the details in one place
        auction_items = soup.find_all('tr', id=re.compile(r'auction_item_\d+'))
        
        seen_vehicles = set()
        
        for tr_item in auction_items:
            item_id_match = re.search(r'auction_item_(\d+)', tr_item.get('id', ''))
            if not item_id_match:
                continue
            
            item_id = item_id_match.group(1)
            vehicle_data = {'item_id': item_id}
            
            # Extract vehicle detail link
            vehicle_link_tag = tr_item.find('a', href=re.compile(r'#/auction/vehicleDetail/'))
            if vehicle_link_tag:
                href = vehicle_link_tag.get('href', '')
                match = re.search(r'#/auction/vehicleDetail/([^/]+)/(\d+)', href)
                if match:
                    vid = match.group(1)
                    vehicle_data['vid'] = vid
                    vehicle_data['vehicle_link'] = href  # Store the full link
                    
                    # Extract Make/Model from title
                    title_text = vehicle_link_tag.get_text(strip=True)
                    if title_text:
                        vehicle_data['make_model'] = title_text
            
            # If no VID from link, try to get from title div
            if 'vid' not in vehicle_data:
                vid_div = tr_item.find('div', class_=re.compile(r'title'))
                if vid_div:
                    vid_text = vid_div.get_text()
                    vid_match = re.search(r'VID:\s*([A-Z0-9]+)', vid_text)
                    if vid_match:
                        vehicle_data['vid'] = vid_match.group(1)
            
            # Extract Registration Number
            reg_li = tr_item.find('li', title="Registration Number")
            if reg_li:
                vehicle_data['registration_number'] = reg_li.get_text(strip=True)
            
            # Extract Manufacturing Year
            year_li = tr_item.find('li', title="Mfg Year")
            if year_li:
                year_text = year_li.get_text(strip=True)
                # Remove bullet and extract year
                year_text = re.sub(r'^[•\s]+', '', year_text)
                vehicle_data['manufacturing_year'] = year_text
            
            # Extract Location
            location_li = tr_item.find('li', title="Location")
            if location_li:
                location_text = location_li.get_text(strip=True)
                location_text = re.sub(r'^[•\s]+', '', location_text)
                vehicle_data['location'] = location_text
            
            # Extract Paper Status (Scrap/Without Paper)
            paper_li = tr_item.find('li', title="Scrap/Without Paper")
            if paper_li:
                paper_text = paper_li.get_text(strip=True)
                paper_text = re.sub(r'^[•\s]+', '', paper_text)
                vehicle_data['paper_status'] = paper_text
            
            # Extract RC Status
            rc_li = tr_item.find('li', title="RC Available")
            if rc_li:
                rc_text = rc_li.get_text(strip=True)
                # Remove "RC:" prefix if present
                rc_text = re.sub(r'^RC:\s*', '', rc_text, flags=re.IGNORECASE)
                vehicle_data['rc_status'] = rc_text.strip()
            
            # Extract Transmission
            trans_li = tr_item.find('li', title="Transmission")
            if trans_li:
                trans_text = trans_li.get_text(strip=True)
                trans_text = re.sub(r'^[•\s]+', '', trans_text)
                vehicle_data['transmission'] = trans_text
            
            # Extract Ownership
            owner_li = tr_item.find('li', title="Ownership")
            if owner_li:
                owner_text = owner_li.get_text(strip=True)
                owner_text = re.sub(r'^[•\s]+', '', owner_text)
                vehicle_data['ownership'] = owner_text
            
            # Extract Fuel Type
            fuel_li = tr_item.find('li', title="Fuel Type")
            if fuel_li:
                fuel_text = fuel_li.get_text(strip=True)
                fuel_text = re.sub(r'^[•\s]+', '', fuel_text)
                vehicle_data['fuel_type'] = fuel_text
            
            # Only add if we have at least VID and item_id
            if vehicle_data.get('vid') and vehicle_data.get('item_id'):
                vehicle_key = f"{vehicle_data['vid']}_{vehicle_data['item_id']}"
                if vehicle_key not in seen_vehicles:
                    seen_vehicles.add(vehicle_key)
                    vehicles.append(vehicle_data)
                    logging.debug(f"Found vehicle: VID={vehicle_data.get('vid')}, item_id={item_id}, reg={vehicle_data.get('registration_number', 'N/A')}")
        
        # Extract Yard Name and Yard Location from download table (auctionDetailDownload)
        # The download table structure:
        # Index 0: VID, Index 1: Registration, Index 2-4: empty, Index 5: Make, Index 6: Model,
        # Index 7: Variant, Index 8: Mfg Year, Index 9: Fuel Type, Index 10: Owner Serial,
        # Index 11: Yard Name, Index 12: Yard Address
        download_table_rows = soup.find_all('tr', {'ng-repeat': re.compile(r'det in auctionDetailDownload')})
        
        # Create a mapping of registration number to yard details
        yard_details_map = {}
        for download_row in download_table_rows:
            tds = download_row.find_all('td', class_='ng-binding')
            if len(tds) >= 13:  # Need at least 13 columns (0-12)
                # Extract registration number (index 1)
                reg_from_table = tds[1].get_text(strip=True) if len(tds) > 1 else ''
                # Yard Name is at index 11, Yard Address is at index 12
                yard_name = tds[11].get_text(strip=True) if len(tds) > 11 else ''
                yard_location = tds[12].get_text(strip=True) if len(tds) > 12 else ''
                
                # Use registration number as key (more reliable than VID)
                if reg_from_table:
                    yard_details_map[reg_from_table] = {
                        'yard_name': yard_name,
                        'yard_location': yard_location
                    }
        
        # Match yard details to vehicles by registration number
        for vehicle in vehicles:
            reg_no = vehicle.get('registration_number', '')
            if reg_no and reg_no in yard_details_map:
                vehicle['yard_name'] = yard_details_map[reg_no]['yard_name']
                vehicle['yard_location'] = yard_details_map[reg_no]['yard_location']
        
        # Method 2: Fallback - Find all vehicle detail links if Method 1 didn't work
        if not vehicles:
            vehicle_links = soup.find_all('a', href=re.compile(r'#/auction/vehicleDetail/'))
            
            for link in vehicle_links:
                href = link.get('href', '')
                match = re.search(r'#/auction/vehicleDetail/([^/]+)/(\d+)', href)
                if match:
                    vid = match.group(1)
                    item_id = match.group(2)
                    
                    vehicle_key = f"{vid}_{item_id}"
                    if vehicle_key not in seen_vehicles:
                        seen_vehicles.add(vehicle_key)
                        vehicles.append({
                            'vid': vid,
                            'item_id': item_id,
                            'vehicle_link': href
                        })
                        logging.debug(f"Found vehicle from link: VID={vid}, item_id={item_id}")
        
        logging.info(f"Extracted {len(vehicles)} vehicle links from auction page")
        return vehicles
        
    except Exception as e:
        logging.error(f"Error extracting vehicle links: {e}")
        import traceback
        logging.error(traceback.format_exc())
        return vehicles


def update_auction_paths_with_vehicles():
    """
    Step 3a: Extract vehicle links from each auction detail page
    and update the auction_paths.json file with vehicle information.
    """
    load_dotenv()
    cookie = os.getenv("CAR_DEKHO_COOKIE")
    
    if not cookie:
        logging.error("CAR_DEKHO_COOKIE not found in .env file")
        return False
    
    paths_file = "downloads/cardekho_auction_paths.json"
    if not os.path.exists(paths_file):
        logging.error(f"Auction paths file not found: {paths_file}")
        logging.error("Please run filter_insurance_business() first")
        return False
    
    logging.info("")
    logging.info("STEP 3a: EXTRACTING VEHICLE DATA")
    logging.info("")
    logging.info("🎯 FILTER CRITERIA:")
    logging.info("   ✓ Registration: Gujarat (GJ) only")
    logging.info("   ✓ RC Status: 'With Papers' only")
    logging.info("")
    
    # Load auction paths
    with open(paths_file, "r", encoding="utf-8") as f:
        auctions = json.load(f)
    
    total_expected_vehicles = sum(int(auction.get("vehicle_count", 0) or 0) for auction in auctions)
    logging.info(f"📦 PROCESSING: {len(auctions)} auctions")
    logging.info(f"📊 Total vehicles in auctions: {total_expected_vehicles}")
    logging.info("")
    
    total_vehicles_found = 0
    total_vehicles_filtered = 0
    failed_auctions = []  # Track failed auctions for manual retry
    timeout_auctions = []  # Track timeout auctions for retry
    
    # Process each auction and extract vehicle links
    for idx, auction in enumerate(auctions, 1):
        slug = auction.get('slug')
        title = auction.get('title', 'Unknown')
        vehicle_count = auction.get('vehicle_count', 0)
        auction_id = auction.get('auction_id', 'Unknown')
        
        if not slug:
            logging.warning(f"   ⚠️  Skipping auction {idx}: No slug found")
            continue
        
        logging.info("")
        logging.info(f"AUCTION {idx}/{len(auctions)}: {title} (ID: {auction_id}, Expected: {vehicle_count} vehicles)")
        
        auction_html = fetch_auction_detail_page(slug, auction_id, cookie)
        if not auction_html:
            logging.warning(f"   ❌ Failed to fetch auction page after all retries")
            auction['vehicles'] = []  # Add empty vehicles array
            auction['gj_vehicle_count'] = 0
            auction['status'] = "failed"
            auction['summary'] = f"Status: FAILED - Expected: {vehicle_count}, Loaded: 0, Filtered: 0, With Data: 0, With Images: 0"
            auction['fetch_failed'] = True  # Mark as failed
            auction['fetch_error'] = "Failed after all retry attempts"
            
            # Track failed auction for manual retry
            failed_auctions.append({
                'auction_id': auction_id,
                'title': title,
                'slug': slug,
                'vehicle_count': vehicle_count,
                'index': idx,
                'error': 'Failed to fetch after all retry attempts'
            })
            
            # Save failed auctions to file
            failed_file = "downloads/cardekho_failed_auctions.json"
            os.makedirs("downloads", exist_ok=True)
            with open(failed_file, "w", encoding="utf-8") as f:
                json.dump(failed_auctions, f, indent=4, ensure_ascii=False)
            logging.info(f"   📝 Failed auction tracked in {failed_file}")
            
            # Save progress even for failed auctions
            with open(paths_file, "w", encoding="utf-8") as f:
                json.dump(auctions, f, indent=4, ensure_ascii=False)
            
            time.sleep(2)  # Brief delay before next auction
            continue
        
        # Extract vehicle links from HTML
        all_vehicles = extract_vehicle_links_from_auction_html(auction_html)
        
        # Check if this looks like a timeout (expected vehicles but found 0)
        is_timeout = False
        if int(vehicle_count or 0) > 0 and len(all_vehicles) == 0:
            is_timeout = True
            logging.warning(f"   ⚠️  Timeout: Expected {vehicle_count} vehicles but found 0")
            # Track for retry
            timeout_auctions.append({
                'auction_id': auction_id,
                'title': title,
                'slug': slug,
                'vehicle_count': vehicle_count,
                'index': idx,
                'auction': auction  # Store reference to update later
            })
            # Set status for timeout
            auction['status'] = "timeout"
            auction['summary'] = f"Status: TIMEOUT - Expected: {vehicle_count}, Loaded: 0, Filtered: 0, With Data: 0, With Images: 0"
            auction['vehicles'] = []
            auction['gj_vehicle_count'] = 0
            # Save and continue
            with open(paths_file, "w", encoding="utf-8") as f:
                json.dump(auctions, f, indent=4, ensure_ascii=False)
            logging.info("   " + "─" * 56)
            continue
        
        # Filter: Only Gujarat (GJ) vehicles with "With Papers" RC status
        filtered_vehicles = []
        gj_only_count = 0
        with_papers_count = 0
        
        for vehicle in all_vehicles:
            reg_no = vehicle.get('registration_number', '')
            rc_status = vehicle.get('rc_status', '')
            
            # Check if it's a Gujarat vehicle
            is_gj = reg_no and reg_no.upper().startswith('GJ')
            # Check if RC status is "With Papers" (case-insensitive)
            is_with_papers = rc_status and 'with papers' in rc_status.lower()
            
            # Count statistics
            if is_gj:
                gj_only_count += 1
            if is_with_papers:
                with_papers_count += 1
            
            # Both conditions must be met: GJ + With Papers
            if is_gj and is_with_papers:
                filtered_vehicles.append(vehicle)
        
        filtered_out = len(all_vehicles) - len(filtered_vehicles)
        total_vehicles_filtered += filtered_out
        
        if len(filtered_vehicles) == 0:
            logging.warning(f"   ⚠️  No vehicles match filters (GJ + With Papers)")
        
        # Extract images for each filtered vehicle with retry logic
        vehicles_with_images = 0
        vehicles_without_images = []
        if len(filtered_vehicles) > 0:
            logging.info("")
            logging.info(f"   📸 EXTRACTING VEHICLE IMAGES ({len(filtered_vehicles)} vehicles)...")
            for vehicle_idx, vehicle in enumerate(filtered_vehicles, 1):
                vid = vehicle.get('vid')
                item_id = vehicle.get('item_id')
                vehicle_link = vehicle.get('vehicle_link', '')
                reg = vehicle.get('registration_number', 'N/A')
                
                if not vid or not item_id:
                    logging.warning(f"      ⚠️  Vehicle {vehicle_idx}: Missing VID or item_id, skipping")
                    vehicle['vehicleimages'] = []
                    vehicles_without_images.append({'reg': reg, 'reason': 'Missing VID or item_id'})
                    continue
                
                logging.info(f"      [{vehicle_idx}/{len(filtered_vehicles)}] {reg} (VID: {vid})...")
                
                # Fetch vehicle detail page and extract images with retry
                image_urls = []
                max_image_retries = 2  # Retry once if no images found
                for img_retry in range(1, max_image_retries + 1):
                    try:
                        html, image_urls = fetch_vehicle_detail_page(vehicle_link, vid, item_id, cookie, max_retries=3)
                        
                        if image_urls and len(image_urls) > 0:
                            vehicle['vehicleimages'] = image_urls
                            filtered_vehicles[vehicle_idx - 1]['vehicleimages'] = image_urls
                            vehicles_with_images += 1
                            if img_retry > 1:
                                logging.info(f"         ✅ Found {len(image_urls)} image(s) on retry {img_retry}")
                            break
                        else:
                            if img_retry < max_image_retries:
                                logging.warning(f"         ⚠️  No images found, retrying ({img_retry}/{max_image_retries})...")
                                time.sleep(2)  # Wait before retry
                            else:
                                vehicle['vehicleimages'] = []
                                filtered_vehicles[vehicle_idx - 1]['vehicleimages'] = []
                                vehicles_without_images.append({'reg': reg, 'vid': vid, 'reason': 'No images found after retries'})
                    except Exception as e:
                        if img_retry < max_image_retries:
                            logging.warning(f"         ⚠️  Error (retry {img_retry}/{max_image_retries}): {e}")
                            time.sleep(2)
                        else:
                            logging.error(f"         ❌ Error extracting images for {reg}: {e}")
                            vehicle['vehicleimages'] = []
                            filtered_vehicles[vehicle_idx - 1]['vehicleimages'] = []
                            vehicles_without_images.append({'reg': reg, 'vid': vid, 'reason': f'Error: {str(e)[:50]}'})
                
                # Small delay between vehicle image fetches
                time.sleep(1)
            
            # Log summary of image extraction
            if vehicles_without_images:
                logging.warning(f"   ⚠️  {len(vehicles_without_images)} vehicle(s) without images:")
                for v in vehicles_without_images[:5]:  # Show first 5
                    logging.warning(f"      • {v.get('reg', 'N/A')}: {v.get('reason', 'Unknown')}")
                if len(vehicles_without_images) > 5:
                    logging.warning(f"      ... and {len(vehicles_without_images) - 5} more")
        
        # Calculate status metrics
        expected_vehicles = vehicle_count
        loaded_vehicles = len(all_vehicles)
        filtered_count = len(filtered_vehicles)
        vehicles_with_data = sum(1 for v in filtered_vehicles if v.get('registration_number') and v.get('make_model'))
        vehicles_with_images_count = sum(1 for v in filtered_vehicles if v.get('vehicleimages') and len(v.get('vehicleimages', [])) > 0)
        
        # Determine status
        if auction_html is None:
            status = "failed"
        elif loaded_vehicles == 0 and expected_vehicles > 0:
            status = "timeout"
        elif expected_vehicles == loaded_vehicles and filtered_count > 0 and vehicles_with_images_count == filtered_count:
            status = "complete"
        elif filtered_count > 0 and vehicles_with_images_count == filtered_count:
            status = "partial"
        elif filtered_count > 0:
            status = "partial"
        else:
            status = "no_match"
        
        # Create summary sentence
        summary = f"Status: {status.upper()} - Expected: {expected_vehicles}, Loaded: {loaded_vehicles}, Filtered: {filtered_count}, With Data: {vehicles_with_data}, With Images: {vehicles_with_images_count}"
        
        # Update auction with status and summary
        auction['gj_vehicle_count'] = filtered_count
        auction['vehicles'] = filtered_vehicles
        auction['status'] = status
        auction['summary'] = summary
        
        total_vehicles_found += filtered_count
        
        # Log summary
        logging.info(f"   📊 {summary}")
        
        # Save after each auction (incremental save to ensure data is persisted)
        with open(paths_file, "w", encoding="utf-8") as f:
            json.dump(auctions, f, indent=4, ensure_ascii=False)
        
        logging.info(f"   💾 Saved ({idx}/{len(auctions)} processed)")
        
        # Delay between requests
        time.sleep(2)
    
    # Retry timeout auctions once
    if timeout_auctions:
        logging.info("")
        logging.info(f"RETRYING TIMEOUT AUCTIONS: {len(timeout_auctions)} auction(s)")
        logging.info("")
        
        retry_successful = 0
        for retry_idx, timeout_auction in enumerate(timeout_auctions, 1):
            auction = timeout_auction['auction']
            slug = timeout_auction['slug']
            title = timeout_auction['title']
            auction_id = timeout_auction['auction_id']
            vehicle_count = timeout_auction['vehicle_count']
            
            logging.info(f"RETRY {retry_idx}/{len(timeout_auctions)}: {title} (ID: {auction_id})")
            
            # Fetch auction detail page again
            auction_html = fetch_auction_detail_page(slug, auction_id, cookie)
            if not auction_html:
                logging.warning(f"   ❌ Retry failed: Still unable to fetch auction page")
                continue
            
            # Extract vehicle links from HTML
            logging.info("   🔍 Extracting vehicle data from page...")
            all_vehicles = extract_vehicle_links_from_auction_html(auction_html)
            
            if len(all_vehicles) == 0:
                logging.warning(f"   ⚠️  Retry found 0 vehicles (may still be timeout)")
                continue
            
            logging.info(f"   ✅ Retry successful! Found {len(all_vehicles)} vehicles")
            retry_successful += 1
            
            # Filter: Only Gujarat (GJ) vehicles with "With Papers" RC status
            filtered_vehicles = []
            gj_only_count = 0
            with_papers_count = 0
            
            for vehicle in all_vehicles:
                reg_no = vehicle.get('registration_number', '')
                rc_status = vehicle.get('rc_status', '')
                
                is_gj = reg_no and reg_no.upper().startswith('GJ')
                is_with_papers = rc_status and 'with papers' in rc_status.lower()
                
                if is_gj:
                    gj_only_count += 1
                if is_with_papers:
                    with_papers_count += 1
                
                if is_gj and is_with_papers:
                    filtered_vehicles.append(vehicle)
            
            # Extract images for filtered vehicles with retry
            vehicles_with_images_retry = 0
            if len(filtered_vehicles) > 0:
                logging.info(f"   📸 Extracting images ({len(filtered_vehicles)} vehicles)...")
                for vehicle_idx, vehicle in enumerate(filtered_vehicles, 1):
                    vid = vehicle.get('vid')
                    item_id = vehicle.get('item_id')
                    vehicle_link = vehicle.get('vehicle_link', '')
                    reg = vehicle.get('registration_number', 'N/A')
                    
                    if not vid or not item_id:
                        vehicle['vehicleimages'] = []
                        continue
                    
                    # Retry logic for images
                    image_urls = []
                    max_image_retries = 2
                    for img_retry in range(1, max_image_retries + 1):
                        try:
                            html, image_urls = fetch_vehicle_detail_page(vehicle_link, vid, item_id, cookie, max_retries=3)
                            if image_urls and len(image_urls) > 0:
                                vehicle['vehicleimages'] = image_urls
                                filtered_vehicles[vehicle_idx - 1]['vehicleimages'] = image_urls
                                vehicles_with_images_retry += 1
                                break
                            elif img_retry < max_image_retries:
                                time.sleep(2)
                        except Exception as e:
                            if img_retry < max_image_retries:
                                time.sleep(2)
                            else:
                                vehicle['vehicleimages'] = []
                                filtered_vehicles[vehicle_idx - 1]['vehicleimages'] = []
                    
                    if not image_urls:
                        vehicle['vehicleimages'] = []
                        filtered_vehicles[vehicle_idx - 1]['vehicleimages'] = []
                    
                    time.sleep(1)
            
            # Update status for retry
            vehicles_with_data_retry = sum(1 for v in filtered_vehicles if v.get('registration_number') and v.get('make_model'))
            expected_vehicles_retry = vehicle_count
            loaded_vehicles_retry = len(all_vehicles)
            
            if loaded_vehicles_retry == 0 and expected_vehicles_retry > 0:
                status_retry = "timeout"
            elif expected_vehicles_retry == loaded_vehicles_retry and len(filtered_vehicles) > 0 and vehicles_with_images_retry == len(filtered_vehicles):
                status_retry = "complete"
            elif len(filtered_vehicles) > 0 and vehicles_with_images_retry == len(filtered_vehicles):
                status_retry = "partial"
            elif len(filtered_vehicles) > 0:
                status_retry = "partial"
            else:
                status_retry = "no_match"
            
            # Create summary sentence
            summary_retry = f"Status: {status_retry.upper()} - Expected: {expected_vehicles_retry}, Loaded: {loaded_vehicles_retry}, Filtered: {len(filtered_vehicles)}, With Data: {vehicles_with_data_retry}, With Images: {vehicles_with_images_retry}"
            
            # Update the auction in the list
            auction['gj_vehicle_count'] = len(filtered_vehicles)
            auction['vehicles'] = filtered_vehicles
            auction['status'] = status_retry
            auction['summary'] = summary_retry
            auction['retry_successful'] = True
            
            # Log summary
            logging.info(f"   📊 {summary_retry}")
            total_vehicles_found += len(filtered_vehicles)
            
            # Save progress after each retry
            with open(paths_file, "w", encoding="utf-8") as f:
                json.dump(auctions, f, indent=4, ensure_ascii=False)
            
            logging.info(f"   💾 Updated")
            
            time.sleep(2)  # Delay between retries
        
        logging.info("")
        logging.info(f"✅ Retry complete: {retry_successful}/{len(timeout_auctions)} auctions successfully retried")
        logging.info("")
    
    # Retry partial and failed auctions 3 times
    partial_failed_auctions = [auction for auction in auctions if auction.get('status') in ['partial', 'failed']]
    if partial_failed_auctions:
        logging.info("")
        logging.info(f"RETRYING PARTIAL/FAILED AUCTIONS: {len(partial_failed_auctions)} auction(s) (3 attempts)")
        logging.info("")
        
        for retry_round in range(1, 4):  # 3 retry rounds
            logging.info(f"Retry Round {retry_round}/3")
            retry_improved = 0
            
            for auction in partial_failed_auctions[:]:  # Copy list to modify during iteration
                if auction.get('status') in ['complete', 'no_match']:
                    # Status improved, remove from retry list
                    partial_failed_auctions.remove(auction)
                    continue
                
                slug = auction.get('slug')
                auction_id = auction.get('auction_id')
                title = auction.get('title', 'Unknown')
                vehicle_count = auction.get('vehicle_count', 0)
                
                if not slug:
                    continue
                
                logging.info(f"   Retry {retry_round}/3: {title} (ID: {auction_id})")
                
                # Fetch auction detail page
                auction_html = fetch_auction_detail_page(slug, auction_id, cookie)
                if not auction_html:
                    continue
                
                # Extract vehicle links
                all_vehicles = extract_vehicle_links_from_auction_html(auction_html)
                
                if len(all_vehicles) == 0:
                    continue
                
                # Filter: Only Gujarat (GJ) vehicles with "With Papers" RC status
                filtered_vehicles = []
                for vehicle in all_vehicles:
                    reg_no = vehicle.get('registration_number', '')
                    rc_status = vehicle.get('rc_status', '')
                    is_gj = reg_no and reg_no.upper().startswith('GJ')
                    is_with_papers = rc_status and 'with papers' in rc_status.lower()
                    if is_gj and is_with_papers:
                        filtered_vehicles.append(vehicle)
                
                # Extract images for filtered vehicles with retry
                vehicles_with_images_retry = 0
                for vehicle in filtered_vehicles:
                    vid = vehicle.get('vid')
                    item_id = vehicle.get('item_id')
                    vehicle_link = vehicle.get('vehicle_link', '')
                    
                    if not vid or not item_id:
                        vehicle['vehicleimages'] = []
                        continue
                    
                    # Retry logic for images
                    image_urls = []
                    max_image_retries = 2
                    for img_retry in range(1, max_image_retries + 1):
                        try:
                            html, image_urls = fetch_vehicle_detail_page(vehicle_link, vid, item_id, cookie, max_retries=3)
                            if image_urls and len(image_urls) > 0:
                                vehicle['vehicleimages'] = image_urls
                                vehicles_with_images_retry += 1
                                break
                            elif img_retry < max_image_retries:
                                time.sleep(2)
                        except Exception:
                            if img_retry < max_image_retries:
                                time.sleep(2)
                            else:
                                vehicle['vehicleimages'] = []
                    
                    if not image_urls:
                        vehicle['vehicleimages'] = []
                    
                    time.sleep(1)
                
                # Calculate metrics
                expected_vehicles_retry = vehicle_count
                loaded_vehicles_retry = len(all_vehicles)
                filtered_count_retry = len(filtered_vehicles)
                vehicles_with_data_retry = sum(1 for v in filtered_vehicles if v.get('registration_number') and v.get('make_model'))
                vehicles_with_images_count_retry = sum(1 for v in filtered_vehicles if v.get('vehicleimages') and len(v.get('vehicleimages', [])) > 0)
                
                # Determine status
                if loaded_vehicles_retry == 0 and expected_vehicles_retry > 0:
                    status_retry = "timeout"
                elif expected_vehicles_retry == loaded_vehicles_retry and filtered_count_retry > 0 and vehicles_with_images_count_retry == filtered_count_retry:
                    status_retry = "complete"
                elif filtered_count_retry > 0 and vehicles_with_images_count_retry == filtered_count_retry:
                    status_retry = "partial"
                elif filtered_count_retry > 0:
                    status_retry = "partial"
                else:
                    status_retry = "no_match"
                
                # Create summary
                summary_retry = f"Status: {status_retry.upper()} - Expected: {expected_vehicles_retry}, Loaded: {loaded_vehicles_retry}, Filtered: {filtered_count_retry}, With Data: {vehicles_with_data_retry}, With Images: {vehicles_with_images_count_retry}"
                
                # Update auction
                old_status = auction.get('status')
                auction['gj_vehicle_count'] = filtered_count_retry
                auction['vehicles'] = filtered_vehicles
                auction['status'] = status_retry
                auction['summary'] = summary_retry
                
                if status_retry != old_status:
                    retry_improved += 1
                    logging.info(f"   ✅ Status improved: {old_status} → {status_retry}")
                else:
                    logging.info(f"   📊 {summary_retry}")
                
                # Save progress
                with open(paths_file, "w", encoding="utf-8") as f:
                    json.dump(auctions, f, indent=4, ensure_ascii=False)
                
                time.sleep(2)
            
            logging.info(f"   Round {retry_round} complete: {retry_improved} auction(s) improved")
            
            # If no more partial/failed auctions, break
            if not partial_failed_auctions:
                break
            
            if retry_round < 3:
                logging.info("")
                time.sleep(3)  # Wait before next round
    
    # Final summary
    logging.info("")
    logging.info("EXTRACTION COMPLETE!")
    logging.info(f"Auctions processed: {len(auctions)}, Vehicles found: {total_vehicles_found}, Excluded: {total_vehicles_filtered}")
    if timeout_auctions:
        logging.info(f"Timeout auctions retried: {len(timeout_auctions)}")
    if failed_auctions:
        logging.warning(f"Failed auctions: {len(failed_auctions)}")
    partial_failed_final = [a for a in auctions if a.get('status') in ['partial', 'failed']]
    if partial_failed_final:
        logging.warning(f"Partial/Failed auctions remaining: {len(partial_failed_final)}")
    logging.info(f"Data saved to: {paths_file}")
    logging.info("")
    
    return True


def scrape_cardekho_vehicles():
    """
    Step 3b: Main function to scrape CarDekho vehicle details.
    Reads auction paths file (with vehicle links) and scrapes vehicle details.
    """
    load_dotenv()
    cookie = os.getenv("CAR_DEKHO_COOKIE")
    
    if not cookie:
        logging.error("CAR_DEKHO_COOKIE not found in .env file")
        return False
    
    paths_file = "downloads/cardekho_auction_paths.json"
    if not os.path.exists(paths_file):
        logging.error(f"Auction paths file not found: {paths_file}")
        logging.error("Please run update_auction_paths_with_vehicles() first")
        return False
    
    logging.info("=" * 60)
    logging.info("STEP 3b: Scraping CarDekho vehicle details")
    logging.info("=" * 60)
    
    # Load auction paths with vehicle links
    with open(paths_file, "r", encoding="utf-8") as f:
        auctions = json.load(f)
    
    base_dir = "downloads/car_dekho"
    os.makedirs(base_dir, exist_ok=True)
    
    total_vehicles = 0
    successful_scrapes = 0
    
    # Process each auction's vehicles
    for auction in auctions:
        title = auction.get('title', 'Unknown')
        vehicles = auction.get('vehicles', [])
        
        if not vehicles:
            continue
        
        logging.info(f"Processing {len(vehicles)} vehicles from auction: {title}")
        
        # Process each vehicle
        for vehicle in vehicles:
            vid = vehicle.get('vid')
            item_id = vehicle.get('item_id')
            
            if not vid or not item_id:
                logging.warning(f"Skipping vehicle: missing VID or item_id")
                continue
            
            total_vehicles += 1
            
            # Fetch vehicle detail page
            vehicle_html = fetch_vehicle_detail_page(vid, item_id, cookie)
            if not vehicle_html:
                logging.warning(f"Failed to fetch vehicle detail page: {vid}/{item_id}")
                time.sleep(2)
                continue
            
            # Extract vehicle details
            details = extract_vehicle_details(vehicle_html)
            
            if not details or not details.get('registration'):
                logging.warning(f"Failed to extract details for vehicle {vid}/{item_id}")
                time.sleep(2)
                continue
            
            # Sanitize registration number for folder name
            reg_no = re.sub(r'[^A-Za-z0-9]', '_', details['registration'].strip().upper())
            
            # Create vehicle folder
            vehicle_dir = os.path.join(base_dir, reg_no)
            os.makedirs(vehicle_dir, exist_ok=True)
            
            # Save metadata
            metadata_file = os.path.join(vehicle_dir, "metadata.txt")
            with open(metadata_file, "w", encoding="utf-8") as f:
                f.write("=== VEHICLE DETAILS ===\n\n")
                
                if details.get('make_model'):
                    f.write(f"Make/Model: {details['make_model']}\n")
                if details.get('registration'):
                    f.write(f"Registration Number: {details['registration']}\n")
                if details.get('year'):
                    f.write(f"Manufacturing Year: {details['year']}\n")
                if details.get('location'):
                    f.write(f"Location: {details['location']}\n")
                if details.get('paper_status'):
                    f.write(f"Paper Status: {details['paper_status']}\n")
                if details.get('rc_status'):
                    f.write(f"RC Status: {details['rc_status']}\n")
                if details.get('transmission'):
                    f.write(f"Transmission: {details['transmission']}\n")
                if details.get('ownership'):
                    f.write(f"Ownership: {details['ownership']}\n")
                if details.get('fuel_type'):
                    f.write(f"Fuel Type: {details['fuel_type']}\n")
            
            logging.info(f"✅ Saved metadata for {reg_no}")
            successful_scrapes += 1
            
            # Delay between vehicle requests
            time.sleep(2)
    
    logging.info("=" * 60)
    logging.info("🎯 VEHICLE SCRAPING SUMMARY")
    logging.info("=" * 60)
    logging.info(f"🚗 Processed {total_vehicles} vehicles")
    logging.info(f"✅ Successfully scraped {successful_scrapes} vehicles")
    logging.info(f"📁 Saved to: {base_dir}/")
    logging.info("=" * 60)
    
    return True



