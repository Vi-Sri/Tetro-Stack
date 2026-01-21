#!/usr/bin/env python3
"""
Tetro-Stack Nightly Job

Scheduled task that runs every night to:
1. Fetch latest 1-day iPhone listings from OLX India & Facebook Marketplace
2. Parse with Gemini AI
3. Qualify listings based on deal criteria
4. Assign seller ratings
5. Export qualified leads

Usage:
    python nightly_job.py                    # Run full pipeline
    python nightly_job.py --days 1           # Only 1-day listings (default)
    python nightly_job.py --platform olx     # Only OLX
    python nightly_job.py --dry-run          # Test without scraping
"""

import os
import sys
import asyncio
import json
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
from typing import Optional
from pathlib import Path

# Ensure environment is loaded
if not os.environ.get("APIFY_API_TOKEN"):
    print("Loading environment from env.sh...")
    env_file = Path(__file__).parent / "env.sh"
    if env_file.exists():
        import subprocess
        result = subprocess.run(f"source {env_file} && env", shell=True, capture_output=True, text=True, executable="/bin/bash")
        for line in result.stdout.split("\n"):
            if "=" in line and not line.startswith("_"):
                key, _, value = line.partition("=")
                os.environ[key] = value

from tetro_stack.clients.apify_client import ApifyMarketplaceClient
from tetro_stack.clients.platforms import Platform
from tetro_stack.parsers.iphone_parser import iPhoneParser
from tetro_stack.filters.inventory_filter import InventoryFilterEngine, FilterCriteria
from tetro_stack.models.iphone_listing import iPhoneListing, iPhoneSeries, StorageCapacity
from tetro_stack.exporters.data_exporter import DataExporter


class DealQuality(str, Enum):
    """Deal quality classification."""
    HOT = "HOT"           # Excellent deal - act fast
    GOOD = "GOOD"         # Good deal
    FAIR = "FAIR"         # Fair price
    OVERPRICED = "SKIP"   # Overpriced


class SellerRating(str, Enum):
    """Seller trust rating."""
    TRUSTED = "TRUSTED"       # High trust - AI Verifications
    VERIFIED = "VERIFIED"        # Moderate trust  
    NEW = "NEW"               # New/unknown seller
    CAUTION = "CAUTION"          # Proceed with caution


@dataclass
class QualifiedListing:
    """A listing that passed qualification with ratings."""
    listing: iPhoneListing 
    deal_quality: DealQuality
    seller_rating: SellerRating
    deal_score: int  # 0-100
    notes: list[str]


class ListingQualifier:
    """
    Qualifies iPhone listings based on price, specs, and seller info.
    """
    
    # Market price estimates (INR) - Updated Jan 2025
    MARKET_PRICES = {
        # iPhone 16 series
        "iPhone 16 Pro Max": {"128GB": 135000, "256GB": 145000, "512GB": 165000, "1TB": 185000},
        "iPhone 16 Pro": {"128GB": 115000, "256GB": 125000, "512GB": 145000, "1TB": 165000},
        "iPhone 16 Plus": {"128GB": 85000, "256GB": 95000, "512GB": 110000},
        "iPhone 16": {"64GB": 70000, "128GB": 75000, "256GB": 85000},
        
        # iPhone 15 series
        "iPhone 15 Pro Max": {"256GB": 110000, "512GB": 125000, "1TB": 145000},
        "iPhone 15 Pro": {"128GB": 90000, "256GB": 100000, "512GB": 115000, "1TB": 130000},
        "iPhone 15 Plus": {"128GB": 65000, "256GB": 75000, "512GB": 85000},
        "iPhone 15": {"128GB": 55000, "256GB": 65000, "512GB": 75000},
        
        # iPhone 14 series  
        "iPhone 14 Pro Max": {"128GB": 75000, "256GB": 85000, "512GB": 95000, "1TB": 110000},
        "iPhone 14 Pro": {"128GB": 65000, "256GB": 72000, "512GB": 82000, "1TB": 95000},
        "iPhone 14 Plus": {"128GB": 50000, "256GB": 58000, "512GB": 68000},
        "iPhone 14": {"128GB": 42000, "256GB": 50000, "512GB": 58000},
        
        # iPhone 13 series
        "iPhone 13 Pro Max": {"128GB": 55000, "256GB": 62000, "512GB": 72000, "1TB": 85000},
        "iPhone 13 Pro": {"128GB": 48000, "256GB": 55000, "512GB": 65000, "1TB": 75000},
        "iPhone 13": {"128GB": 35000, "256GB": 42000, "512GB": 50000},
        "iPhone 13 Mini": {"128GB": 30000, "256GB": 36000, "512GB": 42000},
        
        # iPhone 12 series
        "iPhone 12 Pro Max": {"128GB": 42000, "256GB": 48000, "512GB": 55000},
        "iPhone 12 Pro": {"128GB": 35000, "256GB": 42000, "512GB": 48000},
        "iPhone 12": {"64GB": 25000, "128GB": 30000, "256GB": 36000},
        "iPhone 12 Mini": {"64GB": 22000, "128GB": 26000, "256GB": 32000},
        
        # iPhone 11 series
        "iPhone 11 Pro Max": {"64GB": 32000, "256GB": 38000, "512GB": 45000},
        "iPhone 11 Pro": {"64GB": 28000, "256GB": 34000, "512GB": 40000},
        "iPhone 11": {"64GB": 20000, "128GB": 24000, "256GB": 30000},
    }
    
    def get_market_price(self, model: str, storage: str) -> Optional[int]:
        """Get estimated market price for model+storage combo."""
        model_prices = self.MARKET_PRICES.get(model, {})
        return model_prices.get(storage)
    
    def calculate_deal_score(self, listing: iPhoneListing) -> tuple[int, DealQuality, list[str]]:
        """
        Calculate deal score (0-100) and classify deal quality.
        
        Returns: (score, quality, notes)
        """
        score = 50  # Start neutral
        notes = []
        
        model_name = listing.model.value if listing.model else "Unknown"
        storage_name = listing.storage.value if listing.storage else "Unknown"
        
        # Price analysis
        market_price = self.get_market_price(model_name, storage_name)
        
        if market_price and listing.price > 0:
            price_ratio = listing.price / market_price
            
            if price_ratio < 0.70:
                score += 35
                notes.append(f"💰 {int((1-price_ratio)*100)}% below market!")
            elif price_ratio < 0.85:
                score += 25
                notes.append(f"💰 {int((1-price_ratio)*100)}% below market")
            elif price_ratio < 0.95:
                score += 15
                notes.append("Fair market price")
            elif price_ratio < 1.10:
                score -= 10
                notes.append("Slightly above market")
            else:
                score -= 25
                notes.append(f"⚠️ {int((price_ratio-1)*100)}% overpriced")
        else:
            notes.append("Unable to verify price")
        
        # Battery health bonus
        if listing.battery_health and listing.battery_health.percentage:
            bat = listing.battery_health.percentage
            if bat >= 95:
                score += 15
                notes.append(f"Excellent battery ({bat}%)")
            elif bat >= 85:
                score += 8
                notes.append(f"Good battery ({bat}%)")
            elif bat >= 75:
                score += 0
                notes.append(f"Fair battery ({bat}%)")
            else:
                score -= 15
                notes.append(f"Low battery ({bat}%)")
        
        # Warranty bonus
        if listing.warranty and listing.warranty.has_warranty:
            score += 10
            notes.append(f"✓ Has warranty ({listing.warranty.warranty_type or 'unspecified'})")
        
        # Freshness bonus (newer listings = more relevant)
        if listing.days_active == 0:
            score += 5
            notes.append("📍 Listed today")
        elif listing.days_active == 1:
            score += 3
            notes.append("📍 Listed yesterday")
        
        # Model desirability (Pro models worth more)
        if "Pro Max" in model_name:
            score += 5
        elif "Pro" in model_name:
            score += 3
        
        # Clamp score
        score = max(0, min(100, score))
        
        # Classify
        if score >= 75:
            quality = DealQuality.HOT
        elif score >= 55:
            quality = DealQuality.GOOD
        elif score >= 40:
            quality = DealQuality.FAIR
        else:
            quality = DealQuality.OVERPRICED
        
        return score, quality, notes
    
    def calculate_seller_rating(self, listing: iPhoneListing) -> tuple[SellerRating, list[str]]:
        """
        Calculate seller trustworthiness rating.
        
        Returns: (rating, notes)
        """
        notes = []
        trust_score = 50
        
        # Check seller info completeness
        if listing.seller.name and listing.seller.name not in ["Unknown", "Seller", ""]:
            trust_score += 10
            notes.append(f"Seller: {listing.seller.name}")
        else:
            trust_score -= 10
            notes.append("Anonymous seller")
        
        # Check if profile URL exists
        if listing.seller.profile_url:
            trust_score += 15
            notes.append("Has profile link")
        
        # Check seller rating if available
        if listing.seller.rating:
            if listing.seller.rating >= 4.5:
                trust_score += 20
                notes.append(f"{listing.seller.rating}/5 rating")
            elif listing.seller.rating >= 4.0:
                trust_score += 10
                notes.append(f"{listing.seller.rating}/5 rating")
            elif listing.seller.rating < 3.0:
                trust_score -= 20
                notes.append(f"Low rating: {listing.seller.rating}/5")
        
        # Check total listings
        if listing.seller.total_listings:
            if listing.seller.total_listings >= 10:
                trust_score += 15
                notes.append(f"Experienced seller ({listing.seller.total_listings} listings)")
            elif listing.seller.total_listings >= 3:
                trust_score += 5
        
        # Check location
        if listing.seller.city:
            trust_score += 5
            notes.append(f"{listing.seller.city}")
        
        # Classify
        if trust_score >= 70:
            rating = SellerRating.TRUSTED
        elif trust_score >= 50:
            rating = SellerRating.VERIFIED
        elif trust_score >= 30:
            rating = SellerRating.NEW
        else:
            rating = SellerRating.CAUTION
        
        return rating, notes
    
    def qualify(self, listing: iPhoneListing) -> QualifiedListing:
        """Fully qualify a listing with deal score and seller rating."""
        deal_score, deal_quality, deal_notes = self.calculate_deal_score(listing)
        seller_rating, seller_notes = self.calculate_seller_rating(listing)
        
        return QualifiedListing(
            listing=listing,
            deal_quality=deal_quality,
            seller_rating=seller_rating,
            deal_score=deal_score,
            notes=deal_notes + seller_notes
        )


async def run_nightly_job(
    days_filter: int = 1,
    platforms: list[Platform] = None,
    dry_run: bool = False,
    max_results: int = 100
):
    """
    Run the nightly scraping and qualification job.
    
    Args:
        days_filter: Max listing age in days (default: 1)
        platforms: Which platforms to scrape (default: both)
        dry_run: If True, use cached data instead of scraping
        max_results: Max listings per platform
    """
    print("=" * 60)
    print(f"TETRO-STACK NIGHTLY JOB")
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Filter: Last {days_filter} day(s)")
    print("=" * 60)
    
    platforms = platforms or [Platform.OLX_INDIA, Platform.FACEBOOK_MARKETPLACE]
    all_listings = []
    
    if not dry_run:
        # Initialize clients
        client = ApifyMarketplaceClient()
        parser = iPhoneParser()
        
        print(f"\n🤖 Gemini AI: {'Active' if parser.use_ai else 'Inactive (using regex)'}")
        
        for platform in platforms:
            print(f"\n{'─' * 40}")
            print(f"📱 Scraping {platform.value}...")
            
            try:
                listings = await client.fetch_listings(
                    platform=platform,
                    query="iPhone",
                    max_results=max_results,
                    days_filter=days_filter
                )
                
                print(f"   Raw listings: {len(listings)}")
                
                # Parse with AI
                for listing in listings:
                    if listing.title:
                        parsed = parser.parse_listing(
                            listing.title,
                            listing.description or ""
                        )
                        # Update listing with parsed data
                        listing.series = parsed.get("series", listing.series)
                        listing.model = parsed.get("model", listing.model)
                        listing.storage = parsed.get("storage", listing.storage)
                        listing.color = parsed.get("color", listing.color)
                        if parsed.get("battery_health"):
                            listing.battery_health = parsed["battery_health"]
                        if parsed.get("warranty"):
                            listing.warranty = parsed["warranty"]
                
                all_listings.extend(listings)
                print(f"   Added {len(listings)} listings")
                
            except Exception as e:
                print(f"   Error: {e}")
    else:
        print("\nDry Run - Using sample data")
        # Would load from cache here
    
    if not all_listings:
        print("\nNo listings found!")
        return
    
    # Apply inventory filter
    filter_engine = InventoryFilterEngine()
    filtered = filter_engine.filter_by_days(all_listings, days_filter)
    
    print(f"\nInventory Summary")
    print(f"   Total scraped: {len(all_listings)}")
    print(f"   Within {days_filter}-day filter: {len(filtered)}")
    
    # Show breakdown
    summary = filter_engine.get_inventory_summary(all_listings)
    print(f"\n   Age Breakdown:")
    print(f"      1-day: {summary['1_day']}")
    print(f"      3-day: {summary['3_day']}")
    print(f"      5-day: {summary['5_day']}")
    print(f"      7-day: {summary['7_day']}")
    
    # Qualify listings
    print(f"\nQualifying Listings...")
    qualifier = ListingQualifier()
    qualified = [qualifier.qualify(l) for l in filtered]
    
    # Sort by deal score
    qualified.sort(key=lambda q: q.deal_score, reverse=True)
    
    # Group by quality
    hot_deals = [q for q in qualified if q.deal_quality == DealQuality.HOT]
    good_deals = [q for q in qualified if q.deal_quality == DealQuality.GOOD]
    fair_deals = [q for q in qualified if q.deal_quality == DealQuality.FAIR]
    skip_deals = [q for q in qualified if q.deal_quality == DealQuality.OVERPRICED]
    
    print(f"\nQualification Results")
    print(f"   HOT deals: {len(hot_deals)}")
    print(f"   GOOD deals: {len(good_deals)}")
    print(f"   FAIR deals: {len(fair_deals)}")
    print(f"   SKIP: {len(skip_deals)}")
    
    # Show top deals
    print(f"\n{'=' * 60}")
    print("Top Deals")
    print("=" * 60)
    
    for i, q in enumerate(qualified[:10], 1):
        l = q.listing
        print(f"\n{i}. {q.deal_quality.value} | Score: {q.deal_score}/100 | {q.seller_rating.value}")
        print(f"   {l.model.value} {l.storage.value}")
        print(f"   ₹{l.price:,.0f}")
        print(f"   {l.seller.city or 'Unknown location'}")
        print(f"   {l.url[:60]}..." if l.url else "No URL")
        for note in q.notes[:3]:
            print(f"    {note}")
    
    # Export results
    print(f"\n{'=' * 60}")
    print("Exporting Results")
    print("=" * 60)
    
    exports_dir = Path("exports")
    exports_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Export all qualified (not skipped)
    good_listings = [q.listing for q in qualified if q.deal_quality != DealQuality.OVERPRICED]
    
    if good_listings:
        exporter = DataExporter()
        
        csv_path = exports_dir / f"qualified_leads_{timestamp}.csv"
        exporter.to_csv(good_listings, str(csv_path))
        print(f"   CSV: {csv_path}")
        
        json_path = exports_dir / f"qualified_leads_{timestamp}.json"
        exporter.to_json(good_listings, str(json_path))
        print(f"   JSON: {json_path}")
        
        # Export summary
        summary_data = {
            "job_time": datetime.now().isoformat(),
            "days_filter": days_filter,
            "total_scraped": len(all_listings),
            "total_qualified": len(good_listings),
            "breakdown": {
                "hot": len(hot_deals),
                "good": len(good_deals),
                "fair": len(fair_deals),
                "skipped": len(skip_deals)
            },
            "top_deals": [
                {
                    "model": q.listing.model.value,
                    "storage": q.listing.storage.value,
                    "price": q.listing.price,
                    "score": q.deal_score,
                    "quality": q.deal_quality.value,
                    "url": q.listing.url
                }
                for q in qualified[:20]
            ]
        }
        
        summary_path = exports_dir / f"job_summary_{timestamp}.json"
        with open(summary_path, "w") as f:
            json.dump(summary_data, f, indent=2)
        print(f"   Summary: {summary_path}")
    
    print(f"\n{'=' * 60}")
    print("Nightly Job Complete")
    print("=" * 60)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Tetro-Stack Nightly Job")
    parser.add_argument("--days", type=int, default=1, help="Max listing age in days")
    parser.add_argument("--platform", choices=["olx", "facebook", "both"], default="both")
    parser.add_argument("--dry-run", action="store_true", help="Use cached data")
    parser.add_argument("--max-results", type=int, default=100, help="Max results per platform")
    
    args = parser.parse_args()
    
    platforms = None
    if args.platform == "olx":
        platforms = [Platform.OLX_INDIA]
    elif args.platform == "facebook":
        platforms = [Platform.FACEBOOK_MARKETPLACE]
    
    asyncio.run(run_nightly_job(
        days_filter=args.days,
        platforms=platforms,
        dry_run=args.dry_run,
        max_results=args.max_results
    ))
