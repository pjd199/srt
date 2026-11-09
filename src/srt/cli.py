import click
from .generator import download_plan, markdown_conversion, build_epub, SHEREADSTRUTH, HEREADSTRUTH

@click.group()
def main():
    """SRT Scraper & Kindle EPUB Generator CLI"""
    pass

@main.command()
@click.argument("slug")
@click.argument(
    "version",
    type=click.Choice(["", "esv", "niv", "nlt", "msg"], case_sensitive=False),
    default="",
)
@click.option("--images", is_flag=True, default=False, help="Include chapter images.")
@click.option("--refresh", is_flag=True, help="Force refresh cache.")
def download(slug, version, refresh, images):
    """Download markdown, HTML, and EPUB versions for a plan."""
    for domain in (SHEREADSTRUTH, HEREADSTRUTH):
        download_plan(domain, slug, version=version, refresh=refresh)
        markdown_conversion(domain, slug, version=version)
        build_epub(domain, slug, version=version, images=images)
    click.echo("Download complete.")

if __name__ == "__main__":
    main()
