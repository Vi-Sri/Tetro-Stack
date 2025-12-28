#!/bin/bash
# Tetro-Stack Environment Variables
# Copy this to env.sh and fill in your keys: cp env.example.sh env.sh
# Then source it: source env.sh

# Apify API Token (for OLX India & Facebook Marketplace scrapers)
# Get yours at: https://apify.com/ → Settings → Integrations
export APIFY_API_TOKEN="your_apify_token_here"

# Gemini API Key (for AI-powered listing parsing)
# Get yours at: https://aistudio.google.com/
export GEMINI_API_KEY="your_gemini_api_key_here"

echo "✅ Tetro-Stack environment variables loaded"

