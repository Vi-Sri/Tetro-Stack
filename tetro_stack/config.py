"""
Configuration and environment settings for Tetro-Stack.

Authentication Options:
-----------------------
1. META CONTENT LIBRARY API (Research Only)
   - Requires approved researcher access
   - Works within Secure Research Environment (Jupyter)
   - No API keys needed - authentication handled by environment

2. THIRD-PARTY SCRAPER (Commercial)
   - Apify, Bright Data, ScraperAPI
   - Requires API keys from provider

3. BROWSER AUTOMATION
   - Requires Facebook login credentials
   - Session-based authentication
"""

import os
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class ClientType(Enum):
    """Available client types for fetching Marketplace data."""
    META_CONTENT_LIBRARY = "mcl"      # Research only
    APIFY_SCRAPER = "apify"           # Third-party service
    BRIGHT_DATA = "bright_data"       # Third-party service
    PLAYWRIGHT = "playwright"          # Browser automation


class InventoryFilter(Enum):
    """Time-based inventory filters."""
    ONE_DAY = 1
    THREE_DAYS = 3
    FIVE_DAYS = 5
    SEVEN_DAYS = 7
    ALL = None


@dataclass
class MetaContentLibraryConfig:
    """
    Meta Content Library API Configuration.
    
    NOTE: This API is ONLY available to approved researchers.
    Access is granted through Meta's Content Library Access Program.
    
    How to apply:
    1. Visit: https://developers.facebook.com/docs/content-library-and-api/get-access
    2. Submit application with research proposal
    3. Wait for approval (can take weeks)
    4. Access through Secure Research Environment (SRE)
    
    Authentication:
    - No API keys required
    - Authentication handled by the SRE Jupyter environment
    - You login to the SRE portal with your researcher credentials
    """
    # These are set automatically in the Secure Research Environment
    environment: str = "SRE"  # Secure Research Environment
    version: str = "LATEST_VERSION"
    
    # Search defaults for iPhones
    default_query: str = "iPhone"
    default_categories: list = field(default_factory=lambda: ["Electronics", "Cell Phones"])
    default_countries: list = field(default_factory=lambda: ["US"])


@dataclass
class ApifyConfig:
    """
    Apify Facebook Marketplace Scraper Configuration.
    
    How to get API key:
    1. Sign up at: https://apify.com/
    2. Go to Settings > Integrations
    3. Copy your API token
    
    Pricing: Pay-per-result (check current rates on Apify)
    """
    api_token: str = field(default_factory=lambda: os.getenv("APIFY_API_TOKEN", ""))
    actor_id: str = "autoscraping/facebook-marketplace-by-url"
    base_url: str = "https://api.apify.com/v2"
    
    def is_configured(self) -> bool:
        return bool(self.api_token)


@dataclass
class BrightDataConfig:
    """
    Bright Data Web Scraping Configuration.
    
    How to get credentials:
    1. Sign up at: https://brightdata.com/
    2. Create a Web Scraper API zone
    3. Get your customer ID and zone credentials
    """
    customer_id: str = field(default_factory=lambda: os.getenv("BRIGHT_DATA_CUSTOMER_ID", ""))
    zone_password: str = field(default_factory=lambda: os.getenv("BRIGHT_DATA_ZONE_PASSWORD", ""))
    zone_name: str = field(default_factory=lambda: os.getenv("BRIGHT_DATA_ZONE_NAME", "marketplace"))
    
    def is_configured(self) -> bool:
        return bool(self.customer_id and self.zone_password)


@dataclass
class PlaywrightConfig:
    """
    Playwright Browser Automation Configuration.
    
    CAUTION: Using automation with Facebook may violate TOS.
    Use at your own risk.
    
    How to set up:
    1. Set FB_EMAIL and FB_PASSWORD in .env
    2. Run: playwright install chromium
    """
    fb_email: str = field(default_factory=lambda: os.getenv("FB_EMAIL", ""))
    fb_password: str = field(default_factory=lambda: os.getenv("FB_PASSWORD", ""))
    headless: bool = True
    slow_mo: int = 100  # Milliseconds between actions
    
    def is_configured(self) -> bool:
        return bool(self.fb_email and self.fb_password)


@dataclass
class TetroConfig:
    """Main configuration class for Tetro-Stack."""
    
    # Select which client to use
    active_client: ClientType = ClientType.APIFY_SCRAPER
    
    # Client-specific configs
    mcl: MetaContentLibraryConfig = field(default_factory=MetaContentLibraryConfig)
    apify: ApifyConfig = field(default_factory=ApifyConfig)
    bright_data: BrightDataConfig = field(default_factory=BrightDataConfig)
    playwright: PlaywrightConfig = field(default_factory=PlaywrightConfig)
    
    # AI Configuration
    gemini_api_key: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    
    # Search settings
    search_query: str = "iPhone"
    location: str = "United States"
    max_results: int = 100
    
    # Filtering - iPhones are high demand, listings older than 5 days are stale
    inventory_filter: InventoryFilter = InventoryFilter.FIVE_DAYS
    max_listing_age_days: int = 5  # Default max age for listings
    min_price: Optional[int] = None
    max_price: Optional[int] = None
    
    def get_active_config(self):
        """Get the configuration for the active client."""
        mapping = {
            ClientType.META_CONTENT_LIBRARY: self.mcl,
            ClientType.APIFY_SCRAPER: self.apify,
            ClientType.BRIGHT_DATA: self.bright_data,
            ClientType.PLAYWRIGHT: self.playwright,
        }
        return mapping[self.active_client]
    
    def is_client_configured(self) -> bool:
        """Check if the active client is properly configured."""
        config = self.get_active_config()
        if hasattr(config, 'is_configured'):
            return config.is_configured()
        return True  # MCL doesn't need external config


# Global config instance
config = TetroConfig()

