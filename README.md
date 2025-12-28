# 📱 Tetro-Stack

**Cross-Platform iPhone Marketplace Intelligence**

A Python client to scrape, parse, and analyze iPhone listings from multiple marketplaces (OLX India, Facebook Marketplace) with AI-powered data extraction.

## ✨ Features

- **Multi-Platform Scraping**: OLX India + Facebook Marketplace
- **AI-Powered Parsing**: Gemini 2.0 Flash extracts iPhone specs from unstructured text
- **Structured Data Extraction**:
  - Series, Model, Storage, Color
  - Battery Health, Warranty info
  - Seller details, Price, Location
- **Smart Filtering**: 1-day, 3-day, 5-day, 7-day inventory age filters
- **Export**: CSV and JSON formats
- **Cities Supported**: Chennai, Bangalore, Coimbatore

## 🚀 Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/Vi-Sri/Tetro-Stack.git
cd Tetro-Stack
pip install -r requirements.txt
```

### 2. Configure Environment

Create `env.sh` with your API keys:

```bash
#!/bin/bash
export APIFY_API_TOKEN="your_apify_token_here"
export GEMINI_API_KEY="your_gemini_api_key_here"
```

Then source it:

```bash
source env.sh
```

### 3. Run the Scraper

```bash
# Full cross-platform scrape (OLX + Facebook)
python test_ensemble.py

# Token validation & cached data (no credits used)
python test_integration.py

# Test AI parser only
python test_gemini_parser.py
```

## 🔑 API Keys Setup

### Apify (Required)
1. Sign up at [apify.com](https://apify.com)
2. Go to **Settings → Integrations**
3. Copy your API token
4. Add payment method for paid actors

**Actors Used:**
- `natanielsantos/olx-india-scraper` (OLX India)
- `curious_coder/facebook-marketplace` (Facebook Marketplace)

### Gemini AI (Optional, enhances parsing)
1. Go to [Google AI Studio](https://aistudio.google.com/)
2. Create API key
3. Model used: `gemini-2.0-flash`

## 📁 Project Structure

```
tetro_stack/
├── clients/
│   ├── apify_client.py     # Apify scraper integration
│   ├── platforms.py        # Platform configs (OLX, FB)
│   └── base_client.py      # Abstract base client
├── models/
│   └── iphone_listing.py   # Pydantic data models
├── parsers/
│   └── iphone_parser.py    # Gemini AI + regex parsing
├── filters/
│   └── inventory_filter.py # Age-based filtering
├── exporters/
│   └── data_exporter.py    # CSV/JSON export
└── config.py               # Configuration
```

## 📊 Sample Output

```
┏━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━┓
┃ Model             ┃ Storage ┃ Price    ┃ City          ┃
┡━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━┩
│ iPhone 14 Pro Max │ 128GB   │ ₹54,500  │ Bengaluru, KA │
│ iPhone 13         │ 128GB   │ ₹27,000  │ Chennai, TN   │
│ iPhone 12 Pro     │ 256GB   │ ₹26,000  │ Bengaluru, KA │
│ iPhone 11         │ 64GB    │ ₹14,500  │ Coimbatore    │
└───────────────────┴─────────┴──────────┴───────────────┘
```

## 📈 Data Fields

| Field | Description |
|-------|-------------|
| `series` | iPhone generation (11, 12, 13, 14, 15, 16) |
| `model` | Specific model (Pro, Pro Max, Plus, Mini) |
| `storage` | Capacity (64GB, 128GB, 256GB, 512GB, 1TB) |
| `color` | Device color |
| `battery_health` | Battery percentage if available |
| `warranty` | Warranty status and type |
| `price` | Listed price in INR |
| `seller.city` | Seller location |
| `days_active` | Days since listing was posted |
| `source` | Platform (olx_india, facebook_marketplace) |

## ⚡ Performance

- **~240 listings** per run (100 OLX + 140 Facebook)
- **~55 seconds** total scrape time
- **3 cities** searched simultaneously
- **AI parsing** with regex fallback

## 📝 Notes

- Listings older than 5 days are filtered out (iPhones move fast!)
- Facebook Marketplace doesn't expose seller names in search results
- Gemini free tier has rate limits; falls back to regex when exceeded


