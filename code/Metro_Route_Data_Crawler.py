#!/usr/bin/env python3
"""
Metro Route Data Crawler

This module crawls metro/subway route data from Chinese mapping APIs and web sources.
Collects route geometries, stop locations, and operational information for
urban metro transportation network analysis.

Dependencies:
    - requests
    - pandas
    - BeautifulSoup4
    - uuid
    - transform (coordinate conversion module)
    - box_test (testing utilities)

Input:
    - City list CSV file with city names and codes
    - AMap API key for geocoding services
    - 
    Translation API key for Chinese to English translation

Output:
    - Enhanced CSV files with metro route data per city
    - Route geometries and stop information
    - Operational details (schedule, pricing)

Author: Urban Transportation Research Team
License: MIT
"""

import csv
import json
import os
import threading
import time
import re
import requests
import pandas as pd
import uuid
import hashlib
from urllib.parse import quote
import transform
import box_test
from bs4 import BeautifulSoup

# Global configuration
API_KEY = "Your Amap Key"
ALLOWED_METRO_TYPES = ['地铁', '轻轨', '有轨电车', '无轨电车', '磁悬浮列车']

# Azure Translation API configuration
AZURE_TRANSLATOR_KEY = "Your Azure Key"
AZURE_TRANSLATOR_ENDPOINT = "https://api.cognitive.microsofttranslator.com"
AZURE_TRANSLATOR_LOCATION = "eastasia"

# Translation cache to avoid repeated translation of same content
translation_cache = {}

# Cache for city mapping to avoid repeated loading
_city_mapping_cache = None


def safe_get_string(data, default=""):
    """
    Safely get string value, handling cases where data might be a list or other types
    
    Args:
        data: Data to extract string from
        default (str): Default value if extraction fails
        
    Returns:
        str: Extracted string value
    """
    if isinstance(data, str):
        return data.strip()
    elif isinstance(data, list):
        # If it's a list, try to get the first element, return default if empty
        if len(data) > 0 and isinstance(data[0], str):
            return data[0].strip()
        else:
            return default
    elif data is None:
        return default
    else:
        # Other types, try to convert to string
        return str(data).strip()


def chinese_to_english(text):
    """
    Convert Chinese text to English using Azure Translation API
    
    Args:
        text (str): Chinese text to translate
        
    Returns:
        str: English translation
    """
    if not text or not isinstance(text, str):
        return ""
    
    # Clean text while preserving parentheses and basic punctuation
    cleaned_text = re.sub(r'[^\u4e00-\u9fff\w\(\)（）\-\s]', '', text).strip()
    
    if not cleaned_text:
        return ""
    
    # Check cache
    if cleaned_text in translation_cache:
        return translation_cache[cleaned_text]
    
    try:
        # Build Azure Translation API request
        path = '/translate'
        constructed_url = AZURE_TRANSLATOR_ENDPOINT + path

        params = {
            'api-version': '3.0',
            'from': 'zh-Hans',  # Simplified Chinese
            'to': 'en'         # English
        }

        headers = {
            'Ocp-Apim-Subscription-Key': AZURE_TRANSLATOR_KEY,
            'Ocp-Apim-Subscription-Region': AZURE_TRANSLATOR_LOCATION,
            'Content-type': 'application/json',
            'X-ClientTraceId': str(uuid.uuid4())
        }

        # Request body
        body = [{
            'text': cleaned_text
        }]

        # Send request
        request = requests.post(constructed_url, params=params, headers=headers, json=body, timeout=10)
        response = request.json()

        if request.status_code == 200 and response:
            # Extract translation result
            translated_text = response[0]['translations'][0]['text']
            
            # Process translation result to make it suitable for file names
            processed_text = process_translated_text(translated_text)
            
            # Cache result
            translation_cache[cleaned_text] = processed_text
            
            print(f"Translation successful: '{cleaned_text}' -> '{processed_text}'")
            return processed_text
        else:
            print(f"Translation failed: {request.status_code}, {response}")
            # Fallback handling: use simple pinyin replacement
            fallback_result = fallback_pinyin_conversion(cleaned_text)
            translation_cache[cleaned_text] = fallback_result
            return fallback_result
            
    except Exception as e:
        print(f"Azure Translation API error: {e}")
        # Fallback handling on error
        fallback_result = fallback_pinyin_conversion(cleaned_text)
        translation_cache[cleaned_text] = fallback_result
        return fallback_result


def process_translated_text(translated_text):
    """
    Process translated English text to make it suitable for file names and identifiers
    
    Args:
        translated_text (str): Raw translated text
        
    Returns:
        str: Processed text suitable for file names
    """
    if not translated_text:
        return ""
    
    # Convert to lowercase
    processed = translated_text.lower()
    
    # Remove special characters, keep only letters, numbers, underscores and hyphens
    processed = re.sub(r'[^\w\s\-]', '', processed)
    
    # Replace spaces with underscores
    processed = re.sub(r'\s+', '_', processed)
    
    # Remove multiple underscores
    processed = re.sub(r'_+', '_', processed)
    
    # Remove leading and trailing underscores
    processed = processed.strip('_')
    
    # Return default if result is empty
    if not processed:
        processed = "unknown"
    
    return processed


def fallback_pinyin_conversion(text):
    """
    Fallback handling: simple pinyin conversion when Azure Translation API is unavailable
    This is a simplified version that can be expanded as needed
    
    Args:
        text (str): Chinese text to convert
        
    Returns:
        str: Fallback identifier
    """
    # Simple processing for numbers and existing English characters
    processed = re.sub(r'[^\w\(\)（）]', '', text)
    
    # If text is mainly numbers and existing English, process directly
    if re.match(r'^[\w\(\)（）]+$', processed):
        return processed.lower().replace('（', '(').replace('）', ')')
    
    # Otherwise return a simple identifier based on original text
    hash_part = hashlib.md5(text.encode('utf-8')).hexdigest()[:8]
    return f"metro_{hash_part}"


def batch_translate_texts(texts):
    """
    Batch translate texts to improve efficiency
    Enhanced version: adds input validation to ensure all texts are strings
    
    Args:
        texts (list): List of texts to translate
        
    Returns:
        dict: Mapping from original texts to translations
    """
    if not texts:
        return {}
    
    # Filter and clean texts that need translation
    valid_texts = []
    for text in texts:
        # Ensure it's a string and not empty
        if isinstance(text, str) and text.strip():
            valid_texts.append(text.strip())
        elif text is not None:
            # Try to convert to string
            str_text = str(text).strip()
            if str_text:
                valid_texts.append(str_text)
    
    # Remove duplicates and filter already cached texts
    unique_texts = list(set(valid_texts))
    texts_to_translate = [text for text in unique_texts if text not in translation_cache]
    
    if not texts_to_translate:
        return {text: translation_cache.get(text, "") for text in valid_texts}
    
    try:
        # Build batch translation request
        path = '/translate'
        constructed_url = AZURE_TRANSLATOR_ENDPOINT + path

        params = {
            'api-version': '3.0',
            'from': 'zh-Hans',
            'to': 'en'
        }

        headers = {
            'Ocp-Apim-Subscription-Key': AZURE_TRANSLATOR_KEY,
            'Ocp-Apim-Subscription-Region': AZURE_TRANSLATOR_LOCATION,
            'Content-type': 'application/json',
            'X-ClientTraceId': str(uuid.uuid4())
        }

        # Prepare batch request body (max 100 texts)
        batch_size = 100
        results = {}
        
        for i in range(0, len(texts_to_translate), batch_size):
            batch_texts = texts_to_translate[i:i+batch_size]
            body = [{'text': text} for text in batch_texts]
            
            request = requests.post(constructed_url, params=params, headers=headers, json=body, timeout=30)
            response = request.json()
            
            if request.status_code == 200 and response:
                for j, result in enumerate(response):
                    original_text = batch_texts[j]
                    translated_text = result['translations'][0]['text']
                    processed_text = process_translated_text(translated_text)
                    
                    translation_cache[original_text] = processed_text
                    results[original_text] = processed_text
                    
                print(f"Batch translation successful: {len(batch_texts)} texts")
            else:
                # If batch translation fails, process individually
                print(f"Batch translation failed, switching to individual translation")
                for text in batch_texts:
                    results[text] = chinese_to_english(text)
            
            # Add delay to avoid API limits
            time.sleep(0.1)
        
        # Merge all results (including cached ones)
        final_results = {}
        for text in valid_texts:
            if text in results:
                final_results[text] = results[text]
            elif text in translation_cache:
                final_results[text] = translation_cache[text]
            else:
                final_results[text] = chinese_to_english(text)
        
        return final_results
        
    except Exception as e:
        print(f"Batch translation error: {e}")
        # If error occurs, translate individually
        return {text: chinese_to_english(text) for text in valid_texts}


class MetroDataCrawler:
    """
    Metro route data crawler for Chinese cities
    
    Retrieves comprehensive metro route data including:
    - Route geometries and stop locations
    - Operational information (schedule, pricing)
    - Route type filtering and status validation
    """
    
    def __init__(self, api_key=None, output_dir=None):
        """
        Initialize the metro data crawler
        
        Args:
            api_key (str): AMap API key for geocoding services
            output_dir (str): Output directory for collected data
        """
        self.api_key = api_key or API_KEY
        
        if output_dir is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            output_dir = os.path.join(current_dir, "..", "dataset", "metro")
        
        self.output_dir = output_dir
        self.city_mapping_cache = None
        
        # Ensure output directories exist
        for subdir in ["metro_routes", "metro_stops", "enhanced_data"]:
            os.makedirs(os.path.join(output_dir, subdir), exist_ok=True)
    
    def chinese_to_english_field(self, text):
        """
        Convert Chinese text to English for field names using Azure Translation API
        
        Args:
            text (str): Chinese text to convert
            
        Returns:
            str: English representation
        """
        if not text or not isinstance(text, str):
            return ""
        
        # Clean text while preserving parentheses
        cleaned_text = re.sub(r'[^\u4e00-\u9fff\w\(\)（）]', '', text)
        return chinese_to_english(cleaned_text)
    
    def load_city_mapping_from_csv(self):
        """
        Load city code mapping from CSV file
        
        Returns:
            dict: Mapping from city codes to city names
        """
        if self.city_mapping_cache is not None:
            return self.city_mapping_cache
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        mapping_file = os.path.join(current_dir, "..", "city_list", "AMap_adcode_citycode.csv")
        
        city_mapping = {}
        
        try:
            if not os.path.exists(mapping_file):
                print(f"Warning: City mapping file not found: {mapping_file}")
                return city_mapping
            
            print(f"Loading city mapping table: {mapping_file}")
            
            df = pd.read_csv(mapping_file, encoding='utf-8')
            
            # Check required columns
            if '中文名' not in df.columns or 'citycode' not in df.columns:
                print(f"Error: CSV file missing required columns (中文名, citycode)")
                return city_mapping
            
            # Build mapping relationships
            processed_count = 0
            for _, row in df.iterrows():
                citycode = str(row['citycode']).strip()
                chinese_name = str(row['中文名']).strip()
                
                # Filter invalid citycodes
                if citycode and citycode not in ['nan', '\\N', 'None']:
                    clean_city_name = self._clean_city_name_for_mapping(chinese_name)
                    if clean_city_name:
                        city_mapping[citycode] = clean_city_name
                        processed_count += 1
            
            print(f"Successfully loaded {processed_count} city code mappings")
            self.city_mapping_cache = city_mapping
            
        except Exception as e:
            print(f"Failed to load city mapping file: {e}")
            self.city_mapping_cache = {}
        
        return self.city_mapping_cache
    
    def _clean_city_name_for_mapping(self, city_name):
        """
        Clean city name for mapping purposes
        
        Args:
            city_name (str): Raw city name
            
        Returns:
            str: Cleaned city name
        """
        if not city_name or city_name == 'nan':
            return ""
        
        # Remove common administrative suffixes
        suffixes_to_remove = ['市', '自治区', '自治州', '地区', '盟', '特别行政区']
        
        cleaned_name = city_name
        for suffix in suffixes_to_remove:
            if cleaned_name.endswith(suffix):
                cleaned_name = cleaned_name[:-len(suffix)]
                break
        
        # Special handling for specific regions
        special_mappings = {
            '北京': '北京', '上海': '上海', '天津': '天津', '重庆': '重庆',
            '香港特别行政': '香港', '澳门特别行政': '澳门',
            '内蒙古自治': '内蒙古', '广西壮族自治': '广西',
            '西藏自治': '西藏', '宁夏回族自治': '宁夏',
            '新疆维吾尔自治': '新疆'
        }
        
        for key, value in special_mappings.items():
            if cleaned_name.startswith(key):
                return value
        
        return cleaned_name
    
    def get_city_name_by_code(self, city_code):
        """
        Get city name by city code using mapping table
        
        Args:
            city_code (str): City code
            
        Returns:
            str: Corresponding city name
        """
        if not city_code:
            return "Unknown City"
        
        city_code = str(city_code).strip()
        city_mapping = self.load_city_mapping_from_csv()
        
        city_name = city_mapping.get(city_code)
        
        if city_name:
            return city_name
        
        # Try alternative codes (with/without leading zeros)
        alternative_codes = []
        if city_code.startswith('0'):
            alternative_codes.append(city_code.lstrip('0'))
        if not city_code.startswith('0') and len(city_code) <= 3:
            alternative_codes.append('0' + city_code)
        
        for alt_code in alternative_codes:
            alt_city = city_mapping.get(alt_code)
            if alt_city:
                print(f"Found city code variant mapping: {city_code} -> {alt_code} -> {alt_city}")
                return alt_city
        
        print(f"Warning: City code {city_code} not found in mapping")
        return f"City{city_code}"
    
    def load_metro_cities_from_csv(self, csv_path):
        """
        Load metro cities from CSV configuration file
        
        Args:
            csv_path (str): Path to CSV file with city mappings
            
        Returns:
            dict: Mapping from city codes to city names
        """
        metro_cities = {}
        
        if not os.path.exists(csv_path):
            print(f"Warning: City list file not found: {csv_path}")
            return metro_cities
        
        try:
            df = pd.read_csv(csv_path, encoding='utf-8')
            
            if 'city_simple' not in df.columns or 'city_cn' not in df.columns:
                print(f"Error: CSV file missing required columns (city_simple, city_cn)")
                return metro_cities
            
            for _, row in df.iterrows():
                city_simple = str(row['city_simple']).strip()
                city_cn = str(row['city_cn']).strip()
                
                if city_simple and city_cn and city_simple != 'nan' and city_cn != 'nan':
                    metro_cities[city_simple] = city_cn
            
            print(f"Successfully loaded {len(metro_cities)} city mappings from {csv_path}")
            
        except Exception as e:
            print(f"Failed to read city list file: {e}")
        
        return metro_cities
    
    def get_metro_route_data(self, city_name, line_name):
        """
        Retrieve metro route data from AMap API
        
        Args:
            city_name (str): Target city name
            line_name (str): Metro line identifier
            
        Returns:
            list: List of processed route data dictionaries
        """
        # Build search keywords for metro lines
        metro_keywords = [
            f"{city_name}地铁{line_name}",
            f"地铁{line_name}",
            f"{city_name}{line_name}",
            line_name
        ]
        
        message_list = []
        
        for keywords in metro_keywords:
            try:
                url = quote(
                    f"https://restapi.amap.com/v3/bus/linename?s=rsv3&extensions=all&key={self.api_key}"
                    f"&output=json&city={city_name}&offset=0&keywords={keywords}&platform=JS",
                    safe=":/?&="
                )
                
                response = requests.get(url, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "1" and data.get("buslines"):
                        buslines_list = data["buslines"]
                        
                        print(f"API returned {len(buslines_list)} routes for keywords: {keywords}")
                        
                        for busline in buslines_list:
                            line_name_api = safe_get_string(busline.get("name", ""))
                            line_type = safe_get_string(busline.get("type", ""))
                            
                            # Filter by metro type
                            if line_type not in ALLOWED_METRO_TYPES:
                                print(f"Skipping non-metro type: {line_name_api} (type: {line_type})")
                                continue
                            
                            # Check line name matching
                            if self._is_line_match(line_name, line_name_api):
                                route_data = self._process_route_data(busline, city_name)
                                message_list.append(route_data)
                                print(f"Successfully matched and processed route: {line_name_api}")
                
            except Exception as e:
                print(f"Failed to retrieve data for {city_name} {keywords}: {e}")
                continue
        
        print(f"Total routes found: {len(message_list)}")
        return message_list
    
    def _is_line_match(self, search_line, api_line):
        """
        Check if search line matches API returned line name
        
        Args:
            search_line (str): Line name being searched
            api_line (str): Line name from API
            
        Returns:
            bool: True if lines match
        """
        # Method 1: Direct matching
        if search_line.lower() in api_line.lower():
            return True
        
        # Method 2: Remove "号线" suffix matching
        if search_line.replace("号线", "").lower() in api_line.lower():
            return True
        
        # Method 3: Keyword matching
        if any(part.lower() in api_line.lower() for part in search_line.split() if len(part) > 1):
            return True
        
        # Method 4: Special T-line matching
        if 'T' in search_line.upper() and 'T' in api_line.upper():
            search_t_num = re.findall(r'T(\d+)', search_line.upper())
            api_t_num = re.findall(r'T(\d+)', api_line.upper())
            if search_t_num and api_t_num and search_t_num[0] == api_t_num[0]:
                return True
        
        return False
    
    def _process_route_data(self, busline, city_name):
        """
        Process raw route data from API response
        
        Args:
            busline (dict): Raw busline data from API
            city_name (str): City name
            
        Returns:
            dict: Processed route data
        """
        # Process polyline coordinates
        polyline = safe_get_string(busline.get("polyline", ""))
        coordinates = []
        if polyline:
            coords = polyline.split(";")
            coordinates = [p.split(",") for p in coords if "," in p]
        
        # Collect texts to translate
        texts_to_translate = []
        
        # Get basic route information
        line_name = safe_get_string(busline.get("name", ""))
        company = safe_get_string(busline.get("company", ""))
        start_stop = safe_get_string(busline.get("start_stop", ""))
        end_stop = safe_get_string(busline.get("end_stop", ""))
        
        texts_to_translate.extend([line_name, company, start_stop, end_stop])
        
        # Process metro stops and collect stop names for translation
        enhanced_stops = []
        for stop in busline.get("busstops", []):
            stop_name = safe_get_string(stop.get("name", "")).replace("站", "").strip()
            texts_to_translate.append(stop_name)
            enhanced_stop = {
                "name": stop_name,
                "id": safe_get_string(stop.get("id", "")),
                "stop_unique_id": safe_get_string(stop.get("id", "")),
                "location": safe_get_string(stop.get("location", "")),
                "sequence": stop.get("sequence", len(enhanced_stops) + 1)
            }
            enhanced_stops.append(enhanced_stop)
        
        # Get city information
        city_code = safe_get_string(busline.get("citycode", ""))
        city_name_cn = self.get_city_name_by_code(city_code)
        texts_to_translate.append(city_name_cn)
        
        # Batch translate all texts
        translations = batch_translate_texts(texts_to_translate)
        
        # Apply translations
        line_name_en = translations.get(line_name, chinese_to_english(line_name))
        company_en = translations.get(company, chinese_to_english(company))
        start_stop_en = translations.get(start_stop, chinese_to_english(start_stop))
        end_stop_en = translations.get(end_stop, chinese_to_english(end_stop))
        city_name_en = translations.get(city_name_cn, chinese_to_english(city_name_cn))
        
        # Apply translations to stops
        for stop in enhanced_stops:
            stop["name_en"] = translations.get(stop["name"], chinese_to_english(stop["name"]))
        
        # Extract operational information
        route_data = {
            'route_name_cn': line_name,
            'route_name_en': line_name_en,
            "route_id": safe_get_string(busline.get("id", f"metro_{city_name_en}_{line_name_en}")),
            "city_code": city_code,
            "route_type": safe_get_string(busline.get("type", "地铁")),
            "company_cn": company,
            "company_en": company_en,
            "start_stop_cn": start_stop,
            "start_stop_en": start_stop_en,
            "end_stop_cn": end_stop,
            "end_stop_en": end_stop_en,
            "distance": safe_get_string(busline.get("distance", "0")),
            "start_time": safe_get_string(busline.get("start_time", "")),
            "end_time": safe_get_string(busline.get("end_time", "")),
            "timedesc": safe_get_string(busline.get("timedesc", "")),
            "loop": safe_get_string(busline.get("loop", "")),
            "status": safe_get_string(busline.get("status", "")),
            "basic_price": safe_get_string(busline.get("basic_price", "")),
            "total_price": safe_get_string(busline.get("total_price", "")),
            'polyline': coordinates,
            'metro_stops': enhanced_stops,
            'total_stops': len(enhanced_stops),
            'city_name_cn': city_name_cn,
            'city_name_en': city_name_en
        }
        
        return route_data
    
    def get_metro_lines_from_web(self, city_code, metro_cities):
        """
        Get metro line list from web source (8684.cn)
        
        Args:
            city_code (str): City code
            metro_cities (dict): City mapping dictionary
            
        Returns:
            list: List of operational metro lines
        """
        city_name = metro_cities.get(city_code, city_code)
        metro_lines = []
        
        try:
            base_url = f"https://dt.8684.cn/{city_code}"
            
            response = requests.get(base_url, timeout=30, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            response.encoding = 'utf-8'
            
            if response.status_code != 200:
                print(f"{city_name} metro page unavailable, status code: {response.status_code}")
                return metro_lines
            
            html = BeautifulSoup(response.text, "html.parser")
            
            # Find metro line container
            metro_container = html.find("ul", {"class": "ib-mn rl-mn ib-box"})
            if not metro_container:
                possible_containers = ["ul.ib-mn", "div.ib-mn", "div[class*='line']", "ul[class*='line']"]
                for selector in possible_containers:
                    metro_container = html.select(selector)
                    if metro_container:
                        metro_container = metro_container[0]
                        break
            
            if metro_container:
                unopened_lines = []
                
                for li in metro_container.find_all("li"):
                    line_link = li.find("a", {"class": re.compile(r"line-a")})
                    if not line_link:
                        line_link = li.find("a")
                    
                    # Check for "unopened" marking
                    unopened_mark = li.find("font", {"color": "red"})
                    is_unopened = unopened_mark and "未开通" in unopened_mark.get_text(strip=True)
                    
                    if line_link:
                        line_name = line_link.get_text(strip=True)
                        if line_name:
                            # Filter metro-related lines
                            is_metro_line = any(keyword in line_name for keyword in 
                                              ["号线", "地铁", "轨道", "城际", "有轨电车", "无轨电车", "轻轨", "APM", "线", "环"])
                            
                            if is_metro_line:
                                if is_unopened:
                                    unopened_lines.append(line_name)
                                    print(f"{city_name} skipping unopened line: {line_name}")
                                else:
                                    metro_lines.append(line_name)
                                    print(f"{city_name} adding operational line: {line_name}")
                
                print(f"{city_name} metro line statistics - Total operational: {len(metro_lines)}, Unopened: {len(unopened_lines)}")
            
        except Exception as e:
            print(f"{city_name} failed to get metro lines: {e}")
        
        return metro_lines
    
    def save_city_data(self, city_name, route_data_list):
        """
        Save route data for a specific city
        
        Args:
            city_name (str): City name
            route_data_list (list): List of route data dictionaries
        """
        if not route_data_list:
            return
        
        # Use actual city English name from first route
        first_route = route_data_list[0]
        city_name_en = first_route.get('city_name_en', chinese_to_english(city_name))
        
        # Create city directories
        route_dir = os.path.join(self.output_dir, "metro_routes", city_name_en)
        stop_dir = os.path.join(self.output_dir, "metro_stops", city_name_en)
        enhanced_dir = os.path.join(self.output_dir, "enhanced_data", city_name_en)
        
        for directory in [route_dir, stop_dir, enhanced_dir]:
            os.makedirs(directory, exist_ok=True)
        
        # Save enhanced data
        enhanced_file = os.path.join(enhanced_dir, f"{city_name_en}_metro_enhanced.csv")
        
        # Check existing data
        existing_route_ids = set()
        if os.path.exists(enhanced_file):
            try:
                df = pd.read_csv(enhanced_file, encoding='utf-8')
                if 'route_id' in df.columns:
                    existing_route_ids = set(df['route_id'].dropna().astype(str))
            except Exception as e:
                print(f"Error reading existing enhanced file: {e}")
        
        # Filter new routes
        new_routes = [route for route in route_data_list if route['route_id'] not in existing_route_ids]
        
        if new_routes:
            # Save enhanced data (append mode)
            enhanced_headers = [
                'route_name_cn', 'route_name_en', 'route_id', 'city_code', 'route_type',
                'company_cn', 'company_en', 'start_stop_cn', 'start_stop_en',
                'end_stop_cn', 'end_stop_en', 'distance', 'start_time', 'end_time',
                'timedesc', 'loop', 'status', 'basic_price', 'total_price',
                'polyline', 'metro_stops', 'total_stops', 'city_name_cn', 'city_name_en'
            ]
            
            mode = 'a' if existing_route_ids else 'w'
            with open(enhanced_file, mode, newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                if mode == 'w':
                    writer.writerow(enhanced_headers)
                
                for route in new_routes:
                    row = [
                        route.get(field, '') if field not in ['polyline', 'metro_stops'] 
                        else json.dumps(route.get(field, []))
                        for field in enhanced_headers
                    ]
                    writer.writerow(row)
            
            # Save individual route and stop files
            for route in new_routes:
                self._save_route_files(route, route_dir, stop_dir)
            
            print(f"Saved {len(new_routes)} new routes for {city_name} ({city_name_en})")
        else:
            print(f"No new routes to save for {city_name}")
    
    def _save_route_files(self, route_data, route_dir, stop_dir):
        """
        Save individual route and stop files
        
        Args:
            route_data (dict): Route data
            route_dir (str): Route directory path
            stop_dir (str): Stop directory path
        """
        route_name_en = route_data['route_name_en']
        city_name_en = route_data['city_name_en']
        
        # Save route geometry file
        route_filename = f"{city_name_en}_{route_name_en}_route.csv"
        route_file_path = os.path.join(route_dir, route_filename)
        
        with open(route_file_path, "w", newline="", encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["name_cn", "name_en", "longitude", "latitude", "sequence", "route_id"])
            
            for idx, coord in enumerate(route_data["polyline"]):
                if len(coord) >= 2:
                    # Convert coordinates from GCJ02 to WGS84
                    coord_wgs84 = transform.gcj02_to_wgs84(float(coord[0]), float(coord[1]))
                    writer.writerow([
                        route_data["route_name_cn"],
                        route_data["route_name_en"],
                        str(coord_wgs84[0]),
                        str(coord_wgs84[1]),
                        idx,
                        route_data["route_id"]
                    ])
        
        # Save stops file
        stop_filename = f"{city_name_en}_{route_name_en}_stops.csv"
        stop_file_path = os.path.join(stop_dir, stop_filename)
        
        with open(stop_file_path, "w", newline="", encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                "name_cn", "name_en", "stop_id", "stop_unique_id",
                "longitude", "latitude", "sequence",
                "route_cn", "route_en", "route_id", "city_code",
                "city_cn", "city_en"
            ])
            
            for stop in route_data["metro_stops"]:
                if stop.get("location"):
                    coords = stop["location"].split(",")
                    if len(coords) >= 2:
                        coord_wgs84 = transform.gcj02_to_wgs84(float(coords[0]), float(coords[1]))
                        writer.writerow([
                            stop["name"],
                            stop["name_en"],
                            stop["id"],
                            stop["stop_unique_id"],
                            str(coord_wgs84[0]),
                            str(coord_wgs84[1]),
                            stop.get("sequence", 0),
                            route_data["route_name_cn"],
                            route_data["route_name_en"],
                            route_data["route_id"],
                            route_data["city_code"],
                            route_data["city_name_cn"],
                            route_data["city_name_en"]
                        ])
    
    def crawl_city_data(self, city_name, metro_cities):
        """
        Crawl all metro data for a specific city
        
        Args:
            city_name (str): Target city name
            metro_cities (dict): City mapping dictionary
        """
        print(f"Starting metro data crawl for city: {city_name}")
        
        # Find city code
        city_code = None
        for code, name in metro_cities.items():
            if name == city_name:
                city_code = code
                break
        
        if not city_code:
            print(f"{city_name} city code not found")
            return
        
        # Get metro line list
        metro_lines = self.get_metro_lines_from_web(city_code, metro_cities)
        
        if not metro_lines:
            print(f"{city_name} no operational metro lines found")
            return
        
        print(f"{city_name} found {len(metro_lines)} operational metro lines")
        
        # Crawl data for each line
        all_route_data = []
        
        for line in metro_lines:
            try:
                route_data_list = self.get_metro_route_data(city_name, line)
                all_route_data.extend(route_data_list)
                time.sleep(0.5)  # Rate limiting
            except Exception as e:
                print(f"Failed to process line {line}: {e}")
                continue
        
        # Save collected data
        if all_route_data:
            self.save_city_data(city_name, all_route_data)
            print(f"Completed crawling for {city_name}: {len(all_route_data)} routes processed")
        else:
            print(f"No valid data collected for {city_name}")


def main():
    """Main execution function for metro data crawling"""
    print("Starting Metro Route Data Crawler")
    print("Features: Operational line filtering, coordinate conversion, enhanced data extraction")
    print("Translation: Azure Translation API for Chinese to English conversion")
    
    # Set up paths
    current_dir = os.path.dirname(os.path.abspath(__file__))
    city_list_path = os.path.join(current_dir, "..", "city_list", "metro_city_list_split.csv")
    output_dir = os.path.join(current_dir, "..", "dataset", "metro")
    logs_dir = os.path.join(current_dir, "..", "logs")
    
    # Ensure directories exist
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(logs_dir, exist_ok=True)
    
    # Initialize crawler
    crawler = MetroDataCrawler(output_dir=output_dir)
    
    # Load city mappings
    metro_cities = crawler.load_metro_cities_from_csv(city_list_path)
    
    if not metro_cities:
        print(f"Failed to load city mappings from {city_list_path}")
        return
    
    print(f"Loaded {len(metro_cities)} cities for processing")
    print(f"Allowed metro types: {ALLOWED_METRO_TYPES}")
    print(f"Using Azure Translation API: {AZURE_TRANSLATOR_ENDPOINT}")
    
    # Process each city
    cities = list(metro_cities.values())
    
    start_time = time.time()
    for city_name in cities:
        try:
            print(f"\nProcessing city: {city_name}")
            crawler.crawl_city_data(city_name, metro_cities)
            
        except Exception as e:
            print(f"Failed to process {city_name}: {e}")
            continue
    
    # Save processing log
    processing_time = time.time() - start_time
    log_filename = os.path.join(logs_dir, f"metro_azure_crawling_log_{int(time.time())}.log")
    with open(log_filename, "w", encoding='utf-8') as f:
        f.write(f"=== Metro Data Processing Record (Azure Translation Enhanced) ===\n")
        f.write(f"Processing time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Duration: {processing_time:.2f} seconds\n")
        f.write(f"City list file: {city_list_path}\n")
        f.write(f"Output directory: {output_dir}\n")
        f.write(f"Total cities: {len(metro_cities)}\n")
        f.write(f"Translation API: Azure Cognitive Services Translator\n")
        f.write(f"Translation cache entries: {len(translation_cache)}\n")
        f.write(f"Allowed metro types: {ALLOWED_METRO_TYPES}\n")
        f.write(f"Features: Operational line filtering, coordinate conversion, Azure translation\n")
    
    # Save translation cache
    cache_filename = os.path.join(logs_dir, f"metro_translation_cache_{int(time.time())}.json")
    with open(cache_filename, "w", encoding='utf-8') as f:
        json.dump(translation_cache, f, ensure_ascii=False, indent=2)
    
    print("Metro route data crawling completed successfully")
    print(f"Output directory: {output_dir}")
    print(f"Processing log: {log_filename}")
    print(f"Translation cache: {cache_filename}")
    print("Data structure:")
    print("  metro_routes/city_en/: Route geometry data by city")
    print("  metro_stops/city_en/: Stop data by city")
    print("  enhanced_data/city_en/: Enhanced route data with operational info")
    print(f"Translation cache entries: {len(translation_cache)}")


if __name__ == "__main__":
    main()