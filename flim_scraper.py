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

AUTH_TOKEN = os.getenv("FLIM_AUTH_TOKEN")

TARGET_COUNT = 2000
OUTPUT_FOLDER = Path("flim_downloads")
MAX_WORKERS = 8

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
        token_part = token.replace("Bearer ", "").strip()
        parts = token_part.split(".")
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
    except:
        pass
    return None

def fetch_page(page):
    url = "https://api.flim.ai/2.0.0/search"
    try:
        response = requests.post(url, json=get_payload(page), headers=headers, timeout=30)
        if response.status_code == 200:
            data = response.json()
            images = data.get("query_response", {}).get("images", [])
            return images
        else:
            logger.error(f"Page {page}: Error {response.status_code}")
            return []
    except Exception as e:
        logger.error(f"Page {page}: {e}")
        return []

def fetch_metadata():
    logger.info(f"Fetching metadata for {TARGET_COUNT} items...")
    all_items = []
    page = 0
    
    while len(all_items) < TARGET_COUNT:
        images = fetch_page(page)
        if not images:
            logger.info("No more results.")
            break
        
        all_items.extend(images)
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

def download_video(item, index, total):
    if not item.get("has_video_urls"):
        return
    
    video_urls = item.get("video_urls", {})
    url = video_urls.get("url_thumbnail")
    if not url:
        return
    
    item_id = item.get("id", f"unknown_{index}")
    filename = f"{item_id}.mp4"
    filepath = OUTPUT_FOLDER / filename
    
    if filepath.exists():
        logger.info(f"[{index}/{total}] Skipping (exists): {filename}")
        return
    
    try:
        response = requests.get(url, timeout=30, stream=True)
        if response.status_code == 200:
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
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
        logger.error("Get token from https://app.flim.ai (DevTools -> Network -> Copy Authorization header)")
        logger.error("Set: export FLIM_AUTH_TOKEN='Bearer ...' or update AUTH_TOKEN in script")
        return
    
    hours_left = check_token_expiry(AUTH_TOKEN)
    if hours_left is not None:
        if hours_left <= 0:
            logger.error("Token expired. Get a new token from https://app.flim.ai")
            return
        logger.info(f"Token expires in {hours_left:.1f} hours")
    
    items = fetch_metadata()
    if not items:
        logger.warning("No items found. Check if your token is valid.")
        return
    
    save_metadata(items)
    
    videos = [item for item in items if item.get("has_video_urls")]
    logger.info(f"Found {len(videos)} items with videos out of {len(items)} total")
    
    if videos:
        logger.info(f"Downloading {len(videos)} videos with {MAX_WORKERS} workers...")
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [executor.submit(download_video, item, i+1, len(videos)) for i, item in enumerate(videos)]
            for future in as_completed(futures):
                pass
        logger.info("Downloads complete!")
    else:
        logger.info("No videos to download.")
    
    elapsed_time = time.time() - start_time
    minutes = int(elapsed_time // 60)
    seconds = int(elapsed_time % 60)
    if minutes > 0:
        logger.info(f"Total scraping time: {minutes}m {seconds}s")
    else:
        logger.info(f"Total scraping time: {seconds}s")

if __name__ == "__main__":
    main()
