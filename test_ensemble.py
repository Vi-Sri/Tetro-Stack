#!/usr/bin/env python3
"""
Full Ensemble Test - Cross-Platform iPhone Marketplace Scraper
Runs OLX India + Facebook Marketplace with Gemini AI parsing
"""

import asyncio
import os
import warnings

warnings.filterwarnings("ignore")

# Tokens should be set via: source env.sh
# Or set environment variables: APIFY_API_TOKEN, GEMINI_API_KEY
if not os.environ.get("APIFY_API_TOKEN"):
    print("❌ Error: APIFY_API_TOKEN not set. Run: source env.sh")
    exit(1)

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from datetime import datetime

from tetro_stack.clients import ApifyMarketplaceClient, Platform
from tetro_stack.exporters import DataExporter
from tetro_stack.filters.inventory_filter import InventoryFilter

console = Console()


async def scrape_olx_india(max_items: int = 50):
    """Scrape OLX India for iPhones."""
    console.print("\n[bold blue]📱 OLX India Scrape[/bold blue]")
    console.print("[dim]   Cities: Chennai, Bangalore, Coimbatore[/dim]")
    
    async with ApifyMarketplaceClient(platform=Platform.OLX_INDIA) as client:
        listings = await client.fetch_listings(
            query="iphone",
            max_results=max_items,
        )
        console.print(f"[green]   ✅ Retrieved {len(listings)} listings[/green]")
        return listings


async def scrape_facebook(max_items: int = 50):
    """Scrape Facebook Marketplace for iPhones."""
    console.print("\n[bold magenta]📱 Facebook Marketplace Scrape[/bold magenta]")
    console.print("[dim]   Cities: Chennai, Bangalore, Coimbatore[/dim]")
    
    async with ApifyMarketplaceClient(platform=Platform.FACEBOOK_MARKETPLACE) as client:
        listings = await client.fetch_listings(
            query="iphone",
            max_results=max_items,
        )
        console.print(f"[green]   ✅ Retrieved {len(listings)} listings[/green]")
        return listings


def display_summary(olx_listings, fb_listings):
    """Display summary statistics."""
    console.print("\n" + "="*60)
    console.print(Panel.fit(
        "[bold green]📊 ENSEMBLE SCRAPE SUMMARY[/bold green]",
        border_style="green"
    ))
    
    all_listings = olx_listings + fb_listings
    
    # Stats table
    stats_table = Table(title="Platform Statistics", show_header=True)
    stats_table.add_column("Platform", style="cyan")
    stats_table.add_column("Listings", style="green", justify="right")
    stats_table.add_column("Avg Price", style="yellow", justify="right")
    stats_table.add_column("Price Range", style="magenta")
    
    for name, listings in [("OLX India", olx_listings), ("Facebook", fb_listings)]:
        if listings:
            prices = [l.price for l in listings if l.price > 0]
            avg = sum(prices) / len(prices) if prices else 0
            min_p = min(prices) if prices else 0
            max_p = max(prices) if prices else 0
            stats_table.add_row(
                name,
                str(len(listings)),
                f"₹{avg:,.0f}",
                f"₹{min_p:,.0f} - ₹{max_p:,.0f}"
            )
    
    stats_table.add_row(
        "[bold]TOTAL[/bold]",
        f"[bold]{len(all_listings)}[/bold]",
        "-",
        "-"
    )
    
    console.print(stats_table)
    
    # Model breakdown
    model_counts = {}
    for listing in all_listings:
        model = listing.model.value if listing.model else "Unknown"
        model_counts[model] = model_counts.get(model, 0) + 1
    
    if model_counts:
        model_table = Table(title="\n📱 iPhone Model Distribution", show_header=True)
        model_table.add_column("Model", style="cyan")
        model_table.add_column("Count", style="green", justify="right")
        
        for model, count in sorted(model_counts.items(), key=lambda x: -x[1])[:12]:
            model_table.add_row(model, str(count))
        
        console.print(model_table)
    
    return all_listings


def display_top_listings(listings, title: str, limit: int = 10):
    """Display top listings in a table."""
    table = Table(title=title, show_lines=True)
    
    table.add_column("Model", style="cyan", max_width=18)
    table.add_column("Storage", style="magenta")
    table.add_column("Price", style="bold green")
    table.add_column("City", style="blue", max_width=15)
    table.add_column("Source", style="yellow")
    table.add_column("Age", style="dim")
    
    for listing in listings[:limit]:
        model_str = listing.model.value if listing.model else listing.title[:16]
        storage_str = listing.storage.value if listing.storage else "?"
        city = (listing.seller.city or "")[:15] if listing.seller else ""
        age = f"{listing.days_active}d" if hasattr(listing, 'days_active') else "-"
        
        table.add_row(
            model_str,
            storage_str,
            f"₹{listing.price:,.0f}",
            city,
            listing.source[:8] if listing.source else "-",
            age
        )
    
    console.print(table)


async def main():
    start_time = datetime.now()
    
    console.print(Panel.fit(
        "[bold cyan]🚀 TETRO-STACK ENSEMBLE SCRAPER[/bold cyan]\n"
        "Cross-Platform iPhone Marketplace Intelligence\n\n"
        "[dim]Platforms: OLX India + Facebook Marketplace[/dim]\n"
        "[dim]Cities: Chennai, Bangalore, Coimbatore[/dim]\n"
        "[dim]AI Parser: Gemini 2.0 Flash[/dim]",
        border_style="cyan"
    ))
    
    # Run scrapers
    console.print("\n[yellow]⏳ Starting scrapers (this may take 2-4 minutes)...[/yellow]")
    
    olx_listings = []
    fb_listings = []
    
    try:
        olx_listings = await scrape_olx_india(max_items=100)
    except Exception as e:
        console.print(f"[red]   ❌ OLX India failed: {e}[/red]")
    
    try:
        fb_listings = await scrape_facebook(max_items=100)
    except Exception as e:
        console.print(f"[red]   ❌ Facebook failed: {e}[/red]")
    
    # Display summary
    all_listings = display_summary(olx_listings, fb_listings)
    
    # Filter recent listings (5 days)
    recent_listings = [l for l in all_listings if l.days_active <= 5]
    console.print(f"\n[cyan]📅 Recent listings (≤5 days): {len(recent_listings)}[/cyan]")
    
    # Sort by price and show best deals
    if recent_listings:
        sorted_by_price = sorted(recent_listings, key=lambda x: x.price if x.price > 0 else float('inf'))
        display_top_listings(sorted_by_price, "💰 Best Deals (Lowest Price First)")
    
    # Export
    exporter = DataExporter(output_dir="exports")
    
    if all_listings:
        csv_path = exporter.to_csv(all_listings, filename="ensemble_all.csv")
        console.print(f"\n[green]💾 All listings exported: {csv_path}[/green]")
    
    if recent_listings:
        csv_path = exporter.to_csv(recent_listings, filename="ensemble_recent.csv")
        console.print(f"[green]💾 Recent listings exported: {csv_path}[/green]")
    
    # Timing
    elapsed = (datetime.now() - start_time).total_seconds()
    console.print(f"\n[dim]⏱️ Total time: {elapsed:.1f} seconds[/dim]")
    
    console.print("\n[bold green]✅ Ensemble scrape completed![/bold green]")


if __name__ == "__main__":
    asyncio.run(main())

