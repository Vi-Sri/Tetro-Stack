"""
Data Exporter for iPhone Listings.

Exports listings to various formats: JSON, CSV, Excel.
"""

import json
import csv
from pathlib import Path
from datetime import datetime
from typing import Optional

from ..models.iphone_listing import iPhoneListing


class DataExporter:
    """
    Exporter for iPhone listings data.
    
    Supports:
    - JSON export (full data)
    - CSV export (tabular format)
    - Excel export (with pandas)
    """
    
    def __init__(self, output_dir: str = "exports"):
        """
        Initialize the exporter.
        
        Args:
            output_dir: Directory for exported files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def _generate_filename(self, prefix: str, extension: str) -> Path:
        """Generate a timestamped filename."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return self.output_dir / f"{prefix}_{timestamp}.{extension}"
    
    def to_json(
        self, 
        listings: list[iPhoneListing],
        filename: Optional[str] = None,
        pretty: bool = True
    ) -> Path:
        """
        Export listings to JSON file.
        
        Args:
            listings: List of iPhone listings
            filename: Optional custom filename
            pretty: Whether to format JSON nicely
            
        Returns:
            Path to the exported file
        """
        if filename:
            filepath = self.output_dir / filename
        else:
            filepath = self._generate_filename("iphone_listings", "json")
        
        data = [listing.model_dump(mode="json") for listing in listings]
        
        with open(filepath, "w", encoding="utf-8") as f:
            if pretty:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            else:
                json.dump(data, f, ensure_ascii=False, default=str)
        
        return filepath
    
    def to_csv(
        self,
        listings: list[iPhoneListing],
        filename: Optional[str] = None
    ) -> Path:
        """
        Export listings to CSV file.
        
        Args:
            listings: List of iPhone listings
            filename: Optional custom filename
            
        Returns:
            Path to the exported file
        """
        if filename:
            filepath = self.output_dir / filename
        else:
            filepath = self._generate_filename("iphone_listings", "csv")
        
        # Define CSV columns
        columns = [
            "id",
            "series",
            "model",
            "storage",
            "color",
            "battery_health",
            "has_warranty",
            "warranty_type",
            "price",
            "currency",
            "seller_name",
            "city",
            "seller_profile",
            "title",
            "url",
            "created_at",
            "days_active",
        ]
        
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()
            
            for listing in listings:
                row = {
                    "id": listing.id,
                    "series": listing.series.value if listing.series else "",
                    "model": listing.model.value if listing.model else "",
                    "storage": listing.storage.value if listing.storage else "",
                    "color": listing.color.value if listing.color else "",
                    "battery_health": (
                        listing.battery_health.percentage 
                        if listing.battery_health else ""
                    ),
                    "has_warranty": (
                        listing.warranty.has_warranty 
                        if listing.warranty else False
                    ),
                    "warranty_type": (
                        listing.warranty.warranty_type 
                        if listing.warranty else ""
                    ),
                    "price": listing.price,
                    "currency": listing.currency,
                    "seller_name": listing.seller.name,
                    "city": listing.seller.city or "",
                    "seller_profile": listing.seller.profile_url or "",
                    "title": listing.title,
                    "url": listing.url or "",
                    "created_at": listing.created_at.isoformat(),
                    "days_active": listing.days_active,
                }
                writer.writerow(row)
        
        return filepath
    
    def to_excel(
        self,
        listings: list[iPhoneListing],
        filename: Optional[str] = None
    ) -> Path:
        """
        Export listings to Excel file.
        
        Requires pandas and openpyxl.
        
        Args:
            listings: List of iPhone listings
            filename: Optional custom filename
            
        Returns:
            Path to the exported file
        """
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("pandas is required for Excel export. Install with: pip install pandas openpyxl")
        
        if filename:
            filepath = self.output_dir / filename
        else:
            filepath = self._generate_filename("iphone_listings", "xlsx")
        
        # Convert to DataFrame
        records = []
        for listing in listings:
            records.append({
                "ID": listing.id,
                "Series": listing.series.value if listing.series else "",
                "Model": listing.model.value if listing.model else "",
                "Storage": listing.storage.value if listing.storage else "",
                "Color": listing.color.value if listing.color else "",
                "Battery Health (%)": (
                    listing.battery_health.percentage 
                    if listing.battery_health else None
                ),
                "Has Warranty": (
                    listing.warranty.has_warranty 
                    if listing.warranty else False
                ),
                "Warranty Type": (
                    listing.warranty.warranty_type 
                    if listing.warranty else ""
                ),
                "Price": listing.price,
                "Currency": listing.currency,
                "Seller Name": listing.seller.name,
                "City": listing.seller.city or "",
                "Seller Profile URL": listing.seller.profile_url or "",
                "Title": listing.title,
                "Listing URL": listing.url or "",
                "Created At": listing.created_at,
                "Days Active": listing.days_active,
            })
        
        df = pd.DataFrame(records)
        df.to_excel(filepath, index=False, engine="openpyxl")
        
        return filepath
    
    def to_dict_list(self, listings: list[iPhoneListing]) -> list[dict]:
        """
        Convert listings to list of dictionaries.
        
        Useful for in-memory processing or API responses.
        """
        return [listing.model_dump(mode="json") for listing in listings]

