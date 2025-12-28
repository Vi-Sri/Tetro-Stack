"""
Platform definitions for cross-platform marketplace client.

Each platform has its own Apify actor and data mapping.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Platform(str, Enum):
    """Supported marketplace platforms."""
    OLX_INDIA = "olx_india"
    FACEBOOK_MARKETPLACE = "facebook_marketplace"
    # Future platforms
    # OLX_BRAZIL = "olx_brazil"
    # CRAIGSLIST = "craigslist"
    # EBAY = "ebay"


@dataclass
class PlatformConfig:
    """Configuration for a marketplace platform."""
    name: str
    actor_id: str  # Use direct Apify actor ID, not username/name format
    currency: str = "USD"
    country: str = "US"
    
    # Field mappings from platform response to our standard format
    field_mappings: dict = field(default_factory=dict)
    
    # Input configuration
    input_template: dict = field(default_factory=dict)


# Platform configurations
PLATFORM_CONFIGS = {
    Platform.OLX_INDIA: PlatformConfig(
        name="OLX India",
        actor_id="Q7GhqBvTkIMcXdfPc",  # natanielsantos/olx-india-scraper
        currency="INR",
        country="IN",
        field_mappings={
            "id": "id",
            "title": "title",
            "description": "description",
            "url": "url",
            "price": "price.raw",
            "price_display": "price.display",
            "currency": "price.currency.iso_4217",
            "created_at": "createdAt",
            "city": "locationsResolved.ADMIN_LEVEL_3_name",
            "state": "locationsResolved.ADMIN_LEVEL_1_name",
            "seller_id": "userId",
            "images": "images",
            "main_image": "mainImage",
        },
        input_template={
            "startUrls": [],  # Will be populated with search URLs
            "maxItems": 100,
        }
    ),
    
    Platform.FACEBOOK_MARKETPLACE: PlatformConfig(
        name="Facebook Marketplace",
        actor_id="Y0QGH7cuqgKtNbEgt",  # curious_coder/facebook-marketplace (works!)
        currency="INR",
        country="IN",
        field_mappings={
            "id": "id",
            "title": "marketplace_listing_title",
            "price": "listing_price.amount",
            "price_display": "listing_price.formatted_amount",
            "city": "location.reverse_geocode.city",
            "state": "location.reverse_geocode.state",
            "image": "primary_listing_photo.image.uri",
        },
        input_template={
            "urls": [],  # List of Facebook Marketplace search URLs
            "maxItems": 100,
        }
    ),
}


def get_platform_config(platform: Platform) -> PlatformConfig:
    """Get configuration for a platform."""
    return PLATFORM_CONFIGS.get(platform)


def build_olx_india_search_url(query: str, city: Optional[str] = None) -> str:
    """
    Build OLX India search URL.
    
    Args:
        query: Search query (e.g., "iPhone 15")
        city: Optional city name (e.g., "Chennai", "Bangalore", "Coimbatore")
        
    Returns:
        OLX India search URL
    """
    # City configurations for OLX India (verified working formats)
    CITY_CONFIGS = {
        "chennai": {
            "id": "g4059162",
            "format": "mobile-phones_c1453"  # With category
        },
        "bangalore": {
            "id": "g4058803",
            "format": "isSearchCall"  # With isSearchCall param
        },
        "bengaluru": {
            "id": "g4058803",
            "format": "isSearchCall"
        },
        "coimbatore": {
            "id": "g4059164",
            "format": "mobile-phones_c1453"
        },
    }
    
    if city:
        city_key = city.lower().replace(" ", "")
        config = CITY_CONFIGS.get(city_key)
        
        if config:
            city_id = config["id"]
            if config["format"] == "isSearchCall":
                # Format: https://www.olx.in/bengaluru_g4058803/q-iPhone?isSearchCall=true
                return f"https://www.olx.in/{city.lower()}_{city_id}/q-{query}?isSearchCall=true"
            else:
                # Format: https://www.olx.in/chennai_g4059162/mobile-phones_c1453/q-iPhone
                return f"https://www.olx.in/{city.lower()}_{city_id}/{config['format']}/q-{query}"
    
    # Default: All supported cities
    return None  # Will be handled by build_platform_input


def build_olx_india_urls(query: str, cities: Optional[list[str]] = None) -> list[dict]:
    """
    Build OLX India search URLs for multiple cities.
    
    Args:
        query: Search query (e.g., "iPhone")
        cities: List of cities. Defaults to Chennai, Bangalore, Coimbatore
        
    Returns:
        List of URL objects for Apify startUrls
    """
    # Default cities: Chennai, Bangalore, Coimbatore
    target_cities = cities or ["bangalore", "chennai", "coimbatore"]
    
    urls = []
    for city in target_cities:
        url = build_olx_india_search_url(query, city)
        if url:
            urls.append({"url": url, "method": "GET"})
    
    return urls


def build_platform_input(
    platform: Platform,
    query: str,
    location: Optional[str] = None,
    max_items: int = 100,
) -> dict:
    """
    Build input for a platform's scraper.
    
    Args:
        platform: Target platform
        query: Search query
        location: Optional location filter
        max_items: Maximum items to fetch
        
    Returns:
        Input dictionary for the scraper
    """
    config = get_platform_config(platform)
    
    if platform == Platform.OLX_INDIA:
        # If location is specified, use single city; otherwise use all default cities
        if location:
            cities = [location]
        else:
            cities = None  # Will use defaults: Chennai, Bangalore, Coimbatore
        
        urls = build_olx_india_urls(query, cities)
        
        return {
            "startUrls": urls,
            "maxItemsPerUrl": max_items,
            "proxySettings": {
                "useApifyProxy": True
            }
        }
    
    elif platform == Platform.FACEBOOK_MARKETPLACE:
        # Facebook Marketplace scraper using curious_coder/facebook-marketplace
        # Uses same cities as OLX India: Chennai, Bangalore, Coimbatore
        if location:
            cities = [location.lower()]
        else:
            cities = ["chennai", "bangalore", "coimbatore"]
        
        # Build Facebook Marketplace URLs
        urls = [
            f"https://www.facebook.com/marketplace/{city}/search?query={query}"
            for city in cities
        ]
            
        return {
            "urls": urls,
            "maxItems": max_items,
        }
    
    return config.input_template

