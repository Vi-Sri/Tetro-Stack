"""
Base client interface for Marketplace data fetching.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Optional

from ..models.iphone_listing import iPhoneListing
from ..config import InventoryFilter


class BaseMarketplaceClient(ABC):
    """
    Abstract base class for Marketplace data clients.
    
    All client implementations (MCL, Apify, Playwright) must implement this interface.
    """
    
    @abstractmethod
    async def fetch_listings(
        self,
        query: str = "iPhone",
        location: str = "United States",
        max_results: int = 100,
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
        days_filter: Optional[int] = None,
    ) -> list[iPhoneListing]:
        """
        Fetch iPhone listings from Marketplace.
        
        Args:
            query: Search query (default: "iPhone")
            location: Geographic location filter
            max_results: Maximum number of listings to fetch
            min_price: Minimum price filter
            max_price: Maximum price filter
            days_filter: Only return listings from last N days
            
        Returns:
            List of iPhoneListing objects
        """
        pass
    
    @abstractmethod
    async def fetch_listing_details(self, listing_id: str) -> Optional[iPhoneListing]:
        """
        Fetch detailed information for a specific listing.
        
        Args:
            listing_id: The Marketplace listing ID
            
        Returns:
            iPhoneListing object or None if not found
        """
        pass
    
    @abstractmethod
    def is_authenticated(self) -> bool:
        """Check if the client is properly authenticated."""
        pass
    
    def get_date_filter(self, filter_type: InventoryFilter) -> Optional[datetime]:
        """
        Convert inventory filter to a datetime threshold.
        
        Args:
            filter_type: The inventory filter enum value
            
        Returns:
            Datetime threshold or None for no filter
        """
        if filter_type == InventoryFilter.ALL or filter_type.value is None:
            return None
        
        return datetime.utcnow() - timedelta(days=filter_type.value)
    
    def filter_by_days(
        self, 
        listings: list[iPhoneListing], 
        days: int
    ) -> list[iPhoneListing]:
        """
        Filter listings to only include those from the last N days.
        
        Args:
            listings: List of listings to filter
            days: Number of days threshold
            
        Returns:
            Filtered list of listings
        """
        return [l for l in listings if l.matches_filter(days)]

