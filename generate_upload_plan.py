import os
import hashlib

# --- CONFIGURATION ---
BUCKET = "BUCKET NAME"      
PREFIX = "videos"
SOURCE = "SOURCE DIRECTORY"
OUTPUT = "s3_upload_plan.txt"
# ---------------------

def main():
    if not os.path.exists(SOURCE):
        print(f"Error: Source not found: {SOURCE}")
        return

    print(f"Scanning {SOURCE}...")
    count = 0

    with open(OUTPUT, "w") as f:
        with os.scandir(SOURCE) as scanner:
            for entry in scanner:
                if entry.is_file() and entry.name.endswith(".mp4"):
                    fname = entry.name

                    # Hash Sharding
                    hash_obj = hashlib.md5(fname.encode('utf-8'))
                    shard = hash_obj.hexdigest()[:2]

                    cmd = f"cp {entry.path} s3://{BUCKET}/{PREFIX}/{shard}/{fname}\n"

                    f.write(cmd)
                    count += 1

                    if count % 50000 == 0:
                        print(f"Found {count} videos...")

    print(f"DONE: Generated plan for {count} videos in '{OUTPUT}'")

if __name__ == "__main__":
    main()