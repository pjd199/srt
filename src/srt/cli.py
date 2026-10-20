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

@main.command(name="build")
@click.argument("slug_or_url")
@click.option("--refresh", is_flag=True, help="Force refresh cache.")
def build_cmd(slug_or_url, refresh):
    """Build HTML, Markdown, and assets for a specific plan."""
    click.echo(f"Building plan for {slug_or_url}...")
    build_plan(slug_or_url, refresh=refresh)
    click.echo("Build complete.")

@main.command(name="epub")
@click.argument("slug")
@click.option("--version", default="base", help="Bible version (base, esv, niv, nlt, msg)")
def epub_cmd(slug, version):
    """Generate EPUB for a plan."""
    click.echo(f"Generating EPUB ({version}) for {slug}...")
    build_epub(slug, version=version)
    click.echo("EPUB generation complete.")

@main.command()
@click.argument("slug_or_url")
@click.option("--refresh", is_flag=True, help="Force refresh cache.")
def download(slug_or_url, refresh):
    """Download markdown, HTML, and EPUB versions for a plan."""
    click.echo(f"Running full download pipeline for {slug_or_url}...")
    build_plan(slug_or_url, refresh=refresh)
    
    slug = slug_or_url.strip("/").split("/")[-1]
    for ver in ["base", "esv", "niv", "nlt", "msg"]:
        print(f"Generating epub ({slug}-{ver})")
        build_epub(slug, version=ver)
    
    click.echo("Download complete.")

@main.command()
def index():
    """Build the index website linking all downloaded plans."""
    click.echo("Building website index...")
    build_index_site()
    click.echo("Index built successfully.")

if __name__ == "__main__":
    main()
