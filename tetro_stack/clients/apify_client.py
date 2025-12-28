"""
Cross-Platform Apify Marketplace Client.

Supports multiple marketplace platforms through Apify scrapers:
- OLX India
- Facebook Marketplace
- More to come...

Setup:
1. Sign up at https://apify.com/
2. Get your API token from Settings > Integrations
3. Set APIFY_API_TOKEN in your .env file
"""

import httpx
import logging
from datetime import datetime, timedelta
from typing import Optional

from .base_client import BaseMarketplaceClient
from .platforms import (
    Platform,
    PlatformConfig,
    get_platform_config,
    build_platform_input,
)
from ..models.iphone_listing import (
    iPhoneListing,
    SellerInfo,
    BatteryHealth,
    WarrantyInfo,
    iPhoneSeries,
    iPhoneModel,
    StorageCapacity,
    iPhoneColor,
)
from ..config import ApifyConfig
from ..parsers.iphone_parser import iPhoneParser

logger = logging.getLogger(__name__)


class ApifyMarketplaceClient(BaseMarketplaceClient):
    """
    Cross-platform client for marketplace scrapers via Apify.
    
    Supports multiple platforms through different Apify actors.
    Each platform has its own data mapping and input format.
    
    Authentication:
    - Requires Apify API token
    - Set via APIFY_API_TOKEN environment variable
    - Get token from: https://console.apify.com/account/integrations
    
    Usage:
        ```python
        from tetro_stack.clients import ApifyMarketplaceClient
        from tetro_stack.clients.platforms import Platform
        
        async with ApifyMarketplaceClient() as client:
            # Fetch from OLX India
            listings = await client.fetch_listings(
                platform=Platform.OLX_INDIA,
                query="iPhone 15",
                location="Mumbai",
                max_results=50,
            )
        ```
    """
    
    BASE_URL = "https://api.apify.com/v2"
    
    def __init__(
        self, 
        config: Optional[ApifyConfig] = None,
        platform: Platform = Platform.OLX_INDIA,
    ):
        """
        Initialize the Apify client.
        
        Args:
            config: Apify configuration (uses defaults if not provided)
            platform: Default platform to use
        """
        self.config = config or ApifyConfig()
        self.platform = platform
        self.parser = iPhoneParser()
        self._http_client = httpx.AsyncClient(timeout=180.0)
    
    def is_authenticated(self) -> bool:
        """Check if Apify API token is configured."""
        return self.config.is_configured()
    
    @property
    def _headers(self) -> dict:
        """Get authorization headers."""
        return {"Authorization": f"Bearer {self.config.api_token}"}
    
    async def validate_token(self) -> dict:
        """
        Validate the API token and get user info.
        
        Returns:
            User information if valid, raises exception otherwise
        """
        response = await self._http_client.get(
            f"{self.BASE_URL}/users/me",
            headers=self._headers,
        )
        response.raise_for_status()
        return response.json().get("data", {})
    
    async def fetch_listings(
        self,
        query: str = "iPhone",
        location: Optional[str] = None,
        max_results: int = 100,
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
        days_filter: Optional[int] = None,
        platform: Optional[Platform] = None,
    ) -> list[iPhoneListing]:
        """
        Fetch iPhone listings from the specified marketplace platform.
        
        Args:
            query: Search keywords (e.g., "iPhone 15 Pro Max")
            location: Location filter (city name for OLX, location string for FB)
            max_results: Maximum listings to fetch
            min_price: Minimum price filter (post-fetch filtering)
            max_price: Maximum price filter (post-fetch filtering)
            days_filter: Only listings from last N days (post-fetch filtering)
            platform: Platform to fetch from (defaults to self.platform)
            
        Returns:
            List of iPhoneListing objects
        """
        if not self.is_authenticated():
            raise ValueError(
                "Apify API token not configured. "
                "Set APIFY_API_TOKEN in your .env file. "
                "Get your token from: https://console.apify.com/account/integrations"
            )
        
        target_platform = platform or self.platform
        platform_config = get_platform_config(target_platform)
        
        if not platform_config:
            raise ValueError(f"Unsupported platform: {target_platform}")
        
        logger.info(f"Fetching from {platform_config.name}...")
        
        # Build platform-specific input
        scraper_input = build_platform_input(
            platform=target_platform,
            query=query,
            location=location,
            max_items=max_results,
        )
        
        # Start the actor run
        run_url = f"{self.BASE_URL}/acts/{platform_config.actor_id}/runs"
        
        response = await self._http_client.post(
            run_url,
            json=scraper_input,
            headers=self._headers,
            params={"waitForFinish": 180}  # Wait up to 3 minutes
        )
        
        if response.status_code != 201:
            logger.error(f"Failed to start actor: {response.text}")
            raise RuntimeError(f"Actor start failed: {response.text}")
        
        run_data = response.json()
        run_status = run_data.get("data", {}).get("status")
        dataset_id = run_data.get("data", {}).get("defaultDatasetId")
        
        logger.info(f"Run status: {run_status}, Dataset: {dataset_id}")
        
        if not dataset_id:
            logger.error("No dataset ID in response")
            return []
        
        # Fetch results from dataset
        items = await self._fetch_dataset_items(dataset_id)
        
        # Parse into iPhoneListing objects
        listings = []
        for item in items:
            listing = self._parse_item(item, target_platform)
            if listing:
                # Apply post-fetch filters
                if min_price and listing.price < min_price:
                    continue
                if max_price and listing.price > max_price:
                    continue
                if days_filter and listing.days_active > days_filter:
                    continue
                
                listings.append(listing)
        
        logger.info(f"Fetched and parsed {len(listings)} listings")
        return listings
    
    async def _fetch_dataset_items(self, dataset_id: str) -> list[dict]:
        """Fetch all items from an Apify dataset."""
        dataset_url = f"{self.BASE_URL}/datasets/{dataset_id}/items"
        
        response = await self._http_client.get(
            dataset_url,
            headers=self._headers,
            params={"format": "json"}
        )
        response.raise_for_status()
        
        return response.json()
    
    async def get_last_run_data(
        self, 
        platform: Optional[Platform] = None
    ) -> list[iPhoneListing]:
        """
        Get data from the last run without starting a new one.
        
        Useful for accessing previously scraped data.
        """
        target_platform = platform or self.platform
        platform_config = get_platform_config(target_platform)
        
        # Get the last run
        response = await self._http_client.get(
            f"{self.BASE_URL}/acts/{platform_config.actor_id}/runs",
            headers=self._headers,
            params={"limit": 1}
        )
        response.raise_for_status()
        
        runs = response.json().get("data", {}).get("items", [])
        if not runs:
            return []
        
        dataset_id = runs[0].get("defaultDatasetId")
        if not dataset_id:
            return []
        
        items = await self._fetch_dataset_items(dataset_id)
        
        return [
            listing for item in items 
            if (listing := self._parse_item(item, target_platform))
        ]
    
    async def fetch_listing_details(self, listing_id: str) -> Optional[iPhoneListing]:
        """
        Fetch details for a specific listing.
        
        Note: Most Apify scrapers don't support individual listing lookups.
        """
        logger.warning("Individual listing lookup not directly supported by Apify scrapers")
        return None
    
    def _parse_item(
        self, 
        item: dict, 
        platform: Platform
    ) -> Optional[iPhoneListing]:
        """
        Parse a raw item from Apify into iPhoneListing.
        
        Args:
            item: Raw item from dataset
            platform: Platform the item came from
            
        Returns:
            Parsed iPhoneListing or None
        """
        if platform == Platform.OLX_INDIA:
            return self._parse_olx_india_item(item)
        elif platform == Platform.FACEBOOK_MARKETPLACE:
            return self._parse_facebook_item(item)
        
        return None
    
    def _parse_olx_india_item(self, item: dict) -> Optional[iPhoneListing]:
        """Parse OLX India item into iPhoneListing."""
        try:
            title = item.get("title", "")
            description = item.get("description", "")
            
            # Use parser to extract iPhone specs
            parsed = self.parser.parse_listing(title, description)
            
            # Extract location
            locations = item.get("locationsResolved", {})
            city = locations.get("ADMIN_LEVEL_3_name", "")
            state = locations.get("ADMIN_LEVEL_1_name", "")
            
            # Build seller info
            seller = SellerInfo(
                name=f"Seller #{item.get('userId', 'Unknown')}",
                profile_url=None,  # OLX doesn't expose profile URLs in API
                city=f"{city}, {state}" if state else city,
            )
            
            # Parse price
            price_data = item.get("price", {})
            if isinstance(price_data, dict):
                price = float(price_data.get("raw", 0))
                currency = price_data.get("currency", {}).get("iso_4217", "INR")
            else:
                price = float(price_data) if price_data else 0
                currency = "INR"
            
            # Parse date
            created_str = item.get("createdAt", item.get("createdAtFirst"))
            if created_str:
                try:
                    # Handle timezone offset format
                    if "+" in created_str:
                        created_at = datetime.fromisoformat(created_str)
                    else:
                        created_at = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                except Exception:
                    created_at = datetime.utcnow()
            else:
                created_at = datetime.utcnow()
            
            # Get images
            images = item.get("images", [])
            image_urls = []
            if images:
                for img in images:
                    if isinstance(img, dict):
                        # Get the full size image URL
                        full_img = img.get("full", {})
                        url = full_img.get("url") or img.get("url", "")
                        if url:
                            image_urls.append(url)
                    elif isinstance(img, str):
                        image_urls.append(img)
            
            return iPhoneListing(
                id=str(item.get("id", "")),
                url=item.get("url"),
                title=title,
                description=description,
                series=parsed.get("series", iPhoneSeries.UNKNOWN),
                model=parsed.get("model", iPhoneModel.UNKNOWN),
                storage=parsed.get("storage", StorageCapacity.UNKNOWN),
                color=parsed.get("color", iPhoneColor.UNKNOWN),
                battery_health=parsed.get("battery_health"),
                warranty=parsed.get("warranty"),
                price=price,
                currency=currency,
                seller=seller,
                images=image_urls,
                created_at=created_at,
                source="olx_india",
                raw_data=item,
            )
            
        except Exception as e:
            logger.error(f"Failed to parse OLX India item: {e}")
            return None
    
    def _parse_facebook_item(self, item: dict) -> Optional[iPhoneListing]:
        """Parse Facebook Marketplace item into iPhoneListing (curious_coder format)."""
        try:
            # Extract title from marketplace_listing_title or custom_title
            title = item.get("marketplace_listing_title", "")
            if not title:
                title = item.get("custom_title", "")
            if not title:
                # Try to extract from redacted title
                title = item.get("redacted_custom_title", "Unknown iPhone")
            
            description = item.get("description", "") or ""
            
            # Use parser to extract iPhone specs from title
            parsed = self.parser.parse_listing(title, description)
            
            # Extract location
            location_data = item.get("location", {})
            reverse_geocode = location_data.get("reverse_geocode", {})
            city = reverse_geocode.get("city", "")
            state = reverse_geocode.get("state", "")
            
            seller = SellerInfo(
                name="Facebook Seller",  # FB doesn't expose seller name in search results
                profile_url=None,
                city=f"{city}, {state}" if state else city,
            )
            
            # Parse price from listing_price object
            price_data = item.get("listing_price", {})
            if isinstance(price_data, dict):
                price_str = price_data.get("amount", "0")
                try:
                    price = float(price_str)
                except (ValueError, TypeError):
                    price = 0.0
                currency = "INR"  # Facebook India uses INR
            else:
                price = 0.0
                currency = "INR"
            
            # Facebook doesn't provide creation date in search results, use current
            created_at = datetime.utcnow()
            
            # Get primary image
            images = []
            primary_photo = item.get("primary_listing_photo", {})
            if primary_photo:
                image_data = primary_photo.get("image", {})
                if image_data and image_data.get("uri"):
                    images.append(image_data.get("uri"))
            
            # Build listing URL
            listing_id = item.get("id", "")
            url = f"https://www.facebook.com/marketplace/item/{listing_id}" if listing_id else None
            
            return iPhoneListing(
                id=str(listing_id),
                url=url,
                title=title,
                description=description,
                series=parsed.get("series", iPhoneSeries.UNKNOWN),
                model=parsed.get("model", iPhoneModel.UNKNOWN),
                storage=parsed.get("storage", StorageCapacity.UNKNOWN),
                color=parsed.get("color", iPhoneColor.UNKNOWN),
                battery_health=parsed.get("battery_health"),
                warranty=parsed.get("warranty"),
                price=price,
                currency=currency,
                seller=seller,
                images=images,
                created_at=created_at,
                source="facebook_marketplace",
                raw_data=item,
            )
            
        except Exception as e:
            logger.error(f"Failed to parse Facebook item: {e}")
            return None
    
    async def close(self):
        """Close the HTTP client."""
        await self._http_client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
