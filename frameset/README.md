# Frameset Scraper

Python script to scrape and download videos and images from Frameset.

## Setup

1. **Install Python dependencies:**
   ```bash
   pip install requests
   ```

2. **Get your authentication cookies:**
   - Go to https://frameset.app and log in
   - Open browser DevTools (F12)
   - Go to Network tab
   - Make any API request (search)
   - Copy all cookies from the request headers

3. **Set your cookies as environment variable:**
   ```bash
   export FRAMESET_COOKIE_STRING='cookie1=value1; cookie2=value2; ...'
   ```
   
   Or on Windows:
   ```cmd
   set FRAMESET_COOKIE_STRING=cookie1=value1; cookie2=value2; ...
   ```

## Usage

```bash
python frameset_scraper.py
```

## Configuration

Edit these variables in `frameset_scraper.py`:

- `TARGET_COUNT`: Number of items to fetch (default: 2000)
- `OUTPUT_FOLDER`: Where to save files (default: "frameset_downloads")
- `MAX_WORKERS`: Number of parallel downloads (default: 8)
- `PAGE_SIZE`: Items per page (default: 400)
- `DOWNLOAD_DELAY`: Delay between downloads in seconds (default: 0)

## Output

- Motion items (videos) are saved as `{id}.gif` or `{id}.mp4` using `_fs` suffix
- Still items (images) are saved as `{id}.jpg`, `{id}.jpeg`, or `{id}.png` using `_xl` suffix
- Metadata is saved to `_metadata.json`
- Look up item info by searching for the ID in the metadata file
- Downloads all items found (uses `type` field: "motion" for gifs/videos, "still" for images)

## Notes

- Cookies expire periodically - update them when the script warns you
- The script checks token expiry before running
- Existing downloads are skipped automatically
