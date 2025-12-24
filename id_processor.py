import uuid
import os

# -----------------------------------------------------------------------------
# MOODIO GLOBAL ID PROCESSOR
# -----------------------------------------------------------------------------
# This utility ensures that EVERY asset in our system gets a deterministic,
# globally unique UUID v5 regardless of its source ID length (20 vs 36 chars).
# -----------------------------------------------------------------------------

# We derive a unique, stable Namespace UUID from "moodio"
MOODIO_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, 'moodio')

def get_global_uuid(original_id: str) -> str:
    """
    Generates a deterministic UUID v5 for any given input ID.
    Works for 20-char flim IDs, 36-char UUIDs, or any other string.
    """
    if not original_id:
        raise ValueError("Original ID cannot be empty")
    
    # Ensure it's a string for hashing
    return str(uuid.uuid5(MOODIO_NAMESPACE, str(original_id)))

def get_s3_path(original_id: str, asset_type: str = "images", ext: str = "jpg") -> str:
    """
    Generates the sharded S3 path for an asset.
    Format: {asset_type}/{shard}/{uuid}.{ext}
    """
    guid = get_global_uuid(original_id)
    shard = guid[:2]  # First two characters for sharding (00-ff)
    
    # Clean extension (remove leading dot if provided)
    ext = ext.lstrip('.')
    
    return f"{asset_type}/{shard}/{guid}.{ext}"

if __name__ == "__main__":
    # Quick test/validation
    test_id = "TSdwYwc6MkoRxpwhHRvY"
    print(f"Original ID: {test_id}")
    print(f"Global UUID: {get_global_uuid(test_id)}")
    print(f"S3 Path:    {get_s3_path(test_id, 'videos', 'mp4')}")
