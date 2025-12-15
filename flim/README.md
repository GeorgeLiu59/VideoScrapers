# Flim Scraper

Python script to scrape and download videos from Flim.ai.

## Setup

1. **Install Python dependencies:**
   ```bash
   pip install requests
   ```

2. **Get your authentication token:**
   - Go to https://app.flim.ai and log in
   - Open browser DevTools (F12)
   - Go to Network tab
   - Make any API request (search)
   - Find a request to `api.flim.ai`
   - Copy the `Authorization` header value (starts with "Bearer ...")

3. **Set your token as environment variable:**
   ```bash
   export FLIM_AUTH_TOKEN="Bearer your_token_here"
   ```
   
   Or on Windows:
   ```cmd
   set FLIM_AUTH_TOKEN=Bearer your_token_here
   ```

## Usage

```bash
python flim_scraper.py
```

## Configuration

Edit these variables in `flim_scraper.py`:

- `TARGET_COUNT`: Number of items to fetch (default: 10000)
- `OUTPUT_FOLDER`: Where to save files (default: "flim_downloads")
- `MAX_DOWNLOAD_WORKERS`: Number of parallel downloads (default: 48)
- `METADATA_WORKERS`: Number of parallel metadata fetchers (default: 8)

## Output

- Videos are saved as `{id}.mp4` in the output folder
- Metadata is saved to `_metadata.json`
- Look up video info by searching for the ID in the metadata file
- Only videos with `has_video_urls: true` are downloaded

## Notes

- Tokens expire periodically - update them when the script warns you
- The script checks token expiry before running
- Existing downloads are skipped automatically
- Metadata is preserved across runs
