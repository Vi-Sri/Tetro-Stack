#!/usr/bin/env python3
"""
Test the Gemini-powered iPhone parser.
"""

import os
import asyncio

# API keys should be set via: source env.sh
# Or set environment variables: GEMINI_API_KEY, APIFY_API_TOKEN

from tetro_stack.parsers.iphone_parser import iPhoneParser

# Sample listings from OLX India (real examples)
TEST_LISTINGS = [
    {
        "title": "Iphone 13-128Gb( Used ) Excellent Condition",
        "description": """GOKULAN.G
[]Model-IPHONE 13
[]DISPLAY-6.1INCH
[]Processor-A15
[]Front Camera-12MP
[]Rear Camera-12MP
[]Ram-4GB
[]Battery Capacity-3387MAH
[]Capacity -128GB
[]Colour available-RED 

Warranty = 1MONTHS [ SELLER warranty ]
Accessories-available 

We also have IPHONEs FROM 5S to 17pro max 
We provide Credit card EMI 
Brand new condition
Available with us at isqaure garage"""
    },
    {
        "title": "iPhone 15 Pro Max 256GB Natural Titanium - Like New",
        "description": """Selling my iPhone 15 Pro Max
- 256GB Storage
- Natural Titanium Color
- Battery Health: 98%
- AppleCare+ valid till March 2025
- No scratches, always used with case
- Original box and accessories included
Price is slightly negotiable"""
    },
    {
        "title": "iPhone 14 Pro 512gb deep purple 91% battery",
        "description": """iPhone 14 Pro for sale
512 GB storage
Deep Purple color
Battery health 91%
Minor scratches on screen
No warranty
Charger included"""
    },
]


def test_parser():
    print("=" * 60)
    print("🧪 GEMINI PARSER TEST")
    print("=" * 60)
    
    parser = iPhoneParser()
    
    if parser.use_ai:
        print("✅ Gemini AI is active\n")
    else:
        print("⚠️  Using regex fallback (Gemini not available)\n")
    
    for i, listing in enumerate(TEST_LISTINGS, 1):
        print(f"\n{'─' * 60}")
        print(f"📱 LISTING {i}: {listing['title'][:50]}...")
        print(f"{'─' * 60}")
        
        result = parser.parse_listing(listing["title"], listing["description"])
        
        print(f"  Model:   {result['model'].value if result['model'] else 'Unknown'}")
        print(f"  Series:  {result['series'].value if result['series'] else 'Unknown'}")
        print(f"  Storage: {result['storage'].value if result['storage'] else 'Unknown'}")
        print(f"  Color:   {result['color'].value if result['color'] else 'Unknown'}")
        
        if result.get('battery_health'):
            print(f"  Battery: {result['battery_health'].percentage}%")
        else:
            print(f"  Battery: Not specified")
            
        if result.get('warranty'):
            print(f"  Warranty: Yes ({result['warranty'].warranty_type or 'Type unknown'})")
        else:
            print(f"  Warranty: No")
    
    print("\n" + "=" * 60)
    print("✅ Parser test completed!")
    print("=" * 60)


if __name__ == "__main__":
    test_parser()

