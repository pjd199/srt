import os
import re
import json
import urllib.parse
from .cache import fetch_url

ESV_API_KEY = os.environ.get("ESV_API_KEY", "IP")
API_BIBLE_KEY = os.environ.get("API_BIBLE_KEY", "")

# API.Bible Translation ID Mapping
BIBLE_IDS = {
    "niv": "78a9f6124f344018-01",
    "nlt": "d6e14a625393b4da-01",
    "msg": "6f11a7de016f942e-01"
}

_BOOKS_CACHE = {}

def get_bible_text(reference: str, version: str = "esv", refresh: bool = False) -> str:
    """
    Fetches passage HTML for a given reference string and translation version.
    """
    if not reference or reference.strip() == "":
        return ""

    print(f"Reading {reference} from {version.upper()}")
        
    ver = version.lower().strip()
    
    if ver == "esv":
        return fetch_esv_passage(reference, refresh)
    else:
        return fetch_apibible_passage(reference, ver, refresh)

def fetch_esv_passage(reference: str, refresh: bool = False) -> str:
    """Fetches ESV text using the official ESV API."""
    encoded_ref = urllib.parse.quote(reference)
    url = f"https://api.esv.org/v3/passage/html/?q={encoded_ref}&include-passage-references=false&include-footnotes=false&include-headings=false&include-short-copyright=false&include-audio-link=false"
    headers = {"Authorization": f"Token {ESV_API_KEY}"}
    
    try:
        res_text = fetch_url(url, refresh, ext="json", headers=headers,)
        data = json.loads(res_text)
        passages = data.get("passages", [])
        content = ""
        for ref, passage in zip(reference.split(","), passages):
            content += f"<h3>{reference}</h3>{passage}"
        return content
    except Exception:
        return f"<p class='bible-error'>[ESV Passage Error: {reference}]</p>"

def get_bible_books_map(bible_id: str, refresh: bool = False) -> dict:
    """
    Downloads and caches the official list of books from API.Bible 
    (stored locally via fetch_url, and kept in memory for the session).
    """

    if bible_id in _BOOKS_CACHE:
        return _BOOKS_CACHE[bible_id]


    url = f"https://api.scripture.api.bible/v1/bibles/{bible_id}/books"
    headers = {"api-key": API_BIBLE_KEY}

    mapping = {}
    try:
        res_text = fetch_url(url, refresh, ext="json", headers=headers)
        data = json.loads(res_text)
        books = data.get("data", [])
        for b in books:
            b_id = b.get("id")         # e.g., "PHP"
            b_name = b.get("nameLong", "").lower().strip() # e.g., "philippians"

            if b_id and b_name:
                mapping[b_name] = b_id
    except Exception as e:
        print(e)
        
    # Store in memory for subsequent lookups during this run
    _BOOKS_CACHE[bible_id] = mapping
    return mapping

def parse_passage_id(reference: str, bible_id: str) -> str:
    """
    Translates 'Philippians 2:5-8' into API.Bible format 'PHP.2.5-PHP.2.8'
    using the downloaded book mapping dictionary.
    """
    ref = reference.strip()
    match = re.match(r'^([\d\s]*[A-Za-z]+)\s+(\d+):(\d+)(?:-(\d+))?$', ref)
    if not match:
        return ""
        
    book_raw = match.group(1).lower().strip()
    chapter = match.group(2)
    start_verse = match.group(3)
    end_verse = match.group(4)

    books_map = get_bible_books_map(bible_id)
    usfm_code = books_map.get(book_raw)

    if not usfm_code:
        # Fallback heuristic if not found in map
        usfm_code = book_raw[:3].upper()

    if end_verse:
        return f"{usfm_code}.{chapter}.{start_verse}-{usfm_code}.{chapter}.{end_verse}"
    return f"{usfm_code}.{chapter}.{start_verse}"

def fetch_apibible_passage(reference: str, version: str, refresh: bool = False) -> str:
    """Fetches passage content directly using API.Bible passage endpoint."""
    bible_id = BIBLE_IDS.get(version)
    passage_id = parse_passage_id(reference, bible_id)
    if not passage_id:
        return f"<p class='bible-error'>[Invalid Reference Format: {reference}]</p>"
        
    url = f"https://api.scripture.api.bible/v1/bibles/{bible_id}/passages/{passage_id}?content-type=html&include-notes=false&include-titles=false"
    headers = {"api-key": API_BIBLE_KEY}
    
    try:
        res_text = fetch_url(url, refresh, ext="json", headers=headers)
        data = json.loads(res_text)
        content = data.get("data", {}).get("content", "")
        return f"<h3>{reference}</h3><div class='scripture-passage {version}'>{content}</div>"
    except Exception as e:
        print(e)
        return "ERROR {reference}, {version})"