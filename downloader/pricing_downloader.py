import os
import requests
import time
import hashlib
import json
import sys
import random
from tqdm import tqdm

# Configuration
BASE_URL = "https://pricing.us-east-1.amazonaws.com"
OFFERS_URL = f"{BASE_URL}/offers/v1.0/aws/{{}}/current/index.json"
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "raw")
INTEGRITY_FILE = os.path.join(DATA_DIR, "integrity.json")
MAX_RETRIES = 5

SERVICE_CODES = [
    "AmazonEC2",
    "AmazonEBS",
    "AmazonS3",
    "AmazonRDS",
    "AmazonLambda",
    "AmazonCloudFront",
    # Add others as needed
]

def calculate_sha256(filepath):
    """Calculate SHA256 checksum of a file efficiently."""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        # Read in 8k chunks
        for byte_block in iter(lambda: f.read(4096 * 1024), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def get_remote_file_info(url):
    """Get content length and other headers."""
    try:
        response = requests.head(url, timeout=10)
        response.raise_for_status()
        return {
            'size': int(response.headers.get('content-length', 0)),
            'etag': response.headers.get('etag', '').strip('"')
        }
    except Exception as e:
        print(f"  [Head Failed] {e}")
        return None

def download_with_resume(url, filepath, description):
    """
    Download file with resume capability and retries.
    Returns: (success: bool, sha256: str, error: str)
    """
    retries = 0
    while retries < MAX_RETRIES:
        try:
            # Check remote info
            remote_info = get_remote_file_info(url)
            if not remote_info:
                raise Exception("Could not fetch remote file info")
            
            total_size = remote_info['size']
            
            # Check local file
            existing_size = 0
            if os.path.exists(filepath):
                existing_size = os.path.getsize(filepath)
            
            if existing_size == total_size:
                print(f"  [Skipping] {description} already downloaded ({total_size} bytes)")
                return True, calculate_sha256(filepath), None
            
            if existing_size > total_size:
                print(f"  [Warning] Local file larger than remote. Restarting.")
                os.remove(filepath)
                existing_size = 0
            
            # Resume header
            headers = {}
            if existing_size > 0:
                headers['Range'] = f"bytes={existing_size}-"
                print(f"  [Resuming] {description} from {existing_size}/{total_size}")
            
            response = requests.get(url, headers=headers, stream=True, timeout=30)
            
            # 206 Partial Content (Resume) or 200 OK (Full)
            if response.status_code not in [200, 206]:
                # If range not satisfiable (416), maybe file changed?
                if response.status_code == 416:
                    print("  [416] Range not satisfiable, restarting download.")
                    os.remove(filepath)
                    existing_size = 0
                    continue # Retry loop
                raise Exception(f"HTTP {response.status_code}")

            mode = 'ab' if existing_size > 0 else 'wb'
            
            with open(filepath, mode) as f, tqdm(
                desc=description,
                initial=existing_size,
                total=total_size,
                unit='B',
                unit_scale=True,
                unit_divisor=1024,
                leave=False
            ) as bar:
                for chunk in response.iter_content(chunk_size=8192*4):
                    if chunk:
                        f.write(chunk)
                        bar.update(len(chunk))
            
            # Verify size at end
            final_size = os.path.getsize(filepath)
            if final_size != total_size:
                raise Exception(f"Size mismatch: Expected {total_size}, got {final_size}")
            
            # Success
            return True, calculate_sha256(filepath), None

        except Exception as e:
            retries += 1
            wait_time = (2 ** retries) + random.uniform(0, 1)
            print(f"  [Error] {e}. Retrying not taking in {wait_time:.1f}s...")
            time.sleep(wait_time)
    
    return False, None, "Max Retries Exceeded"

def main():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        
    print("Initializing Fault-Tolerant Downloader...")
    
    report = {
        "timestamp": time.time(),
        "files": {},
        "status": "pending"
    }

    # Load Previous Integrity Report to check if we can skip hashing (optional optimization)
    # For now, we will re-hash to be safe as per "Verify per file" requirement
    
    overall_success = True
    
    for code in SERVICE_CODES:
        filename = f"{code.lower()}_pricing.json"
        filepath = os.path.join(DATA_DIR, filename)
        url = OFFERS_URL.format(code)
        
        print(f"Processing {code}...")
        
        success, sha256, error = download_with_resume(url, filepath, code)
        
        file_entry = {
            "success": success,
            "path": filepath,
            "sha256": sha256
        }
        
        if not success:
            file_entry["error"] = error
            overall_success = False
            print(f"  [FAILED] {code}: {error}")
        else:
            print(f"  [OK] Hash: {sha256[:8]}...")
            
        report["files"][code] = file_entry

    report["status"] = "success" if overall_success else "failed"
    
    with open(INTEGRITY_FILE, "w") as f:
        json.dump(report, f, indent=2)
        
    print("\n------------------------------------------------")
    print(f"Download Pipeline Completed. Status: {report['status'].upper()}")
    print(f"Integrity Report saved to {INTEGRITY_FILE}")
    
    if not overall_success:
        print("CRITICAL: One or more files failed integrity check. Aborting.")
        sys.exit(1)

if __name__ == "__main__":
    main()
