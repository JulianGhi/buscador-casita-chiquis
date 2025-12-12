"""Command-line interface for the Argentina Real Estate Scraper."""

import asyncio
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from argentina_scraper.models.database import init_db
from argentina_scraper.storage import export_to_csv, get_property_count, save_property

app = typer.Typer(
    name="arscraper",
    help="Web scraper for Argentine real estate portals",
    add_completion=False,
)
console = Console()


@app.command()
def scrape(
    source: str = typer.Argument(
        ...,
        help="Source to scrape: argenprop, zonaprop, or mercadolibre",
    ),
    operation: str = typer.Option(
        "rent",
        "--operation", "-o",
        help="Operation type: rent or sale",
    ),
    property_type: str = typer.Option(
        "apartment",
        "--type", "-t",
        help="Property type: apartment, house, ph, land, office, local",
    ),
    location: Optional[str] = typer.Option(
        None,
        "--location", "-l",
        help="Neighborhood or city name (e.g., Palermo, Belgrano)",
    ),
    max_pages: int = typer.Option(
        5,
        "--pages", "-p",
        help="Maximum pages to scrape",
    ),
    save: bool = typer.Option(
        True,
        "--save/--no-save",
        help="Save results to database",
    ),
):
    """Scrape properties from a specific source."""
    init_db()

    console.print(f"[bold blue]Scraping {source}...[/bold blue]")
    console.print(f"  Operation: {operation}")
    console.print(f"  Type: {property_type}")
    console.print(f"  Location: {location or 'All'}")
    console.print(f"  Max pages: {max_pages}")
    console.print()

    async def run_scraper():
        count = 0
        saved = 0

        if source == "argenprop":
            from argentina_scraper.scrapers import ArgenpropScraper

            async with ArgenpropScraper() as scraper:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console,
                ) as progress:
                    task = progress.add_task("Scraping Argenprop...", total=None)

                    async for prop in scraper.search(
                        operation=operation,
                        property_type=property_type,
                        location=location,
                        max_pages=max_pages,
                    ):
                        count += 1
                        progress.update(task, description=f"Found {count} properties...")

                        if save:
                            try:
                                save_property(prop)
                                saved += 1
                            except Exception as e:
                                console.print(f"[red]Error saving: {e}[/red]")

        elif source == "zonaprop":
            from argentina_scraper.scrapers import ZonapropScraper

            async with ZonapropScraper() as scraper:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console,
                ) as progress:
                    task = progress.add_task("Scraping Zonaprop...", total=None)

                    async for prop in scraper.search(
                        operation=operation,
                        property_type=property_type,
                        location=location,
                        max_pages=max_pages,
                    ):
                        count += 1
                        progress.update(task, description=f"Found {count} properties...")

                        if save:
                            try:
                                save_property(prop)
                                saved += 1
                            except Exception as e:
                                console.print(f"[red]Error saving: {e}[/red]")

        elif source == "mercadolibre":
            from argentina_scraper.scrapers import MercadoLibreClient

            async with MercadoLibreClient() as client:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console,
                ) as progress:
                    task = progress.add_task("Fetching from MercadoLibre API...", total=None)

                    async for prop in client.search(
                        operation=operation,
                        property_type=property_type,
                        neighborhood=location,
                        max_results=max_pages * 50,  # ~50 per page
                    ):
                        count += 1
                        progress.update(task, description=f"Found {count} properties...")

                        if save:
                            try:
                                save_property(prop)
                                saved += 1
                            except Exception as e:
                                console.print(f"[red]Error saving: {e}[/red]")

        else:
            console.print(f"[red]Unknown source: {source}[/red]")
            console.print("Available sources: argenprop, zonaprop, mercadolibre")
            raise typer.Exit(1)

        return count, saved

    count, saved = asyncio.run(run_scraper())

    console.print()
    console.print(f"[green]✓ Found {count} properties[/green]")
    if save:
        console.print(f"[green]✓ Saved {saved} to database[/green]")


@app.command()
def stats():
    """Show database statistics."""
    init_db()

    table = Table(title="Database Statistics")
    table.add_column("Source", style="cyan")
    table.add_column("Count", style="green", justify="right")

    sources = ["argenprop", "zonaprop", "mercadolibre"]
    total = 0

    for source in sources:
        count = get_property_count(source)
        table.add_row(source, str(count))
        total += count

    table.add_row("─" * 15, "─" * 8)
    table.add_row("[bold]Total[/bold]", f"[bold]{total}[/bold]")

    console.print(table)


@app.command()
def export(
    filepath: str = typer.Argument(
        "properties.csv",
        help="Output CSV file path",
    ),
    source: Optional[str] = typer.Option(
        None,
        "--source", "-s",
        help="Filter by source (argenprop, zonaprop, mercadolibre)",
    ),
):
    """Export properties to CSV file."""
    init_db()

    console.print(f"[bold]Exporting to {filepath}...[/bold]")

    count = export_to_csv(filepath, source)

    if count > 0:
        console.print(f"[green]✓ Exported {count} properties to {filepath}[/green]")
    else:
        console.print("[yellow]No properties to export[/yellow]")


@app.command()
def init():
    """Initialize the database."""
    init_db()
    console.print("[green]✓ Database initialized[/green]")


@app.command()
def test_scraper(
    source: str = typer.Argument(
        ...,
        help="Source to test: argenprop, zonaprop, or mercadolibre",
    ),
):
    """Test a scraper with a single page/request."""
    console.print(f"[bold]Testing {source} scraper...[/bold]")

    async def run_test():
        if source == "argenprop":
            from argentina_scraper.scrapers import ArgenpropScraper

            async with ArgenpropScraper() as scraper:
                count = 0
                async for prop in scraper.search(max_pages=1):
                    count += 1
                    if count == 1:
                        console.print(f"[green]✓ First property found:[/green]")
                        console.print(f"  Title: {prop.title}")
                        console.print(f"  Price: {prop.currency} {prop.price}")
                        console.print(f"  URL: {prop.url}")
                    if count >= 3:
                        break
                return count

        elif source == "zonaprop":
            from argentina_scraper.scrapers import ZonapropScraper

            console.print("[yellow]Note: Zonaprop requires Playwright. Installing if needed...[/yellow]")
            async with ZonapropScraper() as scraper:
                count = 0
                async for prop in scraper.search(max_pages=1):
                    count += 1
                    if count == 1:
                        console.print(f"[green]✓ First property found:[/green]")
                        console.print(f"  Title: {prop.title}")
                        console.print(f"  Price: {prop.currency} {prop.price}")
                        console.print(f"  URL: {prop.url}")
                    if count >= 3:
                        break
                return count

        elif source == "mercadolibre":
            from argentina_scraper.scrapers import MercadoLibreClient

            async with MercadoLibreClient() as client:
                count = 0
                async for prop in client.search(max_results=3):
                    count += 1
                    if count == 1:
                        console.print(f"[green]✓ First property found:[/green]")
                        console.print(f"  Title: {prop.title}")
                        console.print(f"  Price: {prop.currency} {prop.price}")
                        console.print(f"  URL: {prop.url}")
                return count

        else:
            console.print(f"[red]Unknown source: {source}[/red]")
            return 0

    try:
        count = asyncio.run(run_test())
        console.print(f"\n[green]✓ Test successful! Found {count} properties[/green]")
    except Exception as e:
        console.print(f"\n[red]✗ Test failed: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
