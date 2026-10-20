import json
import os
from bs4 import BeautifulSoup
from .cache import fetch_url

PLANS_SOURCE_PATH = "./plans/source.json"

def scrape_plans_index(refresh: bool = False):
    plans = []
    page = 1
    base_url = "https://shereadstruth.com/plans/"
    
    os.makedirs("./plans", exist_ok=True)
    
    while True:
        url = base_url if page == 1 else f"{base_url}page/{page}/"
        try:
            html = fetch_url(url, refresh=refresh, ext="html")
        except Exception:
            # Reaches 404 or end of pages
            break
            
        soup = BeautifulSoup(html, "html.parser")
        
        # Target the verified card structure (.block-product)
        plan_items = soup.select(".block-product")
        
        if not plan_items and page > 1:
            break
            
        found_any = False
        for item in plan_items:
            found_any = True
            
            # Extract link and slug
            link_elem = item.find("a")
            if not link_elem:
                continue
                
            href = link_elem.get("href", "")
            slug = href.strip("/").split("/")[-1]
            
            # Extract title from block body header
            title_elem = item.select_one(".block__body h6") or item.find("h6")
            title = title_elem.get_text(strip=True) if title_elem else link_elem.get_text(strip=True)
            
            # Extract image source
            img_elem = item.find("img")
            image = img_elem.get("src", "") if img_elem else ""
            
            # Extract actual plan length (e.g., "35 days")
            length_elem = item.select_one(".block__body p") or item.find("p")
            length = length_elem.get_text(strip=True) if length_elem else "Unknown"
            
            plans.append({
                "title": title,
                "slug": slug,
                "url": href,
                "image": image,
                "length": length
            })
                
        if not found_any:
            break
            
        page += 1
        
    with open(PLANS_SOURCE_PATH, "w", encoding="utf-8") as f:
        json.dump(plans, f, indent=2)
    return plans