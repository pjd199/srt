import os
from bs4 import BeautifulSoup
from ebooklib import epub
import html2text
from .cache import fetch_url
from .bible import get_bible_text, get_copyright
from unicodedata import normalize
from re import search, IGNORECASE
from datetime import datetime

# domains
SHEREADSTRUTH = "shereadstruth.com"
HEREADSTRUTH = "hereadstruth.com"
URL = "http://{domain}/plans/{slug}"

# file structure
HTML_DIR = "./plans/{domain}/html/{slug}"
MD_DIR = "./plans/{domain}/md/{slug}"
EPUB_DIR = "./plans/{domain}/epub/{slug}"
IMG_DIR = "./plans/{domain}/images/{slug}"

def index_plan(domain: str, slug: str, refresh: bool = False):
    """Download the plan index, and extract links to each day."""
    url = URL.format(domain=domain, slug=slug)
    try:
        print(f"Fetching plan index for {slug} on {domain}")
        main_html = fetch_url(url, refresh=refresh, ext="html")
    except Exception as e:
        print(f"Error fetching plan overview {url}: {e}")
        return

    soup = BeautifulSoup(main_html, "html.parser")

    # Extract plan title
    title_elem = soup.find("h1") or soup.select_one(".section__content h2")
    plan_title = (
        title_elem.get_text(strip=True)
        if title_elem
        else slug.replace("-", " ").title()
    )

    print(f"Indexing data for {plan_title}")

    # Extract plan summary / description
    desc_elem = soup.select_one(".section__content p, .plan-overview__copy")
    plan_summary = desc_elem.get_text(strip=True) if desc_elem else ""

    # Download cover image if present
    cover_img_elem = soup.select_one(".section__image img") or soup.find("img")
    cover_image_path = ""
    if cover_img_elem and cover_img_elem.get("src"):
        cover_url = cover_img_elem["src"]
        img_data = fetch_url(cover_url, ext="jpg", binary=True)
        img_dir = IMG_DIR.format(domain=domain, slug=slug)
        os.makedirs(img_dir, exist_ok=True)
        cover_image_path = os.path.join(img_dir, "cover.jpg")
        with open(cover_image_path, "wb") as f:
            f.write(img_data)

    # Extract links
    day_anchors = soup.select("a:has(.block__table-content), a.daily-reading-list")
    if not day_anchors:
        day_anchors = [
            a
            for a in soup.find_all("a", href=True)
            if a.find(class_="block__table-content")
            or "daily-reading-list" in a.get("class", [])
        ]

    raw_day_links = {}
    for a in day_anchors:
        href = a.get("href", "")
        if href.startswith("/"):
            href = f"https://{domain}{href}"
        text = a.get_text()
        day_match = search(r"Day(?:\s*|&nbsp)(\d+)", text, IGNORECASE)
        day = int(day_match.group(1)) if day_match else 0

        raw_day_links[day] = href

    # sort the days into order
    return (
        plan_title,
        plan_summary,
        cover_image_path,
        {key: raw_day_links[key] for key in sorted(raw_day_links)},
    )


def download_day(
    domain: str, slug: str, day: int, url: str, version: str = "", refresh: bool = False
):
    print(f"Downloading day {day} at {url}")
    day_html = fetch_url(url, ext="html", refresh=refresh)
    day_soup = BeautifulSoup(day_html, "html.parser")

    title = day_soup.select_one("h1").text.strip()

    # 1. Author extraction from .post__meta or fallback signature
    author = "Unknown"
    author_el = day_soup.select_one(".post__meta h6, .post-type-post h6")
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

    # 1. Try She Reads Truth style (.js-replace)
    scripture_el = day_soup.find(class_="js-replace")
    if scripture_el:
        ref_text = scripture_el.get_text(strip=True)
        if "Scripture Reading:" in ref_text:
            ref_text = ref_text.split(":")[-1].strip()
        bible_ref = ref_text

    # 2. If blank, try He Reads Truth style (.scripture-reference)
    if not bible_ref:
        scripture_ref_div = day_soup.find(class_="scripture-reference")
        if scripture_ref_div:
            p_tag = scripture_ref_div.find("strong")
            if p_tag:
                bible_ref = p_tag.get_text(strip=True)

    scripture_html = ""
    if bible_ref:
        if version != "":
            scripture_html = "".join(
                get_bible_text(ref_part.strip(), version)
                for ref_part in bible_ref.split(",")
            )
    else:
        bible_ref = f"Day {day} Reading"

    # 3. Devotional body content cleaning
    entry_el = day_soup.select_one(".post__entry, .post-type-post")

    if entry_el:
        last_p = entry_el.select_one("p:last-of-type")
        if last_p and last_p.find("em") and "Written by" in last_p.get_text():
            if author == "Unknown":
                sig_text = last_p.get_text(strip=True)
                if "Written by" in sig_text:
                    author = sig_text.replace("Written by", "").strip()
            last_p.decompose()

        h6_tag = entry_el.select_one("h6")
        if h6_tag:
            h6_tag.decompose()

        br_tag = entry_el.select_one("br")
        if br_tag:
            br_tag.decompose()

        entry_el.attrs.clear()
        for tag in entry_el.find_all(True):
            tag.attrs.clear()

        # Convert to string and remove line breaks
        raw_html = str(entry_el)

        # Normalize unicode and tidy output
        devotional_html = normalize("NFKD", raw_html.replace("\n", ""))
    else:
        devotional_html = "<p>Devotional content.</p>"

    # 4. Daily image extraction targeting
    day_img_el = day_soup.select_one(".section__image img")
    day_img_filename = ""
    if day_img_el and day_img_el.get("src"):
        d_img_data = fetch_url(day_img_el["src"], ext="jpg", binary=True)
        day_img_filename = f"day{day:03d}.jpg"
        img_dir = IMG_DIR.format(domain=domain, slug=slug)
        os.makedirs(img_dir, exist_ok=True)
        with open(os.path.join(img_dir, day_img_filename), "wb") as f:
            f.write(d_img_data)

    return {
        "day": day,
        "title": title,
        "author": author,
        "bible_ref": bible_ref,
        "scripture": scripture_html,
        "devotional": devotional_html,
        "image": day_img_filename,
        "url": url,
    }


def download_plan(
    domain: str, slug: str, version: str = "", images=False, refresh: bool = False
):
    """
    Download a plan and scripture references, saving into a single html file
    """
    plan_title, plan_summary, cover_image_path, index = index_plan(
        domain, slug, refresh
    )
    days_data = [
        download_day(domain, slug, day, url, version, refresh)
        for day, url in index.items()
    ]

    # Generate HTML and Markdown files for base and Bible versions (esv, niv, nlt, msg)
    print(f"Generating HTML for {slug}{'-' + version if version != '' else ''}")
    html_dir = HTML_DIR.format(domain=domain, slug=slug)
    os.makedirs(html_dir, exist_ok=True)
    html_filename = os.path.join(
        html_dir, f"{slug}.html" if version == "" else f"{slug}-{version}.html"
    )

    html_out = f"<html><head><meta charset='utf-8'><title>{plan_title} ({version.upper()})</title>"
    html_out += "<link rel='stylesheet' href='../../assets/css/style.css'></head><body>"
    html_out += f"<h1>{plan_title}</h1>"

    if images and cover_image_path:
        html_out += f"<img src='../../images/{slug}/cover.jpg' alt='Cover Image' />"

    today = datetime.today()
    html_out += "<section id='overview'>"
    html_out += "<h2>Overview</h2>"
    html_out += f"<p>{plan_summary}</p>"
    html_out += f"<p>Plan downloaded from {URL.format(domain=domain,slug=slug)} on {today.day} {today.strftime('%B %Y')}</p>"
    html_out += f"<p>&copy; {"She"if domain == SHEREADSTRUTH else "He"} Reads Truth</p>"
    if version != "":
        html_out += f"<p>Scripture &copy; {version.upper()}</p>"
        html_out += f"<p>{get_copyright(version)}</p>"
    html_out += "</section>"

    # Index Table of Contents linking to individual days
    html_out += "<div class='toc'><h2>Table of Contents</h2></div>"
    html_out += "<ul>"
    for d in days_data:
        html_out += f"<li><a href='#day{d['day']}'>(Day {d['day']}) {d['title']}</a> — <em>{d['bible_ref']}</em></li>"
    html_out += "</ul><hr/></div>"

    # Daily chapters
    for d in days_data:
        print(
            f"Day {d['day']}: {d['title']} {'(' + version.upper() + ')' if version != '' else ''}"
        )

        html_out += f"<section id='day{d['day']}'>"
        html_out += f"<h2>Day {d['day']}: {d['title']}</h2>"
        html_out += f"<p class='author'>By {d['author']}</p>"
        html_out += f"<p class='bible-ref'><strong>Scripture Reading:</strong> {d['bible_ref']}</p>"

        if images and d["image"]:
            html_out += f"<img src='{IMG_DIR.format(domain=domain,slug=slug)}/{d['image']}' alt='Day {d['day']}' />"

        # Add scripture, if requested
        if version != "":
            html_out += f"<div class='bible-text'>{d['scripture']}</div>"

        html_out += "<h3>Devotional</h3>"
        html_out += f"<div class='devotional-body'>{d['devotional']}</div>"
        html_out += "</section><hr/>"

    html_out += "</body></html>"

    pretty_full_html = BeautifulSoup(html_out, "html.parser").prettify()
    with open(html_filename, "w", encoding="utf-8") as f:
        f.write(pretty_full_html)


def markdown_conversion(domain: str, slug: str, version: str = ""):
    """Markdown conversion."""
    print(f"Converting HTML to Markdown for {slug}{'-' + version if version != '' else ''}")
    md_dir = MD_DIR.format(domain=domain, slug=slug)
    os.makedirs(md_dir, exist_ok=True)
    md_filename = os.path.join(
        md_dir, f"{slug}.md" if version == "" else f"{slug}-{version}.md"
    )
    h2t = html2text.HTML2Text()
    h2t.body_width = 0

    html_filename = os.path.join(
        HTML_DIR.format(domain=domain, slug=slug),
        f"{slug}.html" if version == "" else f"{slug}-{version}.html",
    )
    with open(html_filename) as html_file:
        html = html_file.read()
        with open(md_filename, "w", encoding="utf-8") as mf:
            mf.write(h2t.handle(html))

def build_epub(domain: str, slug: str, version: str = "", images=False):

    print(f"Generating epub for {slug}{'-' + version if version != '' else ''}")

    epub_dir = EPUB_DIR.format(domain=domain, slug=slug)
    os.makedirs(epub_dir, exist_ok=True)

    book = epub.EpubBook()
    book.set_language("en")
    if domain == SHEREADSTRUTH:
        book.set_identifier(f"srt-{slug}-{version}")
        book.set_title(
            f"She Reads Truth - {slug.replace('-', ' ').title()} ({version.upper()})"
        )
        book.add_author("She Reads Truth")
    else:
        book.set_identifier(f"hrt-{slug}-{version}")
        book.set_title(
            f"He Reads Truth - {slug.replace('-', ' ').title()} ({version.upper()})"
        )
        book.add_author("He Reads Truth")

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
        content=style_content,
    )

    # Add it to the book manifest
    book.add_item(css_item)

    # 1. Handle Cover Image
    cover_path = os.path.join(IMG_DIR.format(domain=domain,slug=slug), "cover.jpg")
    if os.path.exists(cover_path):
        with open(cover_path, "rb") as f:
            cover_data = f.read()
        # Set EPUB cover image
        book.set_cover("cover.jpg", cover_data)

    chapters = []

    # 2. Process HTML file sections and embed daily images
    html_path = (
        f"./plans/{domain}/html/{slug}/{slug}.html"
        if version == ""
        else f"./plans/{domain}/html/{slug}/{slug}-{version}.html"
    )

    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")

        sections = soup.find_all("section")
        for idx, sec in enumerate(sections, start=1):
            sec_title = sec.find("h2")
            title_text = sec_title.get_text(strip=True) if sec_title else f"Day {idx}"

            # Check for images inside this section and add them to the EPUB manifest
            if images:
                for img in sec.find_all("img"):
                    src = img.get("src", "")
                    if "images/" in src:
                        # Extract local image filename (e.g., day001.jpg)
                        img_filename = os.path.basename(src)
                        local_img_path = os.path.join(IMG_DIR.format(domain=domain,slug=slug), img_filename)

                        if os.path.exists(local_img_path):
                            with open(local_img_path, "rb") as img_file:
                                img_bytes = img_file.read()

                            # Create an EpubItem for the image
                            epub_img = epub.EpubItem(
                                uid=f"img_{idx}_{img_filename}",
                                file_name=f"images/{img_filename}",
                                media_type="image/jpeg",
                                content=img_bytes,
                            )
                            book.add_item(epub_img)

                            # Update the image `src` attribute for internal EPUB package structure
                            img["src"] = f"images/{img_filename}"

            c = epub.EpubHtml(
                title=title_text, file_name=f"day_{idx:03d}.xhtml", lang="en"
            )
            c.content = str(sec)
            c.add_item(css_item)
            book.add_item(c)
            chapters.append(c)

    # Table of contents & navigation setup
    book.toc = tuple(chapters)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    # Define spine
    book.spine = ["nav"] + chapters

    epub_filename = (
        f"{epub_dir}/{slug}.epub"
        if version == ""
        else f"{epub_dir}/{slug}-{version}.epub"
    )
    epub.write_epub(epub_filename, book)
