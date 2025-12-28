"""
Meta Content Library API Client.

⚠️  IMPORTANT: This client ONLY works within Meta's Secure Research Environment (SRE).
    You cannot use this locally - it requires approved researcher access.

How to get access:
1. Apply at: https://developers.facebook.com/docs/content-library-and-api/get-access
2. Submit research proposal
3. Wait for approval (typically several weeks)
4. Access via SRE Jupyter environment

The metacontentlibraryapi package is pre-installed in the SRE.
"""

from datetime import datetime, timedelta
from typing import Optional
import logging

from .base_client import BaseMarketplaceClient
from ..models.iphone_listing import (
    iPhoneListing, 
    SellerInfo,
    BatteryHealth,
    WarrantyInfo,
)
from ..config import MetaContentLibraryConfig

logger = logging.getLogger(__name__)


# Type hint for the MCL client (not available locally)
try:
    from metacontentlibraryapi import MetaContentLibraryAPIClient as MCLClient
    MCL_AVAILABLE = True
except ImportError:
    MCLClient = None
    MCL_AVAILABLE = False


class MetaContentLibraryClient(BaseMarketplaceClient):
    """
    Client for Meta Content Library API.
    
    This client interfaces with Facebook Marketplace through Meta's
    official Content Library API, designed for academic research.
    
    Authentication:
    - NO API keys required
    - Authentication is handled by the Secure Research Environment
    - You login to SRE with your approved researcher credentials
    
    Usage (in SRE Jupyter notebook):
    ```python
    from metacontentlibraryapi import MetaContentLibraryAPIClient as client
    
    client.set_default_version(client.LATEST_VERSION)
    
    response = client.get(
        path="facebook/marketplace-listings/preview",
        params={
            "q": "iPhone",
            "categories": ["Electronics", "Cell Phones"],
            "listing_countries": ["US"],
            "since": "2024-01-01",
            "fields": "id,listing_details,seller,location,price"
        }
    )
    ```
    """
    
    def __init__(self, config: Optional[MetaContentLibraryConfig] = None):
        """
        Initialize the MCL client.
        
        Args:
            config: MCL configuration (uses defaults if not provided)
        """
        self.config = config or MetaContentLibraryConfig()
        self._client = None
        
        if MCL_AVAILABLE:
            self._client = MCLClient
            self._client.set_default_version(self._client.LATEST_VERSION)
            logger.info("Meta Content Library client initialized")
        else:
            logger.warning(
                "metacontentlibraryapi not available. "
                "This client only works in Meta's Secure Research Environment."
            )
    
    def is_authenticated(self) -> bool:
        """
        Check if running in authenticated SRE environment.
        
        In the SRE, authentication is automatic via the environment.
        """
        return MCL_AVAILABLE and self._client is not None
    
    async def fetch_listings(
        self,
        query: str = "iPhone",
        location: str = "US",
        max_results: int = 100,
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
        days_filter: Optional[int] = None,
    ) -> list[iPhoneListing]:
        """
        Fetch iPhone listings from Facebook Marketplace via MCL API.
        
        Args:
            query: Search keywords (default: "iPhone")
            location: ISO country code (default: "US")
            max_results: Maximum listings to return
            min_price: Minimum price filter
            max_price: Maximum price filter  
            days_filter: Only listings from last N days
            
        Returns:
            List of iPhoneListing objects
        """
        if not self.is_authenticated():
            raise RuntimeError(
                "Meta Content Library API not available. "
                "This client only works in Meta's Secure Research Environment. "
                "Apply for access at: https://developers.facebook.com/docs/content-library-and-api/get-access"
            )
        
        # Build query parameters
        params = {
            "q": query,
            "categories": self.config.default_categories,
            "listing_countries": [location],
            "fields": ",".join([
                "id",
                "listing_details",
                "description", 
                "price",
                "creation_time",
                "update_time",
                "seller",
                "location",
                "multimedia{url}",
            ]),
            "sort": "newest_to_oldest",
        }
        
        # Add date filter
        if days_filter:
            since_date = datetime.utcnow() - timedelta(days=days_filter)
            params["since"] = since_date.strftime("%Y-%m-%d")
        
        # Add price filters (only valid for single country)
        if min_price is not None:
            params["price_min"] = str(min_price)
        if max_price is not None:
            params["price_max"] = str(max_price)
        
        # Make API request
        response = self._client.get(
            path="facebook/marketplace-listings/preview",
            params=params,
        )
        
        # Parse response
        data = response.json()
        listings = []
        
        for item in data.get("data", [])[:max_results]:
            listing = self._parse_listing(item)
            if listing:
                listings.append(listing)
        
        return listings
    
    async def fetch_listing_details(self, listing_id: str) -> Optional[iPhoneListing]:
        """Fetch details for a specific listing."""
        if not self.is_authenticated():
            return None
            
        response = self._client.get(
            path=f"facebook/marketplace-listings/{listing_id}",
            params={"fields": "id,listing_details,description,price,seller,location,multimedia{url}"}
        )
        
        data = response.json()
        return self._parse_listing(data) if data else None
    
    def _parse_listing(self, data: dict) -> Optional[iPhoneListing]:
        """
        Parse raw MCL API response into iPhoneListing model.
        
        Args:
            data: Raw listing data from API
            
        Returns:
            Parsed iPhoneListing or None if parsing fails
        """
        try:
            listing_details = data.get("listing_details", {})
            seller_data = data.get("seller", {})
            location_data = data.get("location", {})
            
            # Build seller info
            seller = SellerInfo(
                name=seller_data.get("name", "Unknown"),
                profile_url=seller_data.get("profile_url"),
                city=location_data.get("city"),
            )
            
            # Parse price
            price_data = data.get("price", {})
            price = float(price_data.get("amount", 0))
            currency = price_data.get("currency", "USD")
            
            # Parse timestamps
            created_at = datetime.fromisoformat(
                data.get("creation_time", datetime.utcnow().isoformat())
            )
            
            # Extract images
            multimedia = data.get("multimedia", [])
            images = [m.get("url") for m in multimedia if m.get("url")]
            
            return iPhoneListing(
                id=str(data.get("id")),
                url=data.get("url"),
                title=listing_details.get("title", ""),
                description=data.get("description", ""),
                price=price,
                currency=currency,
                seller=seller,
                images=images,
                created_at=created_at,
                raw_data=data,
            )
            
        except Exception as e:
            logger.error(f"Failed to parse listing: {e}")
            return None


# Convenience function for SRE Jupyter notebooks
def create_mcl_query(
    query: str = "iPhone",
    categories: Optional[list[str]] = None,
    countries: Optional[list[str]] = None,
    days: int = 7,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
) -> dict:
    """
    Create a query dict for MCL API.
    
    Use this in SRE Jupyter:
    ```python
    from metacontentlibraryapi import MetaContentLibraryAPIClient as client
    from tetro_stack.clients.mcl_client import create_mcl_query
    
    params = create_mcl_query(query="iPhone 15", days=3, max_price=800)
    response = client.get(path="facebook/marketplace-listings/preview", params=params)
    ```
    """
    params = {
        "q": query,
        "categories": categories or ["Electronics", "Cell Phones"],
        "listing_countries": countries or ["US"],
        "since": (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d"),
        "fields": "id,listing_details,description,price,creation_time,seller,location,multimedia{url}",
        "sort": "newest_to_oldest",
    }
    
    if min_price:
        params["price_min"] = str(min_price)
    if max_price:
        params["price_max"] = str(max_price)
    
    return params

