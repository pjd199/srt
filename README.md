# SRT Scraper

A command-line Python tool to scrape reading plans from [She Reads Truth](https://shereadstruth.com/plans/) and [He Reads Truth](https://hereadstruth.com/plans/), generate HTML, Markdown, and Kindle-compatible EPUB files (with Bible version integrations), and build a local library index.

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
```
Usage: srt download [OPTIONS] SLUG [|esv|niv|nlt|msg]

Download markdown, HTML, and EPUB versions for a plan.

Options:
  --images   Include chapter images.
  --refresh  Force refresh cache.
  --help     Show this message and exit.
```