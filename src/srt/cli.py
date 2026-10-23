import click
from .scraper import scrape_plans_index
from .generator import build_plan, build_epub, build_index_site

@click.group()
def main():
    """SRT Scraper & Kindle EPUB Generator CLI"""
    pass

@main.command()
@click.option("--refresh", is_flag=True, help="Force refresh cache.")
def source(refresh):
    """Scrape available plans and save to ./plans/source.json"""
    click.echo("Scraping plans index...")
    plans = scrape_plans_index(refresh=refresh)
    click.echo(f"Successfully saved {len(plans)} plans to ./plans/source.json")

@main.command()
@click.argument("slug_or_url")
@click.argument(
    "version",
    type=click.Choice(["", "esv", "niv", "nlt", "msg"], case_sensitive=False),
    default="",
)
@click.option("--refresh", is_flag=True, help="Force refresh cache.")
def download(slug_or_url, version, refresh):
    """Download markdown, HTML, and EPUB versions for a plan."""
    build_plan(slug_or_url, version, refresh=refresh)
    
    slug = slug_or_url.strip("/").split("/")[-1]
    build_epub(slug, version=version)
    
    click.echo("Download complete.")

@main.command()
def index():
    """Build the index website linking all downloaded plans."""
    click.echo("Building website index...")
    build_index_site()
    click.echo("Index built successfully.")

if __name__ == "__main__":
    main()
