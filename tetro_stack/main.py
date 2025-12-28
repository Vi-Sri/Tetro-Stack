"""
Tetro-Stack Main Entry Point.

Facebook Marketplace iPhone Listings Client.

Usage:
    python -m tetro_stack.main
    
Or with CLI:
    tetro fetch --query "iPhone 15" --days 3
    tetro export --format csv
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

from .config import TetroConfig, ClientType, InventoryFilter
from .clients.apify_client import ApifyMarketplaceClient
from .clients.mcl_client import MetaContentLibraryClient
from .filters.inventory_filter import InventoryFilterEngine, FilterCriteria
from .exporters.data_exporter import DataExporter
from .models.iphone_listing import iPhoneListing, iPhoneSeries

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

console = Console()


class TetroStack:
    """
    Main application class for Tetro-Stack.
    
    Orchestrates the fetching, filtering, and exporting of
    iPhone listings from Facebook Marketplace.
    """
    
    def __init__(self, config: Optional[TetroConfig] = None):
        """
        Initialize Tetro-Stack.
        
        Args:
            config: Configuration object (uses defaults if not provided)
        """
        self.config = config or TetroConfig()
        self.filter_engine = InventoryFilterEngine()
        self.exporter = DataExporter()
        self._client = None
    
    def _get_client(self):
        """Get the appropriate client based on configuration."""
        if self._client:
            return self._client
            
        if self.config.active_client == ClientType.META_CONTENT_LIBRARY:
            self._client = MetaContentLibraryClient(self.config.mcl)
        elif self.config.active_client == ClientType.APIFY_SCRAPER:
            self._client = ApifyMarketplaceClient(self.config.apify)
        else:
            raise ValueError(f"Unsupported client type: {self.config.active_client}")
        
        return self._client
    
    async def fetch_iphone_listings(
        self,
        query: str = "iPhone",
        location: str = "United States",
        max_results: int = 100,
        days_filter: Optional[int] = None,
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
    ) -> list[iPhoneListing]:
        """
        Fetch iPhone listings from Marketplace.
        
        Args:
            query: Search query
            location: Location filter
            max_results: Maximum listings to fetch
            days_filter: Only listings from last N days
            min_price: Minimum price
            max_price: Maximum price
            
        Returns:
            List of iPhoneListing objects
        """
        client = self._get_client()
        
        if not client.is_authenticated():
            raise RuntimeError(
                f"Client {self.config.active_client.value} is not properly configured. "
                "Check your .env file for required credentials."
            )
        
        console.print(f"[bold blue]Fetching listings...[/bold blue]")
        console.print(f"  Query: {query}")
        console.print(f"  Location: {location}")
        console.print(f"  Max results: {max_results}")
        if days_filter:
            console.print(f"  Days filter: {days_filter}")
        
        listings = await client.fetch_listings(
            query=query,
            location=location,
            max_results=max_results,
            min_price=min_price,
            max_price=max_price,
            days_filter=days_filter,
        )
        
        console.print(f"[bold green]Fetched {len(listings)} listings[/bold green]")
        
        return listings
    
    def filter_listings(
        self,
        listings: list[iPhoneListing],
        criteria: Optional[FilterCriteria] = None,
        days: Optional[int] = None,
    ) -> list[iPhoneListing]:
        """
        Filter listings based on criteria.
        
        Args:
            listings: List of listings to filter
            criteria: Full filter criteria object
            days: Simple days filter (alternative to full criteria)
            
        Returns:
            Filtered list of listings
        """
        if criteria:
            return self.filter_engine.apply_criteria(listings, criteria)
        elif days:
            return self.filter_engine.filter_by_days(listings, days)
        return listings
    
    def get_inventory_by_time(
        self,
        listings: list[iPhoneListing]
    ) -> dict[str, list[iPhoneListing]]:
        """
        Organize listings by time periods.
        
        Returns:
            Dictionary with 1_day, 3_day, 5_day, 7_day keys
        """
        return {
            "1_day": self.filter_engine.filter_by_days(listings, 1),
            "3_day": self.filter_engine.filter_by_days(listings, 3),
            "5_day": self.filter_engine.filter_by_days(listings, 5),
            "7_day": self.filter_engine.filter_by_days(listings, 7),
        }
    
    def display_summary(self, listings: list[iPhoneListing]):
        """Display a summary of fetched listings."""
        summary = self.filter_engine.get_inventory_summary(listings)
        
        # Create summary panel
        summary_text = f"""
[bold]Total Listings:[/bold] {summary['total']}

[bold]Active Inventory:[/bold]
  • 1 Day:  {summary['1_day']} listings
  • 3 Days: {summary['3_day']} listings  
  • 5 Days: {summary['5_day']} listings
  • 7 Days: {summary['7_day']} listings
        """
        
        console.print(Panel(summary_text, title="📱 Inventory Summary", border_style="blue"))
    
    def display_listings_table(
        self,
        listings: list[iPhoneListing],
        limit: int = 20
    ):
        """Display listings in a formatted table."""
        table = Table(title="iPhone Listings", show_lines=True)
        
        table.add_column("Model", style="cyan", no_wrap=True)
        table.add_column("Storage", style="magenta")
        table.add_column("Color", style="green")
        table.add_column("Battery", style="yellow")
        table.add_column("Price", style="bold red")
        table.add_column("City", style="blue")
        table.add_column("Days", style="dim")
        
        for listing in listings[:limit]:
            battery = (
                f"{listing.battery_health.percentage}%" 
                if listing.battery_health and listing.battery_health.percentage 
                else "N/A"
            )
            
            table.add_row(
                listing.model.value if listing.model else "Unknown",
                listing.storage.value if listing.storage else "Unknown",
                listing.color.value if listing.color else "Unknown",
                battery,
                f"${listing.price:,.0f}",
                listing.seller.city or "Unknown",
                str(listing.days_active),
            )
        
        console.print(table)
        
        if len(listings) > limit:
            console.print(f"[dim]... and {len(listings) - limit} more listings[/dim]")
    
    def export_listings(
        self,
        listings: list[iPhoneListing],
        format: str = "json"
    ) -> str:
        """
        Export listings to file.
        
        Args:
            listings: Listings to export
            format: Export format (json, csv, excel)
            
        Returns:
            Path to exported file
        """
        if format == "json":
            path = self.exporter.to_json(listings)
        elif format == "csv":
            path = self.exporter.to_csv(listings)
        elif format == "excel":
            path = self.exporter.to_excel(listings)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        console.print(f"[bold green]Exported to:[/bold green] {path}")
        return str(path)


async def main():
    """Main entry point."""
    console.print(Panel.fit(
        "[bold magenta]Tetro-Stack[/bold magenta]\n"
        "Facebook Marketplace iPhone Listings Client",
        border_style="magenta"
    ))
    
    # Initialize
    app = TetroStack()
    
    # Check configuration
    if not app.config.is_client_configured():
        console.print("[bold red]Error:[/bold red] Client not configured!")
        console.print("\nPlease set up your credentials in .env file:")
        console.print("  • APIFY_API_TOKEN for Apify scraper")
        console.print("  • Or use Meta Content Library in SRE environment")
        return
    
    try:
        # Fetch listings
        listings = await app.fetch_iphone_listings(
            query="iPhone",
            location="United States",
            max_results=50,
            days_filter=7,
        )
        
        # Display summary
        app.display_summary(listings)
        
        # Display table
        app.display_listings_table(listings)
        
        # Export to CSV
        app.export_listings(listings, format="csv")
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())

