#!/usr/bin/env python3
"""
Integration test for Tetro-Stack cross-platform client.

Tests the OLX India scraper with real API calls.
"""

import asyncio
import os
from datetime import datetime

# API tokens should be set via: source env.sh
# Or set environment variables: APIFY_API_TOKEN, GEMINI_API_KEY
if not os.environ.get("APIFY_API_TOKEN"):
    print("❌ Error: APIFY_API_TOKEN not set. Run: source env.sh")
    exit(1)

from tetro_stack.clients import ApifyMarketplaceClient, Platform
from tetro_stack.filters import InventoryFilterEngine
from tetro_stack.exporters import DataExporter

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


async def test_token_validation():
    """Test token validation."""
    console.print("\n[bold cyan]1. Testing Token Validation[/bold cyan]")
    console.print("-" * 40)
    
    async with ApifyMarketplaceClient() as client:
        if client.is_authenticated():
            console.print("✅ Token is configured")
            
            try:
                user_info = await client.validate_token()
                console.print(f"✅ Token is valid")
                console.print(f"   User: {user_info.get('username', 'N/A')}")
                console.print(f"   Email: {user_info.get('email', 'N/A')}")
                return True
            except Exception as e:
                console.print(f"❌ Token validation failed: {e}")
                return False
        else:
            console.print("❌ Token not configured")
            return False


async def test_fetch_from_last_run():
    """Test fetching data from last run (no new scrape)."""
    console.print("\n[bold cyan]2. Testing Fetch from Last Run[/bold cyan]")
    console.print("-" * 40)
    
    async with ApifyMarketplaceClient(platform=Platform.OLX_INDIA) as client:
        try:
            listings = await client.get_last_run_data()
            console.print(f"✅ Retrieved {len(listings)} listings from last run")
            
            if listings:
                # Display sample
                display_listings_table(listings[:5])
                
                # Show inventory summary
                filter_engine = InventoryFilterEngine()
                summary = filter_engine.get_inventory_summary(listings)
                console.print(f"\n📊 Inventory Summary:")
                console.print(f"   1 Day:  {summary['1_day']} listings")
                console.print(f"   3 Days: {summary['3_day']} listings")
                console.print(f"   7 Days: {summary['7_day']} listings")
                console.print(f"   Total:  {summary['total']} listings")
            
            return listings
            
        except Exception as e:
            console.print(f"❌ Failed to fetch: {e}")
            return []


async def test_new_scrape():
    """Test starting a new scrape (uses API credits)."""
    console.print("\n[bold cyan]3. Testing New Scrape (Small)[/bold cyan]")
    console.print("-" * 40)
    console.print("[yellow]⚠️  This will use Apify credits[/yellow]")
    
    async with ApifyMarketplaceClient(platform=Platform.OLX_INDIA) as client:
        try:
            console.print("🚀 Starting scrape for iPhone 15...")
            
            listings = await client.fetch_listings(
                query="iPhone 15",
                location="Mumbai",
                max_results=10,  # Small test
            )
            
            console.print(f"✅ Scraped {len(listings)} listings")
            
            if listings:
                display_listings_table(listings)
            
            return listings
            
        except Exception as e:
            console.print(f"❌ Scrape failed: {e}")
            import traceback
            traceback.print_exc()
            return []


def display_listings_table(listings):
    """Display listings in a formatted table."""
    table = Table(title="iPhone Listings", show_lines=True)
    
    table.add_column("Model", style="cyan", no_wrap=True, max_width=25)
    table.add_column("Storage", style="magenta")
    table.add_column("Price", style="bold red")
    table.add_column("City", style="blue", max_width=20)
    table.add_column("Days", style="dim")
    
    for listing in listings:
        table.add_row(
            listing.model.value if listing.model else listing.title[:25],
            listing.storage.value if listing.storage else "?",
            f"₹{listing.price:,.0f}" if listing.currency == "INR" else f"${listing.price:,.0f}",
            listing.seller.city[:20] if listing.seller.city else "Unknown",
            str(listing.days_active),
        )
    
    console.print(table)


async def test_export():
    """Test exporting data."""
    console.print("\n[bold cyan]4. Testing Export[/bold cyan]")
    console.print("-" * 40)
    
    async with ApifyMarketplaceClient(platform=Platform.OLX_INDIA) as client:
        listings = await client.get_last_run_data()
        
        if listings:
            exporter = DataExporter(output_dir="exports")
            
            # Export to CSV
            csv_path = exporter.to_csv(listings, filename="olx_iphones.csv")
            console.print(f"✅ Exported to CSV: {csv_path}")
            
            # Export to JSON
            json_path = exporter.to_json(listings, filename="olx_iphones.json")
            console.print(f"✅ Exported to JSON: {json_path}")
            
            return True
        else:
            console.print("❌ No listings to export")
            return False


async def main():
    console.print(Panel.fit(
        "[bold magenta]Tetro-Stack Integration Test[/bold magenta]\n"
        "Cross-Platform Marketplace Client",
        border_style="magenta"
    ))
    
    # Test 1: Token validation
    token_ok = await test_token_validation()
    
    if not token_ok:
        console.print("\n[bold red]Cannot proceed without valid token[/bold red]")
        return
    
    # Test 2: Fetch from last run (no credits used)
    listings = await test_fetch_from_last_run()
    
    # Test 3: Export
    if listings:
        await test_export()
    
    # Ask about new scrape
    console.print("\n" + "=" * 60)
    console.print("[yellow]Would you like to run a new scrape? (uses Apify credits)[/yellow]")
    console.print("To run a new scrape, call test_new_scrape() manually")
    
    # Summary
    console.print("\n" + "=" * 60)
    console.print("[bold green]✅ Integration test completed![/bold green]")


if __name__ == "__main__":
    asyncio.run(main())

