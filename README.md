# SRT Scraper & EPUB Converter

A command-line Python tool to scrape reading plans from [She Reads Truth](https://shereadstruth.com/plans/), generate HTML, Markdown, and Kindle-compatible EPUB files (with Bible version integrations), and build a local library index.

## Features
- Scrapes all available plans from She Reads Truth with caching and rate-limiting.
- Pulls full scripture text for ESV, NIV, NLT, and MSG versions via APIs.
- Converts plans to clean HTML, Markdown, and KF8/Kindle-ready EPUB formats.
- Generates a local index website for easy file access and downloads.

## Installation

```bash
pip install -e .
```

Set environment variables for Bible APIs:
```bash
export ESV_API_KEY="your_esv_key"
export API_BIBLE_KEY="your_api_bible_key"
```

## CLI Usage

- `srt source` - Scrapes available plans into `./plans/source.json`.
- `srt build <slug|url>` - Builds HTML and Markdown for a specific plan.
- `srt epub <slug>` - Generates EPUB files for a plan.
- `srt download <slug|url>` - Complete pipeline (Markdown, HTML, EPUB across versions).
- `srt index` - Builds `index.html` referencing processed plans.
