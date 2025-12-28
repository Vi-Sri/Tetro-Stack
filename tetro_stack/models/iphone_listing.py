"""
iPhone Listing Data Models.

Structured models for Facebook Marketplace iPhone listings.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, HttpUrl


class iPhoneSeries(str, Enum):
    """iPhone series/generation."""
    IPHONE_16 = "iPhone 16"
    IPHONE_15 = "iPhone 15"
    IPHONE_14 = "iPhone 14"
    IPHONE_13 = "iPhone 13"
    IPHONE_12 = "iPhone 12"
    IPHONE_11 = "iPhone 11"
    IPHONE_XS = "iPhone XS"
    IPHONE_XR = "iPhone XR"
    IPHONE_X = "iPhone X"
    IPHONE_SE = "iPhone SE"
    IPHONE_8 = "iPhone 8"
    IPHONE_7 = "iPhone 7"
    UNKNOWN = "Unknown"


class iPhoneModel(str, Enum):
    """iPhone model variants."""
    # iPhone 16 series
    IPHONE_16_PRO_MAX = "iPhone 16 Pro Max"
    IPHONE_16_PRO = "iPhone 16 Pro"
    IPHONE_16_PLUS = "iPhone 16 Plus"
    IPHONE_16 = "iPhone 16"
    
    # iPhone 15 series
    IPHONE_15_PRO_MAX = "iPhone 15 Pro Max"
    IPHONE_15_PRO = "iPhone 15 Pro"
    IPHONE_15_PLUS = "iPhone 15 Plus"
    IPHONE_15 = "iPhone 15"
    
    # iPhone 14 series
    IPHONE_14_PRO_MAX = "iPhone 14 Pro Max"
    IPHONE_14_PRO = "iPhone 14 Pro"
    IPHONE_14_PLUS = "iPhone 14 Plus"
    IPHONE_14 = "iPhone 14"
    
    # iPhone 13 series
    IPHONE_13_PRO_MAX = "iPhone 13 Pro Max"
    IPHONE_13_PRO = "iPhone 13 Pro"
    IPHONE_13_MINI = "iPhone 13 Mini"
    IPHONE_13 = "iPhone 13"
    
    # iPhone 12 series
    IPHONE_12_PRO_MAX = "iPhone 12 Pro Max"
    IPHONE_12_PRO = "iPhone 12 Pro"
    IPHONE_12_MINI = "iPhone 12 Mini"
    IPHONE_12 = "iPhone 12"
    
    # iPhone 11 series
    IPHONE_11_PRO_MAX = "iPhone 11 Pro Max"
    IPHONE_11_PRO = "iPhone 11 Pro"
    IPHONE_11 = "iPhone 11"
    
    # iPhone X series
    IPHONE_XS_MAX = "iPhone XS Max"
    IPHONE_XS = "iPhone XS"
    IPHONE_XR = "iPhone XR"
    IPHONE_X = "iPhone X"
    
    # iPhone SE
    IPHONE_SE_3RD = "iPhone SE (3rd gen)"
    IPHONE_SE_2ND = "iPhone SE (2nd gen)"
    IPHONE_SE_1ST = "iPhone SE (1st gen)"
    
    # Older models
    IPHONE_8_PLUS = "iPhone 8 Plus"
    IPHONE_8 = "iPhone 8"
    IPHONE_7_PLUS = "iPhone 7 Plus"
    IPHONE_7 = "iPhone 7"
    
    UNKNOWN = "Unknown"


class StorageCapacity(str, Enum):
    """iPhone storage capacity options."""
    GB_32 = "32GB"
    GB_64 = "64GB"
    GB_128 = "128GB"
    GB_256 = "256GB"
    GB_512 = "512GB"
    TB_1 = "1TB"
    TB_2 = "2TB"
    UNKNOWN = "Unknown"


class iPhoneColor(str, Enum):
    """iPhone color options."""
    # Standard colors
    BLACK = "Black"
    WHITE = "White"
    SILVER = "Silver"
    GOLD = "Gold"
    SPACE_GRAY = "Space Gray"
    SPACE_BLACK = "Space Black"
    
    # Pro colors
    GRAPHITE = "Graphite"
    DEEP_PURPLE = "Deep Purple"
    NATURAL_TITANIUM = "Natural Titanium"
    BLUE_TITANIUM = "Blue Titanium"
    WHITE_TITANIUM = "White Titanium"
    BLACK_TITANIUM = "Black Titanium"
    DESERT_TITANIUM = "Desert Titanium"
    
    # Special colors
    MIDNIGHT = "Midnight"
    STARLIGHT = "Starlight"
    BLUE = "Blue"
    GREEN = "Green"
    PINK = "Pink"
    PURPLE = "Purple"
    YELLOW = "Yellow"
    RED = "Red"
    CORAL = "Coral"
    
    UNKNOWN = "Unknown"


class SellerInfo(BaseModel):
    """Seller information from Marketplace listing."""
    name: str = Field(..., description="Seller's display name")
    profile_url: Optional[str] = Field(None, description="URL to seller's Facebook profile")
    city: Optional[str] = Field(None, description="Seller's city/location")
    member_since: Optional[datetime] = Field(None, description="When seller joined Facebook")
    rating: Optional[float] = Field(None, ge=0, le=5, description="Seller rating (0-5)")
    total_listings: Optional[int] = Field(None, description="Total active listings from seller")


class BatteryHealth(BaseModel):
    """iPhone battery health information."""
    percentage: Optional[int] = Field(None, ge=0, le=100, description="Battery health percentage")
    raw_text: Optional[str] = Field(None, description="Raw battery health text from listing")
    is_verified: bool = Field(False, description="Whether battery health is verified")


class WarrantyInfo(BaseModel):
    """Warranty information for the iPhone."""
    has_warranty: bool = Field(False, description="Whether device has warranty")
    warranty_type: Optional[str] = Field(None, description="Type of warranty (AppleCare+, carrier, etc.)")
    expires: Optional[datetime] = Field(None, description="Warranty expiration date")
    raw_text: Optional[str] = Field(None, description="Raw warranty text from listing")


class iPhoneListing(BaseModel):
    """
    Complete iPhone listing from Facebook Marketplace.
    
    This model captures all relevant data points for an iPhone listing
    including device specs, seller info, pricing, and metadata.
    """
    # Listing identifiers
    id: str = Field(..., description="Unique listing ID from Marketplace")
    url: Optional[str] = Field(None, description="Direct URL to the listing")
    
    # iPhone specifications
    series: iPhoneSeries = Field(iPhoneSeries.UNKNOWN, description="iPhone series/generation")
    model: iPhoneModel = Field(iPhoneModel.UNKNOWN, description="Specific iPhone model")
    storage: StorageCapacity = Field(StorageCapacity.UNKNOWN, description="Storage capacity")
    color: iPhoneColor = Field(iPhoneColor.UNKNOWN, description="Device color")
    
    # Condition
    battery_health: Optional[BatteryHealth] = Field(None, description="Battery health info")
    condition: Optional[str] = Field(None, description="Overall condition description")
    
    # Warranty
    warranty: Optional[WarrantyInfo] = Field(None, description="Warranty information")
    
    # Pricing
    price: float = Field(..., description="Listed price in local currency")
    currency: str = Field("USD", description="Price currency")
    original_price: Optional[float] = Field(None, description="Original retail price if mentioned")
    is_negotiable: bool = Field(False, description="Whether price is negotiable")
    
    # Seller information
    seller: SellerInfo = Field(..., description="Seller details")
    
    # Listing metadata
    title: str = Field(..., description="Listing title")
    description: Optional[str] = Field(None, description="Full listing description")
    images: list[str] = Field(default_factory=list, description="Image URLs")
    
    # Timestamps (all stored as naive UTC for consistency)
    created_at: datetime = Field(..., description="When listing was created")
    updated_at: Optional[datetime] = Field(None, description="Last update time")
    fetched_at: datetime = Field(default_factory=datetime.utcnow, description="When we fetched this listing")
    
    @staticmethod
    def normalize_datetime(dt: datetime) -> datetime:
        """Convert timezone-aware datetime to naive UTC."""
        if dt.tzinfo is not None:
            return dt.replace(tzinfo=None)
        return dt
    
    # Source tracking
    source: str = Field("facebook_marketplace", description="Data source")
    raw_data: Optional[dict] = Field(None, description="Original raw data from source")
    
    @property
    def days_active(self) -> int:
        """Calculate days since listing was created."""
        now = datetime.utcnow()
        created = self.created_at
        
        # Handle timezone-aware vs naive datetime comparison
        if created.tzinfo is not None:
            # Make created_at naive by removing timezone info
            created = created.replace(tzinfo=None)
        
        delta = now - created
        return max(0, delta.days)
    
    @property
    def is_recent(self) -> bool:
        """Check if listing is less than 24 hours old."""
        return self.days_active == 0
    
    def matches_filter(self, days: int) -> bool:
        """Check if listing matches the active inventory filter."""
        return self.days_active <= days
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }

