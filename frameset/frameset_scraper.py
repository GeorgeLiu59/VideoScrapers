import requests
import json
import logging
import time
import os
import base64
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)

COOKIE_STRING = os.getenv("FRAMESET_COOKIE_STRING", '')

TARGET_COUNT = 2000
OUTPUT_FOLDER = Path("frameset_downloads")
MAX_WORKERS = 8
PAGE_SIZE = 400

headers = {
    "authority": "frameset.app",
    "accept": "*/*",
    "accept-encoding": "gzip, deflate, br, zstd",
    "accept-language": "en-US,en;q=0.9",
    "referer": "https://frameset.app/search",
    "sec-ch-ua": '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"
}

def parse_cookies(cookie_string):
    cookies = {}
    if not cookie_string:
        return cookies
    for cookie in cookie_string.split(';'):
        cookie = cookie.strip()
        if '=' in cookie:
            key, value = cookie.split('=', 1)
            cookies[key.strip()] = value.strip()
    return cookies

def check_token_expiry(cookies):
    try:
        auth_token = cookies.get("sb-rxmhjspmurpimzyrvtzs-auth-token", "")
        if not auth_token:
            return None
        
        if auth_token.startswith("base64-"):
            token_part = auth_token.replace("base64-", "").strip()
        else:
            token_part = auth_token
        
        decoded_cookie = base64.b64decode(token_part)
        cookie_data = json.loads(decoded_cookie)
        access_token = cookie_data.get("access_token", "")
        if not access_token:
            return None
        
        parts = access_token.split(".")
        if len(parts) != 3:
            return None
        
        payload = parts[1]
        padding = 4 - len(payload) % 4
        if padding != 4:
            payload += "=" * padding
        
        decoded = base64.urlsafe_b64decode(payload)
        data = json.loads(decoded)
        exp = data.get("exp")
        
        if exp:
            exp_time = datetime.fromtimestamp(exp)
            hours_left = (exp_time - datetime.now()).total_seconds() / 3600
            return hours_left
    except Exception:
        pass
    return None

def fetch_page(page, cookies):
    url = f"https://frameset.app/api/search?page={page}&size={PAGE_SIZE}"
    try:
        response = requests.get(url, headers=headers, cookies=cookies, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict) and data.get("success"):
                data_obj = data.get("data", {})
                if isinstance(data_obj, dict):
                    items = data_obj.get("results", [])
                    if isinstance(items, list):
                        return items
            return []
        else:
            logger.error(f"Page {page}: Error {response.status_code}")
            return []
    except Exception as e:
        logger.error(f"Page {page}: {e}")
        return []

def fetch_metadata(cookies):
    logger.info(f"Fetching metadata for {TARGET_COUNT} items...")
    all_items = []
    page = 1
    
    while len(all_items) < TARGET_COUNT:
        items = fetch_page(page, cookies)
        if not items:
            logger.info("No more results.")
            break
        all_items.extend(items)
        logger.info(f"Collected {len(all_items)} items...")
        page += 1
        time.sleep(0.5)
    
    return all_items[:TARGET_COUNT]

def save_metadata(items):
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    filepath = OUTPUT_FOLDER / "_metadata.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved {len(items)} items to {filepath}")

def download_media(item, index, total, cookies):
    item_id = item.get("id") or item.get("_id") or f"unknown_{index}"
    item_type = item.get("type", "motion")
    
    cdn_base = "https://d13mryl9xv19vu.cloudfront.net"
    if item_type == "motion":
        suffix = "_fs"
        extensions = ["gif", "mp4"]
    elif item_type == "still":
        suffix = "_xl"
        extensions = ["jpg", "jpeg", "png"]
    else:
        suffix = "_fs"
        extensions = ["gif", "mp4"]
    
    filename = f"{item_id}.{extensions[0]}"
    filepath = OUTPUT_FOLDER / filename
    
    if filepath.exists():
        logger.info(f"[{index}/{total}] Skipping (exists): {filename}")
        return
    
    cdn_headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Referer": "https://frameset.app/",
        "Origin": "https://frameset.app",
        "Sec-Fetch-Dest": "image",
        "Sec-Fetch-Mode": "no-cors",
        "Sec-Fetch-Site": "cross-site",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "DNT": "1"
    }
    
    for attempt_ext in extensions:
        try_url = f"{cdn_base}/{item_id}{suffix}.{attempt_ext}"
        try:
            response = requests.get(try_url, headers=cdn_headers, cookies=cookies, timeout=30, stream=True)
            if response.status_code == 200:
                content_length = response.headers.get("content-length")
                if content_length and int(content_length) < 100:
                    continue
                
                content_type = response.headers.get("content-type", "").lower()
                if not content_type or any(ct in content_type for ct in ["video", "image", "gif", "octet-stream", "binary"]):
                    final_filename = f"{item_id}.{attempt_ext}"
                    final_filepath = OUTPUT_FOLDER / final_filename
                    
                    if final_filepath.exists():
                        continue
                    
                    with open(final_filepath, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    
                    if final_filepath.exists() and final_filepath.stat().st_size > 0:
                        logger.info(f"[{index}/{total}] Downloaded: {final_filename}")
                        return
        except Exception:
            continue
    
    logger.error(f"[{index}/{total}] Failed to download media for {item_id}")

def main():
    start_time = time.time()
    
    if not COOKIE_STRING:
        logger.error("FRAMESET_COOKIE_STRING is not set!")
        logger.error("Get cookies from https://frameset.app (DevTools -> Network -> Copy all cookies)")
        logger.error("Set: export FRAMESET_COOKIE_STRING='cookie1=value1; cookie2=value2; ...'")
        return
    
    cookies = parse_cookies(COOKIE_STRING)
    if not cookies:
        logger.error("Failed to parse cookies. Check your cookie string format.")
        return
    
    hours_left = check_token_expiry(cookies)
    if hours_left is not None:
        if hours_left <= 0:
            logger.error("Token expired. Get a new cookie from https://frameset.app")
            return
        logger.info(f"Token expires in {hours_left:.1f} hours")
    
    items = fetch_metadata(cookies)
    if not items:
        logger.warning("No items found. Check if your cookie is valid.")
        return
    
    save_metadata(items)
    
    motion_items = [item for item in items if item.get("type") == "motion"]
    still_items = [item for item in items if item.get("type") == "still"]
    
    logger.info(f"Found {len(motion_items)} motion items and {len(still_items)} still items out of {len(items)} total")
    
    all_media = motion_items + still_items
    if all_media:
        logger.info(f"Downloading {len(all_media)} media files with {MAX_WORKERS} workers...")
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [executor.submit(download_media, item, i+1, len(all_media), cookies) for i, item in enumerate(all_media)]
            for future in as_completed(futures):
                pass
        logger.info("Downloads complete!")
    else:
        logger.info("No media to download.")
    
    elapsed_time = time.time() - start_time
    minutes = int(elapsed_time // 60)
    seconds = int(elapsed_time % 60)
    if minutes > 0:
        logger.info(f"Total scraping time: {minutes}m {seconds}s")
    else:
        logger.info(f"Total scraping time: {seconds}s")

if __name__ == "__main__":
    main()
