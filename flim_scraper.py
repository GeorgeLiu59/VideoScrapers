import requests
import json
import logging
import time
import os
import base64
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)

AUTH_TOKEN = os.getenv("FLIM_AUTH_TOKEN")

TARGET_COUNT = 10000
OUTPUT_FOLDER = Path("flim_downloads")
MAX_DOWNLOAD_WORKERS = 48  

session = requests.Session()

headers = {
    "authority": "api.flim.ai",
    "accept": "*/*",
    "accept-encoding": "gzip, deflate, br, zstd",
    "accept-language": "en-US,en;q=0.9",
    "authorization": AUTH_TOKEN,
    "content-type": "application/json",
    "feature-flag": "blockVisitors",
    "origin": "https://app.flim.ai",
    "priority": "u=1, i",
    "referer": "https://app.flim.ai/",
    "sec-ch-ua": '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"
}
session.headers.update(headers)

retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["HEAD", "GET", "POST", "OPTIONS"]
)
adapter = HTTPAdapter(pool_connections=MAX_DOWNLOAD_WORKERS, pool_maxsize=MAX_DOWNLOAD_WORKERS, max_retries=retry_strategy)
session.mount("https://", adapter)
session.mount("http://", adapter)


def get_payload(page):
    return {
        "search": {
            "saved_images": False,
            "full_text": "",
            "similar_picture_id": "",
            "movie_id": "",
            "dop": "",
            "director": "",
            "brand": "",
            "agency": "",
            "production_company": "",
            "actor": "",
            "creator": "",
            "artist": "",
            "collection_id": "",
            "board_id": "",
            "filters": {
                "genres": [],
                "colors": [],
                "number_of_persons": [],
                "years": [],
                "shot_types": [],
                "movie_types": [],
                "aspect_ratio": [],
                "safety_content": [],
                "has_video_cuts": True,
                "camera_motions": []
            },
            "negative_filters": {
                "aspect_ratio": [],
                "genres": ["ANIMATION"],
                "movie_types": [],
                "colors": [],
                "shot_types": [],
                "number_of_persons": [],
                "years": [],
                "safety_content": ["nudity", "violence"]
            }
        },
        "page": page,
        "sort_by": "",
        "order_by": "",
        "number_per_pages": 200
    }

def check_token_expiry(token):
    try:
        if not token: return None
        token_part = token.replace("Bearer ", "").strip()
        parts = token_part.split(".")
        if len(parts) != 3: return None
        
        payload = parts[1]
        padding = 4 - len(payload) % 4
        if padding != 4: payload += "=" * padding
        
        decoded = base64.urlsafe_b64decode(payload)
        data = json.loads(decoded)
        if "exp" in data:
            exp_time = datetime.fromtimestamp(data["exp"])
            return (exp_time - datetime.now()).total_seconds() / 3600
    except Exception:
        pass
    return None

def fetch_page(page):
    url = "https://api.flim.ai/2.0.0/search"
    try:
        # Using 'session.post' is faster than 'requests.post' due to connection reuse
        response = session.post(url, json=get_payload(page), timeout=30)
        if response.status_code == 200:
            data = response.json()
            return data.get("query_response", {}).get("images", [])
        else:
            logger.error(f"Page {page}: Error {response.status_code}")
            return []
    except Exception as e:
        logger.error(f"Page {page}: {e}")
        return []

def load_existing_metadata():
    filepath = OUTPUT_FOLDER / "_metadata.json"
    if filepath.exists():
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.info(f"Loaded {len(data)} existing items from metadata")
            return data
        except Exception as e:
            logger.warning(f"Could not load existing metadata: {e}")
    return []

def save_metadata(new_items, existing_items):
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    filepath = OUTPUT_FOLDER / "_metadata.json"
    
    # Merge existing and new
    existing_ids = {item.get("id") for item in existing_items if item.get("id")}
    final_list = existing_items.copy()
    
    added_count = 0
    for item in new_items:
        if item.get("id") not in existing_ids:
            final_list.append(item)
            existing_ids.add(item.get("id"))
            added_count += 1
            
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(final_list, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Saved metadata. Total: {len(final_list)} (Added {added_count} new this run).")
    return final_list

def download_video(item, index, total):
    if not item.get("has_video_urls"): return
    
    item_id = item.get("id", f"unknown_{index}")
    url = item.get("video_urls", {}).get("url_full")
    if not url: return
    
    filename = f"{item_id}.mp4"
    filepath = OUTPUT_FOLDER / filename
    
    if filepath.exists():
        return
    
    try:
        response = session.get(url, timeout=30, stream=True)
        if response.status_code == 200:
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=32*1024):
                    f.write(chunk)
            logger.info(f"[{index}/{total}] Downloaded: {filename}")
        else:
            logger.error(f"[{index}/{total}] Failed {response.status_code}: {filename}")
    except Exception as e:
        logger.error(f"[{index}/{total}] Error: {filename} - {e}")


def main():
    start_time = time.time()
    
    if not AUTH_TOKEN:
        logger.error("AUTH_TOKEN is not set!")
        return
    
    hours = check_token_expiry(AUTH_TOKEN)
    if hours is not None:
        logger.info(f"Token is valid. Expires in ~{hours:.1f} hours.")
        if hours <= 0:
            logger.error("Token has expired.")
            return

    # 1. Load Existing Data
    existing_items = load_existing_metadata()
    existing_ids = {item.get("id") for item in existing_items if item.get("id")}
    
    # 2. Fetch New Metadata (Original Logic: loop until we get TARGET_COUNT new items)
    logger.info(f"Fetching metadata for {TARGET_COUNT} NEW items...")
    
    new_collected_items = []
    page = 0
    skipped_count = 0
    
    # Loop continues until we have enough NEW items
    while len(new_collected_items) < TARGET_COUNT:
        images = fetch_page(page)
        if not images:
            logger.info("No more results from API.")
            break
        
        # Filter duplicates against what we ALREADY had on disk
        batch_new_items = [img for img in images if img.get("id") not in existing_ids]
        
        # Also filter against what we just collected in this run (in case of API duplicates)
        batch_new_items = [img for img in batch_new_items if img.get("id") not in {x['id'] for x in new_collected_items}]
        
        skipped_in_this_batch = len(images) - len(batch_new_items)
        skipped_count += skipped_in_this_batch
        
        new_collected_items.extend(batch_new_items)
        logger.info(f"Page {page}: Found {len(batch_new_items)} new items (Total new: {len(new_collected_items)}/{TARGET_COUNT})")
        
        # Stop condition: If we found duplicates previously, and this page is purely duplicates, we assume we hit the 'old' data.
        if not batch_new_items and skipped_count > 0:
            logger.info("Hit a page of purely duplicate items. Stopping fetch.")
            break
            
        page += 1
    
    # 3. Save Metadata
    if new_collected_items:
        all_items = save_metadata(new_collected_items, existing_items)
    else:
        logger.info("No new items found.")
        all_items = existing_items

    # 4. Download Videos (Optimized: Parallel)
    # We attempt to download videos for ALL items (just in case previous runs failed downloads)
    # But the 'download_video' function has a check: 'if filepath.exists(): return'
    videos = [item for item in all_items if item.get("has_video_urls")]
    
    logger.info(f"Verifying/Downloading {len(videos)} videos with {MAX_DOWNLOAD_WORKERS} threads...")
    
    if videos:
        with ThreadPoolExecutor(max_workers=MAX_DOWNLOAD_WORKERS) as executor:
            futures = [
                executor.submit(download_video, item, i+1, len(videos)) 
                for i, item in enumerate(videos)
            ]
            # Wait for all downloads to finish
            for future in as_completed(futures):
                pass
    
    elapsed = time.time() - start_time
    logger.info(f"Job Complete. Total time: {int(elapsed // 60)}m {int(elapsed % 60)}s")

if __name__ == "__main__":
    main()