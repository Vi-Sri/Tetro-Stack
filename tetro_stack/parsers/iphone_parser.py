"""
iPhone Listing Parser using Gemini AI.

Extracts structured iPhone specifications from unstructured listing text using Google's Gemini model.
This provides superior accuracy over regex patterns, especially for messy user-generated content.
"""

import json
import logging
import re
from typing import Optional, Dict, Any

from ..models.iphone_listing import (
    iPhoneSeries,
    iPhoneModel,
    StorageCapacity,
    iPhoneColor,
    BatteryHealth,
    WarrantyInfo,
)
from ..config import config

logger = logging.getLogger(__name__)

# Try to import the new google.genai package first, fall back to deprecated one
GENAI_AVAILABLE = False
GENAI_CLIENT = None

try:
    from google import genai
    GENAI_AVAILABLE = True
    GENAI_VERSION = "new"
except ImportError:
    try:
        import google.generativeai as genai_legacy
        GENAI_AVAILABLE = True
        GENAI_VERSION = "legacy"
    except ImportError:
        pass


class iPhoneParser:
    """
    Intelligent parser for iPhone listings using Gemini AI.
    Falls back to regex if Gemini is unavailable or fails.
    """
    
    # Available Gemini models (in order of preference)
    GEMINI_MODELS = [
        'gemini-2.0-flash',
        'gemini-1.5-flash',
        'gemini-1.5-pro',
    ]
    
    def __init__(self):
        """Initialize the parser with Gemini API key if available."""
        self.use_ai = False
        self.client = None
        self.model_name = None
        
        if GENAI_AVAILABLE and config.gemini_api_key:
            try:
                if GENAI_VERSION == "new":
                    # New google.genai package
                    self.client = genai.Client(api_key=config.gemini_api_key)
                    
                    # Try available models
                    for model_name in self.GEMINI_MODELS:
                        try:
                            # Test with a simple query
                            self.model_name = model_name
                            self.use_ai = True
                            logger.info(f"Gemini AI parser initialized with {model_name} (new SDK)")
                            break
                        except Exception:
                            continue
                else:
                    # Legacy google.generativeai package
                    genai_legacy.configure(api_key=config.gemini_api_key)
                    
                    for model_name in self.GEMINI_MODELS:
                        try:
                            self.client = genai_legacy.GenerativeModel(model_name)
                            self.model_name = model_name
                            self.use_ai = True
                            logger.info(f"Gemini AI parser initialized with {model_name} (legacy SDK)")
                            break
                        except Exception:
                            continue
                        
                if not self.use_ai:
                    logger.warning("No Gemini models available")
                    
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini AI: {e}")
        elif not GENAI_AVAILABLE:
            logger.info("google-genai package not found. Using regex fallback.")
        elif not config.gemini_api_key:
            logger.info("GEMINI_API_KEY not set. Using regex fallback.")
            
        # Regex patterns for fallback
        self._compile_patterns()
    
    def parse_listing(self, title: str, description: str = "") -> dict:
        """
        Parse iPhone specifications from listing text.
        
        Args:
            title: Listing title
            description: Listing description
            
        Returns:
            Dictionary with parsed specifications fitting the iPhoneListing model
        """
        # Try AI parsing first
        if self.use_ai:
            try:
                return self._parse_with_gemini(title, description)
            except Exception as e:
                logger.error(f"Gemini parsing failed: {e}. Falling back to regex.")
        
        # Fallback to regex
        return self._parse_with_regex(title, description)
    
    def _parse_with_gemini(self, title: str, description: str) -> dict:
        """Use Gemini to extract structured data."""
        prompt = f"""
        Extract iPhone specifications from this marketplace listing into JSON format.
        
        Title: {title}
        Description: {description}
        
        Output must be valid JSON with these fields:
        - model: Specific model string (e.g., "iPhone 15 Pro Max", "iPhone 13")
        - series: Series string (e.g., "iPhone 15", "iPhone 13")
        - storage: Storage string (e.g., "128GB", "256GB", "1TB", "Unknown")
        - color: Color string (e.g., "Natural Titanium", "Blue", "Unknown")
        - battery_health: Integer percentage (0-100) or null if not found
        - has_warranty: Boolean
        - warranty_type: String or null (e.g., "AppleCare+", "Seller Warranty")
        
        Rules:
        1. If a field is not found, use "Unknown" or null/false as appropriate.
        2. Normalize model names (e.g., "15PM" -> "iPhone 15 Pro Max").
        3. Only extract explicitly stated info.
        """
        
        # Generate response based on SDK version
        if GENAI_VERSION == "new":
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            text = response.text
        else:
            response = self.client.generate_content(prompt)
            text = response.text
        
        # Clean markdown code blocks if present
        if "```json" in text:
            text = text.replace("```json", "").replace("```", "")
        elif "```" in text:
            text = text.replace("```", "")
            
        data = json.loads(text.strip())
        
        # Map to our Enums
        return {
            "series": self._map_enum(iPhoneSeries, data.get("series"), iPhoneSeries.UNKNOWN),
            "model": self._map_enum(iPhoneModel, data.get("model"), iPhoneModel.UNKNOWN),
            "storage": self._map_enum(StorageCapacity, data.get("storage"), StorageCapacity.UNKNOWN),
            "color": self._map_enum(iPhoneColor, data.get("color"), iPhoneColor.UNKNOWN),
            "battery_health": BatteryHealth(percentage=data.get("battery_health")) if data.get("battery_health") else None,
            "warranty": WarrantyInfo(
                has_warranty=data.get("has_warranty", False),
                warranty_type=data.get("warranty_type")
            ) if data.get("has_warranty") else None
        }
    
    def _map_enum(self, enum_cls, value, default):
        """Map string value to Enum member."""
        if not value:
            return default
        try:
            # Try exact match
            return enum_cls(value)
        except ValueError:
            # Try case-insensitive match
            for member in enum_cls:
                if member.value.lower() == str(value).lower():
                    return member
            return default

    def _compile_patterns(self):
        """Compile regex patterns for fallback parsing."""
        self.BATTERY_PATTERN = re.compile(r"battery\s*(?:health|life|condition)?[:\s]*(\d{1,3})\s*%", re.IGNORECASE)
        self.STORAGE_PATTERN = re.compile(r"(\d{1,4})\s*(?:gb|tb)", re.IGNORECASE)
        
        # Simple keyword matching for models/colors
        self.MODEL_KEYWORDS = {m.value.lower(): m for m in iPhoneModel}
        self.COLOR_KEYWORDS = {c.value.lower(): c for c in iPhoneColor}

    def _parse_with_regex(self, title: str, description: str) -> dict:
        """Fallback regex parsing."""
        full_text = f"{title} {description}".lower()
        
        result = {
            "series": iPhoneSeries.UNKNOWN,
            "model": iPhoneModel.UNKNOWN,
            "storage": StorageCapacity.UNKNOWN,
            "color": iPhoneColor.UNKNOWN,
            "battery_health": None,
            "warranty": None,
        }
        
        # Find longest matching model name
        found_model = None
        longest_match = 0
        for name, enum_val in self.MODEL_KEYWORDS.items():
            if name in full_text and len(name) > longest_match:
                found_model = enum_val
                longest_match = len(name)
        
        if found_model:
            result["model"] = found_model
            # Infer series from model (e.g. "iPhone 15 Pro" -> "iPhone 15")
            for series in iPhoneSeries:
                if series.value in found_model.value:
                    result["series"] = series
                    break
        
        # Storage
        storage_match = self.STORAGE_PATTERN.search(full_text)
        if storage_match:
            qty = storage_match.group(1)
            unit = "tb" if "tb" in storage_match.group(0).lower() else "gb"
            val = f"{qty}{unit.upper()}"
            try:
                result["storage"] = StorageCapacity(val)
            except ValueError:
                pass

        # Color
        for name, enum_val in self.COLOR_KEYWORDS.items():
            if name in full_text:
                result["color"] = enum_val
                break
                
        # Battery
        bat_match = self.BATTERY_PATTERN.search(full_text)
        if bat_match:
            try:
                result["battery_health"] = BatteryHealth(percentage=int(bat_match.group(1)))
            except ValueError:
                pass
                
        # Warranty
        if "warranty" in full_text or "applecare" in full_text:
            result["warranty"] = WarrantyInfo(has_warranty=True, raw_text="Warranty mentioned")
            
        return result
