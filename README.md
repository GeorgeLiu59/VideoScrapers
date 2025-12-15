# Video Scrapers

Python scripts to scrape and download videos/images from Flim.ai and Frameset.

## Demo

(Flim) Setting up Auth and Scraping 100 Videos: ~11 Videos/Second [Watch on Vimeo](https://vimeo.com/1142171332)

(Frameset) Setting up Auth and Scraping Videos: ~4.5 Shots/Second [Watch on Vimeo](https://vimeo.com/1142266850)

## Overview

This repository contains two separate scrapers:

- **Flim Scraper** (`flim/`) - Downloads videos from Flim.ai
- **Frameset Scraper** (`frameset/`) - Downloads videos and images from Frameset

Each scraper has its own directory with setup instructions, configuration options, and usage details. See the README in each directory for specific information.

## Quick Start

1. Navigate to the scraper directory you want to use (`flim/` or `frameset/`)
2. Follow the setup instructions in that directory's README
3. Configure the scraper settings as needed
4. Run the scraper script

## S3 Upload with s5cmd

This repository includes `generate_upload_plan.py` for generating s5cmd upload commands to S3. The script:

- Scans a source directory for `.mp4` files
- Uses MD5 hash-based sharding (first 2 characters) to organize files into subdirectories
- Generates s5cmd `cp` commands in the format: `s3://BUCKET/PREFIX/shard/filename.mp4`

**Usage:**

1. Edit `generate_upload_plan.py` and configure:
   - `BUCKET`: Your S3 bucket name
   - `PREFIX`: S3 prefix/folder (default: "videos")
   - `SOURCE`: Local directory containing video files
   - `OUTPUT`: Output file for upload commands (default: "s3_upload_plan.txt")

2. Run the script:
   ```bash
   python generate_upload_plan.py
   ```

3. Execute the generated upload plan with s5cmd:
   ```bash
   s5cmd run s3_upload_plan.txt
   ```

The sharding strategy distributes files across subdirectories based on filename hash, helping to avoid S3 prefix hotspots.
