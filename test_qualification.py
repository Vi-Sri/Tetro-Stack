#!/usr/bin/env python3
"""
Test the qualification and filtering logic using cached data.
"""
import os
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path

# Set environment
os.environ.setdefault("APIFY_API_TOKEN", "test")
os.environ.setdefault("GEMINI_API_KEY", "test")

from tetro_stack.models.iphone_listing import (
    iPhoneListing, iPhoneSeries, iPhoneModel, StorageCapacity, 
    iPhoneColor, SellerInfo, BatteryHealth, WarrantyInfo
)
from tetro_stack.filters.inventory_filter import InventoryFilterEngine, FilterCriteria
from nightly_job import ListingQualifier, DealQuality, SellerRating

# Create sample listings that simulate real scraped data
SAMPLE_LISTINGS = [
    # HOT DEAL - Great price, good battery
    {
        "id": "1001",
        "title": "iPhone 14 Pro Max 256GB - Excellent Condition",
        "model": iPhoneModel.IPHONE_14_PRO_MAX,
        "series": iPhoneSeries.IPHONE_14,
        "storage": StorageCapacity.GB_256,
        "color": iPhoneColor.DEEP_PURPLE,
        "price": 62000,  # Market is 85000, this is 27% below
        "battery_health": BatteryHealth(percentage=96),
        "warranty": WarrantyInfo(has_warranty=True, warranty_type="AppleCare+"),
        "seller": SellerInfo(name="Raj Kumar", city="Chennai", profile_url="https://olx.in/user/raj", rating=4.8, total_listings=15),
        "created_at": datetime.utcnow() - timedelta(hours=6),  # Today
        "url": "https://olx.in/item/iphone-14-pro-max-1001"
    },
    # GOOD DEAL - Fair price, decent battery
    {
        "id": "1002", 
        "title": "iPhone 13 128GB Space Gray",
        "model": iPhoneModel.IPHONE_13,
        "series": iPhoneSeries.IPHONE_13,
        "storage": StorageCapacity.GB_128,
        "color": iPhoneColor.SPACE_GRAY,
        "price": 30000,  # Market is 35000, 14% below
        "battery_health": BatteryHealth(percentage=88),
        "warranty": None,
        "seller": SellerInfo(name="Priya S", city="Bangalore", profile_url="https://olx.in/user/priya", rating=4.2),
        "created_at": datetime.utcnow() - timedelta(hours=20),  # Yesterday
        "url": "https://olx.in/item/iphone-13-1002"
    },
    # FAIR DEAL - At market price
    {
        "id": "1003",
        "title": "iPhone 15 Pro 256GB Natural Titanium",
        "model": iPhoneModel.IPHONE_15_PRO,
        "series": iPhoneSeries.IPHONE_15,
        "storage": StorageCapacity.GB_256,
        "color": iPhoneColor.NATURAL_TITANIUM,
        "price": 98000,  # Market is 100000
        "battery_health": BatteryHealth(percentage=100),
        "warranty": WarrantyInfo(has_warranty=True, warranty_type="Apple Warranty"),
        "seller": SellerInfo(name="Tech Store", city="Coimbatore", rating=4.5, total_listings=50),
        "created_at": datetime.utcnow() - timedelta(days=2),  # 2 days ago
        "url": "https://olx.in/item/iphone-15-pro-1003"
    },
    # OVERPRICED - Too expensive
    {
        "id": "1004",
        "title": "iPhone 12 64GB Blue - Minor Scratch",
        "model": iPhoneModel.IPHONE_12,
        "series": iPhoneSeries.IPHONE_12,
        "storage": StorageCapacity.GB_64,
        "color": iPhoneColor.BLUE,
        "price": 35000,  # Market is 25000, 40% overpriced!
        "battery_health": BatteryHealth(percentage=72),
        "warranty": None,
        "seller": SellerInfo(name="Unknown", city="Chennai"),
        "created_at": datetime.utcnow() - timedelta(hours=12),
        "url": "https://olx.in/item/iphone-12-1004"
    },
    # GOOD DEAL - Old listing but good price
    {
        "id": "1005",
        "title": "iPhone 11 Pro 256GB Midnight Green",
        "model": iPhoneModel.IPHONE_11_PRO,
        "series": iPhoneSeries.IPHONE_11,
        "storage": StorageCapacity.GB_256,
        "color": iPhoneColor.GREEN,
        "price": 26000,  # Market is 34000, 24% below
        "battery_health": BatteryHealth(percentage=82),
        "warranty": None,
        "seller": SellerInfo(name="Mobile Hub", city="Bangalore", profile_url="https://olx.in/user/mobilehub", total_listings=25),
        "created_at": datetime.utcnow() - timedelta(days=5),  # 5 days ago
        "url": "https://olx.in/item/iphone-11-pro-1005"
    },
    # HOT DEAL - Amazing price on recent model
    {
        "id": "1006",
        "title": "iPhone 15 128GB Pink - Brand New Sealed",
        "model": iPhoneModel.IPHONE_15,
        "series": iPhoneSeries.IPHONE_15,
        "storage": StorageCapacity.GB_128,
        "color": iPhoneColor.PINK,
        "price": 42000,  # Market is 55000, 24% below
        "battery_health": BatteryHealth(percentage=100),
        "warranty": WarrantyInfo(has_warranty=True, warranty_type="Apple 1 Year"),
        "seller": SellerInfo(name="Apple Reseller", city="Chennai", profile_url="https://olx.in/user/applereseller", rating=4.9, total_listings=100),
        "created_at": datetime.utcnow() - timedelta(hours=3),  # Today
        "url": "https://olx.in/item/iphone-15-1006"
    },
]


def create_listings() -> list[iPhoneListing]:
    """Create iPhoneListing objects from sample data."""
    listings = []
    for data in SAMPLE_LISTINGS:
        listing = iPhoneListing(
            id=data["id"],
            title=data["title"],
            model=data["model"],
            series=data["series"],
            storage=data["storage"],
            color=data["color"],
            price=data["price"],
            currency="INR",
            battery_health=data.get("battery_health"),
            warranty=data.get("warranty"),
            seller=data["seller"],
            created_at=data["created_at"],
            url=data.get("url"),
            source="olx_india"
        )
        listings.append(listing)
    return listings


def main():
    print("=" * 70)
    print("🧪 TETRO-STACK QUALIFICATION TEST")
    print("=" * 70)
    
    # Create sample listings
    listings = create_listings()
    print(f"\n📦 Created {len(listings)} sample listings")
    
    # Test inventory filtering
    print(f"\n{'─' * 70}")
    print("📊 INVENTORY FILTERING")
    print("─" * 70)
    
    filter_engine = InventoryFilterEngine()
    summary = filter_engine.get_inventory_summary(listings)
    
    print(f"\n  Age Distribution:")
    print(f"    1-day old:  {summary['1_day']} listings")
    print(f"    3-day old:  {summary['3_day']} listings")
    print(f"    5-day old:  {summary['5_day']} listings")
    print(f"    7-day old:  {summary['7_day']} listings")
    print(f"    Total:      {summary['total']} listings")
    
    # Filter to 1-day only (for nightly job)
    one_day = filter_engine.filter_by_days(listings, 1)
    print(f"\n  ✅ 1-day filter: {len(one_day)} listings pass")
    for l in one_day:
        print(f"      • {l.model.value} - ₹{l.price:,} ({l.days_active} days old)")
    
    # Test qualification
    print(f"\n{'─' * 70}")
    print("🎯 DEAL QUALIFICATION")
    print("─" * 70)
    
    qualifier = ListingQualifier()
    qualified = [qualifier.qualify(l) for l in listings]
    qualified.sort(key=lambda q: q.deal_score, reverse=True)
    
    # Show all with details
    for q in qualified:
        l = q.listing
        print(f"\n  {q.deal_quality.value} | Score: {q.deal_score}/100 | Seller: {q.seller_rating.value}")
        print(f"    📱 {l.model.value} ({l.storage.value})")
        print(f"    💰 ₹{l.price:,}")
        print(f"    📍 {l.seller.city} | 🕐 {l.days_active} day(s) old")
        if l.battery_health and l.battery_health.percentage:
            print(f"    🔋 Battery: {l.battery_health.percentage}%")
        if l.warranty and l.warranty.has_warranty:
            print(f"    ✓ Warranty: {l.warranty.warranty_type}")
        print(f"    Notes: {', '.join(q.notes[:3])}")
    
    # Summary
    print(f"\n{'─' * 70}")
    print("📋 SUMMARY")
    print("─" * 70)
    
    hot = [q for q in qualified if q.deal_quality == DealQuality.HOT]
    good = [q for q in qualified if q.deal_quality == DealQuality.GOOD]
    fair = [q for q in qualified if q.deal_quality == DealQuality.FAIR]
    skip = [q for q in qualified if q.deal_quality == DealQuality.OVERPRICED]
    
    print(f"\n  🔥 HOT deals:  {len(hot)}")
    print(f"  ✅ GOOD deals: {len(good)}")
    print(f"  ⚡ FAIR deals: {len(fair)}")
    print(f"  ❌ SKIP:       {len(skip)}")
    
    # Filter criteria test
    print(f"\n{'─' * 70}")
    print("🔧 ADVANCED FILTERING")
    print("─" * 70)
    
    criteria = FilterCriteria(
        days_active=1,
        min_battery_health=85,
        cities=["Chennai", "Bangalore"]
    )
    
    advanced_filtered = filter_engine.apply_criteria(listings, criteria)
    print(f"\n  Criteria: 1-day, battery≥85%, Chennai/Bangalore")
    print(f"  Results: {len(advanced_filtered)} listings")
    
    for l in advanced_filtered:
        bat = l.battery_health.percentage if l.battery_health else "N/A"
        print(f"    • {l.model.value} | ₹{l.price:,} | {bat}% | {l.seller.city}")
    
    print(f"\n{'=' * 70}")
    print("✅ TEST COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
