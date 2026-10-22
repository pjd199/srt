import os
import json
from bs4 import BeautifulSoup
from ebooklib import epub
import html2text
from .cache import fetch_url
from .bible import get_bible_text
from unicodedata import normalize

def build_plan(slug_or_url: str, refresh: bool = False):
    """
    Parses a plan URL or slug, downloads the plan overview (acting as the main index),
    extracts links, day numbers, and titles to individual study day pages via 
    .block__table-content elements, downloads daily images, dynamically parses 
    Scripture Reading references as bible API keys, and builds HTML, Markdown, and EPUB versions.
    """
    if slug_or_url.startswith("http"):
        url = slug_or_url
        slug = url.strip("/").split("/")[-1]
    else:
        slug = slug_or_url
        url = f"https://shereadstruth.com/plans/{slug}/"
        
    # File structure setup
    html_dir = f"./plans/html/{slug}"
    md_dir = f"./plans/md/{slug}"
    epub_dir = f"./plans/epub/{slug}"
    img_dir = f"./plans/images/{slug}"
    
    os.makedirs(html_dir, exist_ok=True)
    os.makedirs(md_dir, exist_ok=True)
    os.makedirs(epub_dir, exist_ok=True)
    os.makedirs(img_dir, exist_ok=True)
    
    # 1. Fetch main plan overview page (acts as plan index)
    try:
        main_html = fetch_url(url, refresh=refresh, ext="html")
    except Exception as e:
        print(f"Error fetching plan overview {url}: {e}")
        return
        
    soup = BeautifulSoup(main_html, "html.parser")
    
    # Extract plan title
    title_elem = soup.find("h1") or soup.select_one(".section__content h2")
    plan_title = title_elem.get_text(strip=True) if title_elem else slug.replace("-", " ").title()
    
    # Extract plan summary / description
    desc_elem = soup.select_one(".section__content p")
    plan_summary = desc_elem.get_text(strip=True) if desc_elem else ""
    
    # Download cover image if present
    cover_img_elem = soup.select_one(".section__image img") or soup.find("img")
    cover_image_path = ""
    if cover_img_elem and cover_img_elem.get("src"):
        cover_url = cover_img_elem["src"]
        try:
            img_data = fetch_url(cover_url, ext="jpg", binary=True)
            cover_image_path = os.path.join(img_dir, "cover.jpg")
            with open(cover_image_path, "wb") as f:
                f.write(img_data)
        except Exception:
            pass

    # 2. Extract links and titles to individual daily study days from table of contents blocks
    day_anchors = soup.select("a:has(.block__table-content)")
    if not day_anchors:
        day_anchors = [a for a in soup.find_all("a", href=True) if a.find(class_="block__table-content")]

    raw_day_links = []
    for idx, a in enumerate(day_anchors, start=1):
        href = a.get("href", "")
        if href.startswith("/"):
            href = f"https://shereadstruth.com{href}"
            
        table_content = a.find(class_="block__table-content")
        day_num = idx
        day_title = f"Day {idx}"
        
        if table_content:
            p_day = table_content.find("p")
            if p_day:
                nums = "".join(filter(str.isdigit, p_day.get_text()))
                if nums.isdigit():
                    day_num = int(nums)
                    
            h5_title = table_content.find("h5")
            if h5_title:
                day_title = h5_title.get_text(strip=True)
                
        raw_day_links.append({
            "day": day_num,
            "title": day_title,
            "url": href
        })

    days_data = []
    
    # 3. Scrape each targeted daily study page
    for item in raw_day_links:
        try:
            day_html = fetch_url(item["url"], ext="html")
            day_soup = BeautifulSoup(day_html, "html.parser")
            
            # 1. Author extraction from .post__meta or fallback signature
            author = "She Reads Truth"
            author_el = day_soup.select_one(".post__meta h6")
            if author_el:
                a_tag = author_el.find("a")
                if a_tag:
                    author = a_tag.get_text(strip=True)
                else:
                    text = author_el.get_text(strip=True)
                    if text.upper().startswith("BY"):
                        author = text[2:].strip()
            
            # 2. Scripture Reading extraction from <strong> tag inside post entry
            bible_ref = ""
            entry_el = day_soup.select_one(".post__entry")
            
            if entry_el:
                strong_el = entry_el.find("strong")
                if strong_el and "Scripture Reading" in strong_el.get_text():
                    ref_text = strong_el.get_text(strip=True)
                    if "Scripture Reading:" in ref_text:
                        ref_text = ref_text.split(":", 1)[-1].strip()
                    bible_ref = ref_text
                    strong_el.parent.decompose()
                else:
                    scripture_el = day_soup.find(class_="js-replace")
                    if scripture_el:
                        ref_text = scripture_el.get_text(strip=True)
                        if "Scripture Reading:" in ref_text:
                            ref_text = ref_text.split(":")[-1].strip()
                        bible_ref = ref_text
            
            if not bible_ref:
                bible_ref = f"Day {item['day']} Reading"
            

            # 3. Devotional body content cleaning (remove trailing italicized author signature if present)
            if entry_el:
                last_p = entry_el.select_one("p:last-of-type")
                if last_p and last_p.find("em") and "Written by" in last_p.get_text():
                    if author == "She Reads Truth":
                        sig_text = last_p.get_text(strip=True)
                        if "Written by" in sig_text:
                            author = sig_text.replace("Written by", "").strip()
                    last_p.decompose()

                entry_el.attrs.clear()
                for tag in entry_el.find_all(True):
                    tag.attrs.clear()

                # Convert to string and remove line breaks
                raw_html = str(entry_el)

                # Normalize unicode and tidy output
                devotional_html = normalize("NFKD", raw_html.replace("\n", ""))
            else:
                devotional_html = "<p>Devotional content.</p>"
            
            # 4. Daily image extraction targeting <div class="section__image">
            day_img_el = day_soup.select_one(".section__image img")
            day_img_filename = ""
            if day_img_el and day_img_el.get("src"):
                try:
                    d_img_data = fetch_url(day_img_el["src"], ext="jpg", binary=True)
                    day_img_filename = f"day{item['day']:03d}.jpg"
                    with open(os.path.join(img_dir, day_img_filename), "wb") as f:
                        f.write(d_img_data)
                except Exception:
                    pass
                    
            days_data.append({
                "day": item["day"],
                "title": item["title"],
                "author": author,
                "bible_ref": bible_ref,
                "devotional": devotional_html,
                "image": day_img_filename,
                "url": item["url"]
            })
        except Exception:
            continue

    # sort the days into order
    days_data.sort(key=lambda x: x["day"])
    
    # 4. Generate HTML and Markdown files for base and Bible versions (esv, niv, nlt, msg)
    versions = ["base", "esv", "niv", "nlt", "msg"]
    
    for ver in versions:
        print(f"Generating {slug} - {ver}")
        html_filename = os.path.join(html_dir, f"{slug}.html" if ver == "base" else f"{slug}-{ver}.html")
        md_filename = os.path.join(md_dir, f"{slug}.md" if ver == "base" else f"{slug}-{ver}.md")
        
        html_out = f"<html><head><meta charset='utf-8'><title>{plan_title} ({ver.upper()})</title>"
        html_out += "<link rel='stylesheet' href='../../assets/css/style.css'></head><body>"
        html_out += f"<h1>{plan_title}</h1>"
        html_out += f"<div class='summary'><p>{plan_summary}</p></div>"
        
        if cover_image_path:
            html_out += f"<img src='../../images/{slug}/cover.jpg' alt='Cover Image' />"
            
        # Index Table of Contents linking to individual days
        html_out += "<h2>Table of Contents</h2>"
        html_out += "<ul>"
        for d in days_data:
            html_out += f"<li><a href='#day{d['day']}'>(Day {d['day']}) {d['title']}</a> — <em>{d['bible_ref']}</em></li>"
        html_out += "</ul><hr/>"

        
        # Daily chapters
        for d in days_data:
            print(f"Day {d['day']}: {d['title']} ({ver.upper()})")
            html_out += f"<section id='day{d['day']}'>"
            html_out += f"<h2>Day {d['day']}: {d['title']}</h2>"
            html_out += f"<p class='author'>By {d['author']}</p>"
            html_out += f"<p class='bible-ref'><strong>Scripture Reading:</strong> {d['bible_ref']}</p>"
            
            if d['image']:
                html_out += f"<img src='{img_dir}/{d['image']}' alt='Day {d['day']}' />"
                
            # If bible version requested, split comma-separated references and query API sequentially
            if ver != "base" and d['bible_ref']:
                full_scripture_html = ""
                for ref_part in d['bible_ref'].split(","):
                    full_scripture_html += get_bible_text(ref_part.strip(), ver)
                html_out += f"<div class='bible-text'>{full_scripture_html}</div>"

            html_out += "<h3>Devotional</h3>"
            html_out += f"<div class='devotional-body'>{d['devotional']}</div>"
            html_out += "</section><hr/>"
            
        html_out += "</body></html>"

        pretty_full_html = BeautifulSoup(html_out, "html.parser").prettify()
        with open(html_filename, "w", encoding="utf-8") as f:
            f.write(pretty_full_html)
            
        # Markdown conversion
        try:
            h2t = html2text.HTML2Text()
            h2t.body_width = 0
            with open(md_filename, "w", encoding="utf-8") as mf:
                mf.write(h2t.handle(html_out))
        except Exception:
            pass

def build_epub(slug: str, version: str = "base"):
    epub_dir = f"./plans/epub/{slug}"
    img_dir = f"./plans/images/{slug}"
    os.makedirs(epub_dir, exist_ok=True)
    
    book = epub.EpubBook()
    book.set_identifier(f"srt-{slug}-{version}")
    book.set_title(f"She Reads Truth - {slug.replace('-', ' ').title()} ({version.upper()})")
    book.set_language("en")
    book.add_author("She Reads Truth")
    
    # Read your central CSS file from disk
    css_path = "./assets/css/style.css"
    if os.path.exists(css_path):
        with open(css_path, "rb") as f:
            style_content = f.read()
    else:
        style_content = b"body { font-family: serif; margin: 5%; }"

    # Create an EpubItem for the stylesheet
    css_item = epub.EpubItem(
        uid="style",
        file_name="style.css",  # Stored inside the EPUB's internal structure
        media_type="text/css",
        content=style_content
    )

    # Add it to the book manifest
    book.add_item(css_item)
    
    # 1. Handle Cover Image
    cover_path = os.path.join(img_dir, "cover.jpg")
    if os.path.exists(cover_path):
        with open(cover_path, "rb") as f:
            cover_data = f.read()
        # Set EPUB cover image
        book.set_cover("cover.jpg", cover_data)
        
    chapters = []
    
    # 2. Process HTML file sections and embed daily images
    html_path = f"./plans/html/{slug}/{slug}.html" if version == "base" else f"./plans/html/{slug}/{slug}-{version}.html"
    
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")
            
        sections = soup.find_all("section")
        for idx, sec in enumerate(sections, start=1):
            sec_title = sec.find("h2")
            title_text = sec_title.get_text(strip=True) if sec_title else f"Day {idx}"
            
            # Check for images inside this section and add them to the EPUB manifest
            for img in sec.find_all("img"):
                src = img.get("src", "")
                if "images/" in src:
                    # Extract local image filename (e.g., day001.jpg)
                    img_filename = os.path.basename(src)
                    local_img_path = os.path.join(img_dir, img_filename)
                    
                    if os.path.exists(local_img_path):
                        with open(local_img_path, "rb") as img_file:
                            img_bytes = img_file.read()
                            
                        # Create an EpubItem for the image
                        epub_img = epub.EpubItem(
                            uid=f"img_{idx}_{img_filename}",
                            file_name=f"images/{img_filename}",
                            media_type="image/jpeg",
                            content=img_bytes
                        )
                        book.add_item(epub_img)
                        
                        # Update the image `src` attribute for internal EPUB package structure
                        img["src"] = f"images/{img_filename}"
            
            c = epub.EpubHtml(title=title_text, file_name=f"day_{idx:03d}.xhtml", lang="en")
            c.content = str(sec)
            c.add_item(css_item)
            book.add_item(c)
            chapters.append(c)
            
    if not chapters:
        c = epub.EpubHtml(title="Introduction", file_name="intro.xhtml", lang="en")
        c.content = f"<h1>{slug}</h1><p>Please run 'srt build {slug}' first.</p>"
        c.add_item(css_item)
        book.add_item(c)
        chapters.append(c)
        
    # Table of contents & navigation setup
    book.toc = tuple(chapters)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    
    # Define spine
    book.spine = ["nav"] + chapters
    
    epub_filename = f"{epub_dir}/{slug}.epub" if version == "base" else f"{epub_dir}/{slug}-{version}.epub"
    epub.write_epub(epub_filename, book)

def build_index_site():
    os.makedirs("./pages", exist_ok=True)
    index_html = "<html><head><title>SRT Reading Plans</title><link rel='stylesheet' href='./assets/css/style.css'></head><body>"
    index_html += "<h1>Available Downloaded Reading Plans</h1><ul>"
    
    plans_dir = "./plans/html"
    if os.path.exists(plans_dir):
        for slug in os.listdir(plans_dir):
            plan_path = os.path.join("./pages", slug)
            os.makedirs(plan_path, exist_ok=True)
            
            page_content = f"<html><head><title>{slug}</title><link rel='stylesheet' href='../../assets/css/style.css'></head><body>"
            page_content += f"<h1>Plan: {slug}</h1>"
            page_content += "<h2>Downloads</h2><ul>"
            page_content += f"<li>HTML (Base): <a href='../../plans/html/{slug}/{slug}.html'>Download</a></li>"
            page_content += f"<li>Markdown: <a href='../../plans/md/{slug}/{slug}.md'>Download</a></li>"
            page_content += f"<li>EPUB (Base): <a href='../../plans/epub/{slug}/{slug}.epub'>Download</a></li>"
            page_content += f"<li>EPUB (ESV): <a href='../../plans/epub/{slug}/{slug}-esv.epub'>Download</a></li>"
            page_content += f"<li>EPUB (NIV): <a href='../../plans/epub/{slug}/{slug}-niv.epub'>Download</a></li>"
            page_content += "</ul></body></html>"
            
            with open(os.path.join(plan_path, "index.html"), "w", encoding="utf-8") as pf:
                pf.write(page_content)
                
            index_html += f"<li><a href='./pages/{slug}/index.html'>{slug}</a></li>"
            
    index_html += "</ul></body></html>"
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(index_html)