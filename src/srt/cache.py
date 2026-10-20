import hashlib
import json
import os
import time
import requests

CACHE_DIR = "./cache"
LAST_REQUEST_TIME = 0

def get_cache_path(url: str, ext: str = "html", headers: dict = None) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)
    # Include headers in the hash calculation so authenticated and unauthenticated requests cache separately
    key_string = url
    if headers:
        key_string += json.dumps(headers, sort_keys=True)
    url_hash = hashlib.md5(key_string.encode("utf-8")).hexdigest()
    return os.path.join(CACHE_DIR, f"{url_hash}.{ext}")

def rate_limit():
    global LAST_REQUEST_TIME
    elapsed = time.time() - LAST_REQUEST_TIME
    if elapsed < 1.0:
        time.sleep(1.0 - elapsed)
    LAST_REQUEST_TIME = time.time()

def fetch_url(url: str, refresh: bool = False, ext: str = "html", binary: bool = False, headers: dict = None):
    cache_path = get_cache_path(url, ext, headers)
    
    if not refresh and os.path.exists(cache_path):
        #print(f"GET {url} HIT")
        mode = "rb" if binary else "r"
        encoding = None if binary else "utf-8"
        try:
            with open(cache_path, mode, encoding=encoding) as f:
                return f.read()
        except Exception as e:
            # If cached file is corrupt or encoding mismatch, log and re-fetch from network
            print(f"Cache read error for {url}: {e}. Re-fetching...")
            
    #print(f"GET {url} MISS")
    rate_limit()
    
    req_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) srt-cli/1.0"}
    if headers:
        req_headers.update(headers)
        
    response = requests.get(url, headers=req_headers)
    response.raise_for_status()
    
    content = response.content if binary else response.text
    write_mode = "wb" if binary else "w"
    write_encoding = None if binary else "utf-8"
    
    with open(cache_path, write_mode, encoding=write_encoding) as f:
        f.write(content)
        
    return content