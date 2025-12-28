"""
Inventory Filtering Engine.

Provides time-based and specification-based filtering for iPhone listings.
"""

from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass

from ..models.iphone_listing import (
    iPhoneListing,
    iPhoneSeries,
    iPhoneModel,
    StorageCapacity,
    iPhoneColor,
)
from ..config import InventoryFilter


@dataclass
class FilterCriteria:
    """Filter criteria for iPhone listings."""
    # Time filters
    days_active: Optional[int] = None  # 1, 3, 5, 7 days
    
    # Model filters
    series: Optional[list[iPhoneSeries]] = None
    models: Optional[list[iPhoneModel]] = None
    
    # Specs filters
    min_storage: Optional[StorageCapacity] = None
    colors: Optional[list[iPhoneColor]] = None
    
    # Battery filter
    min_battery_health: Optional[int] = None
    
    # Price filters
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    
    # Location filter
    cities: Optional[list[str]] = None
    
    # Warranty filter
    has_warranty: Optional[bool] = None


class InventoryFilterEngine:
    """
    Engine for filtering iPhone listings based on various criteria.
    
    Supports:
    - Time-based filtering (1, 3, 5, 7 days)
    - Model/series filtering
    - Storage capacity filtering
    - Price range filtering
    - Battery health filtering
    - Location filtering
    """
    
    # Storage ordering for comparison
    STORAGE_ORDER = [
        StorageCapacity.GB_32,
        StorageCapacity.GB_64,
        StorageCapacity.GB_128,
        StorageCapacity.GB_256,
        StorageCapacity.GB_512,
        StorageCapacity.TB_1,
        StorageCapacity.TB_2,
    ]
    
    def __init__(self):
        self._storage_rank = {s: i for i, s in enumerate(self.STORAGE_ORDER)}
    
    def filter_by_days(
        self, 
        listings: list[iPhoneListing], 
        days: int
    ) -> list[iPhoneListing]:
        """
        Filter listings by active days.
        
        Args:
            listings: List of listings to filter
            days: Maximum days since listing was created
            
        Returns:
            Filtered list of listings
        """
        return [l for l in listings if l.days_active <= days]
    
    def filter_by_inventory_enum(
        self,
        listings: list[iPhoneListing],
        filter_type: InventoryFilter
    ) -> list[iPhoneListing]:
        """
        Filter using InventoryFilter enum.
        
        Args:
            listings: List of listings
            filter_type: InventoryFilter enum value
            
        Returns:
            Filtered listings
        """
        if filter_type == InventoryFilter.ALL or filter_type.value is None:
            return listings
        return self.filter_by_days(listings, filter_type.value)
    
    def filter_by_series(
        self,
        listings: list[iPhoneListing],
        series: list[iPhoneSeries]
    ) -> list[iPhoneListing]:
        """Filter listings by iPhone series."""
        return [l for l in listings if l.series in series]
    
    def filter_by_models(
        self,
        listings: list[iPhoneListing],
        models: list[iPhoneModel]
    ) -> list[iPhoneListing]:
        """Filter listings by specific iPhone models."""
        return [l for l in listings if l.model in models]
    
    def filter_by_storage(
        self,
        listings: list[iPhoneListing],
        min_storage: StorageCapacity
    ) -> list[iPhoneListing]:
        """Filter listings by minimum storage capacity."""
        min_rank = self._storage_rank.get(min_storage, 0)
        return [
            l for l in listings
            if self._storage_rank.get(l.storage, -1) >= min_rank
        ]
    
    def filter_by_price(
        self,
        listings: list[iPhoneListing],
        min_price: Optional[float] = None,
        max_price: Optional[float] = None
    ) -> list[iPhoneListing]:
        """Filter listings by price range."""
        filtered = listings
        if min_price is not None:
            filtered = [l for l in filtered if l.price >= min_price]
        if max_price is not None:
            filtered = [l for l in filtered if l.price <= max_price]
        return filtered
    
    def filter_by_battery(
        self,
        listings: list[iPhoneListing],
        min_health: int
    ) -> list[iPhoneListing]:
        """Filter listings by minimum battery health percentage."""
        return [
            l for l in listings
            if l.battery_health and l.battery_health.percentage
            and l.battery_health.percentage >= min_health
        ]
    
    def filter_by_cities(
        self,
        listings: list[iPhoneListing],
        cities: list[str]
    ) -> list[iPhoneListing]:
        """Filter listings by seller cities."""
        cities_lower = [c.lower() for c in cities]
        return [
            l for l in listings
            if l.seller.city and l.seller.city.lower() in cities_lower
        ]
    
    def filter_by_warranty(
        self,
        listings: list[iPhoneListing],
        has_warranty: bool = True
    ) -> list[iPhoneListing]:
        """Filter listings by warranty availability."""
        if has_warranty:
            return [
                l for l in listings
                if l.warranty and l.warranty.has_warranty
            ]
        else:
            return [
                l for l in listings
                if not l.warranty or not l.warranty.has_warranty
            ]
    
    def apply_criteria(
        self,
        listings: list[iPhoneListing],
        criteria: FilterCriteria
    ) -> list[iPhoneListing]:
        """
        Apply all filter criteria to listings.
        
        Args:
            listings: List of listings to filter
            criteria: FilterCriteria object with all filters
            
        Returns:
            Filtered list of listings
        """
        filtered = listings
        
        # Time filter
        if criteria.days_active is not None:
            filtered = self.filter_by_days(filtered, criteria.days_active)
        
        # Series filter
        if criteria.series:
            filtered = self.filter_by_series(filtered, criteria.series)
        
        # Model filter
        if criteria.models:
            filtered = self.filter_by_models(filtered, criteria.models)
        
        # Storage filter
        if criteria.min_storage:
            filtered = self.filter_by_storage(filtered, criteria.min_storage)
        
        # Price filter
        if criteria.min_price is not None or criteria.max_price is not None:
            filtered = self.filter_by_price(
                filtered, 
                criteria.min_price, 
                criteria.max_price
            )
        
        # Battery filter
        if criteria.min_battery_health is not None:
            filtered = self.filter_by_battery(filtered, criteria.min_battery_health)
        
        # City filter
        if criteria.cities:
            filtered = self.filter_by_cities(filtered, criteria.cities)
        
        # Warranty filter
        if criteria.has_warranty is not None:
            filtered = self.filter_by_warranty(filtered, criteria.has_warranty)
        
        return filtered
    
    def get_inventory_summary(
        self,
        listings: list[iPhoneListing]
    ) -> dict:
        """
        Generate inventory summary by time periods.
        
        Returns counts for 1-day, 3-day, 5-day, 7-day periods.
        """
        return {
            "1_day": len(self.filter_by_days(listings, 1)),
            "3_day": len(self.filter_by_days(listings, 3)),
            "5_day": len(self.filter_by_days(listings, 5)),
            "7_day": len(self.filter_by_days(listings, 7)),
            "total": len(listings),
        }

