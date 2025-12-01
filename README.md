# Flim Video Scraper

A Python script to scrape and download videos from Flim.ai.

## Demo

Setting up Auth and Scraping 100 Videos: [Watch on Vimeo](https://vimeo.com/1142171332)

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
python film_scraper.py
```

## Configuration

Edit these variables in `film_scraper.py`:

- `TARGET_COUNT`: Number of items to fetch (default: 2000)
- `OUTPUT_FOLDER`: Where to save files (default: "flim_downloads")
- `MAX_WORKERS`: Number of parallel downloads (default: 4)

## Output

- Videos are saved as `{id}.mp4` in the output folder
- Metadata is saved to `_metadata.json`
- Look up video info by searching for the ID in the metadata file

## Notes

- Token expires periodically - update it when the script warns you
- Only videos with `has_video_urls: true` are downloaded

