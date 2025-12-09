import os
import requests
import hashlib
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

def get_session():
    """Created a requests session with retry logic."""
    session = requests.Session()
    retry = Retry(
        total=3,
        read=3,
        connect=3,
        backoff_factor=1, # 1s, 2s, 4s
        status_forcelist=[500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def calculate_sha256(file_path, chunk_size=65536):
    """Calculates SHA256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(chunk_size), b''):
            sha256.update(chunk)
    return sha256.hexdigest()

def download_file(url: str, target_path: Path, expected_hash: str = None) -> bool:
    """
    Downloads a file with resume, retry, and validation capabilities.
    
    Args:
        url: The URL to download.
        target_path: pathlib.Path object for the destination.
        expected_hash: Optional SHA256 hash to verify against.
        
    Returns:
        True if successful, False otherwise.
    """
    target_path = Path(target_path)
    if not target_path.parent.exists():
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
    part_file = target_path.with_suffix(target_path.suffix + '.part')
    meta_file = target_path.with_suffix(target_path.suffix + '.meta')
    
    session = get_session()
    headers = {}
    
    mode = 'wb'
    downloaded_bytes = 0
    
    # Check for existing partial file to resume
    if part_file.exists():
        downloaded_bytes = part_file.stat().st_size
        headers['Range'] = f'bytes={downloaded_bytes}-'
        mode = 'ab'
        logger.info(f"Resuming download for {target_path.name} from byte {downloaded_bytes}")
    else:
        logger.info(f"Starting download for {target_path.name}")
        
    try:
        with session.get(url, headers=headers, stream=True, timeout=30) as response:
            # specialized handling for 416 Range Not Satisfiable (file might be done or changed)
            if response.status_code == 416: 
                logger.warning("Range not satisfiable. Restarting download.")
                part_file.unlink(missing_ok=True)
                downloaded_bytes = 0
                headers.pop('Range', None)
                return download_file(url, target_path, expected_hash)
            
            response.raise_for_status()
            
            # Check if server accepted range
            if 'Range' in headers and response.status_code != 206:
                logger.warning("Server did not accept resume. Restarting.")
                part_file.unlink(missing_ok=True)
                mode = 'wb'
                downloaded_bytes = 0
            
            total_size = int(response.headers.get('content-length', 0)) + downloaded_bytes
            
            with open(part_file, mode) as f:
                for chunk in response.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)
                        
    except Exception as e:
        logger.error(f"Download failed for {url}: {e}")
        return False
        
    # Verify Hash if provided
    if expected_hash:
        logger.info(f"Verifying hash for {target_path.name}")
        file_hash = calculate_sha256(part_file)
        if file_hash != expected_hash:
            logger.error(f"Hash mismatch! Expected {expected_hash}, got {file_hash}")
            part_file.unlink() # Delete bad file
            return False
            
    # Atomic Move
    # replace is atomic on POSIX, usually atomic on Windows (Python 3.3+)
    part_file.replace(target_path)
    
    # Write Metadata
    file_stat = target_path.stat()
    file_sha256 = calculate_sha256(target_path)
    
    metadata = {
        "downloaded_at": datetime.utcnow().isoformat(),
        "sha256": file_sha256,
        "size": file_stat.st_size,
        "source": url
    }
    
    with open(meta_file, 'w') as f:
        json.dump(metadata, f, indent=2)
        
    logger.info(f"Successfully downloaded {target_path.name} ({file_stat.st_size} bytes)")
    return True
