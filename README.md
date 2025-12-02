# Video Scrapers

Python scripts to scrape and download videos/images from Flim.ai and Frameset.

## Demo

(Flim) Setting up Auth and Scraping 100 Videos: ~11 Videos/Second [Watch on Vimeo](https://vimeo.com/1142171332)

(Frameset) Setting up Auth and Scraping Videos: ~4.5 Shots/Second [Watch on Vimeo](https://vimeo.com/1142266850)

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

7. **Set your token as environment variable:**
   ```bash
   export FLIM_AUTH_TOKEN="Bearer your_token_here"
   ```
   
   Or on Windows:
   ```cmd
   set FLIM_AUTH_TOKEN=Bearer your_token_here
   ```

### Usage

```bash
python flim_scraper.py
```

### Configuration

Edit these variables in `flim_scraper.py`:

- `TARGET_COUNT`: Number of items to fetch (default: 2000)
- `OUTPUT_FOLDER`: Where to save files (default: "flim_downloads")
- `MAX_WORKERS`: Number of parallel downloads (default: 8)

### Output

- Videos are saved as `{id}.mp4` in the output folder
- Metadata is saved to `_metadata.json`
- Look up video info by searching for the ID in the metadata file

## Frameset Scraper

### Authentication

1. Go to https://frameset.app and log in
2. Open browser DevTools (F12)
3. Go to Network tab
4. Make any API request (search)
5. Copy all cookies from the request headers

6. **Set your cookies as environment variable:**
   ```bash
   export FRAMESET_COOKIE_STRING='cookie1=value1; cookie2=value2; ...'
   ```
   
   Or on Windows:
   ```cmd
   set FRAMESET_COOKIE_STRING=cookie1=value1; cookie2=value2; ...
   ```

### Usage

```bash
python frameset_scraper.py
```

### Configuration

Edit these variables in `frameset_scraper.py`:

- `TARGET_COUNT`: Number of items to fetch (default: 2000)
- `OUTPUT_FOLDER`: Where to save files (default: "frameset_downloads")
- `MAX_WORKERS`: Number of parallel downloads (default: 8)
- `PAGE_SIZE`: Items per page (default: 400)
- `DOWNLOAD_DELAY`: Delay between downloads in seconds (default: 0)

### Output

- Motion items (videos) are saved as `{id}.gif` or `{id}.mp4` using `_fs` suffix
- Still items (images) are saved as `{id}.jpg`, `{id}.jpeg`, or `{id}.png` using `_xl` suffix
- Metadata is saved to `_metadata.json`
- Look up item info by searching for the ID in the metadata file

## Notes

- Tokens/cookies expire periodically - update them when the script warns you
- Flim: Only videos with `has_video_urls: true` are downloaded
- Frameset: Downloads all items found (uses `type` field: "motion" for gifs, "still" for images)

