#!/usr/bin/env python3
"""
Enhanced Bus Route Data Crawler

This module provides a comprehensive solution for collecting bus route data from 
Chinese mapping APIs and web sources. It features robust error handling, 
incremental processing, and enhanced data fields for urban transportation analysis.

Key Features:
    - Retrieves route geometries, stop locations, and operational information
    - Supports incremental processing to avoid duplicate data collection
    - Includes operational details (schedule, pricing, company information)
    - Robust network handling with retry mechanisms
    - Coordinate transformation from GCJ02 to WGS84
    - Multi-language support (Chinese and English fields)

Dependencies:
    - requests: HTTP client library
    - pandas: Data manipulation and analysis
    - BeautifulSoup4: HTML parsing
    - transform: Coordinate conversion module
    - xpinyin: Chinese to pinyin conversion

Input:
    - City list CSV file with city names and codes
    - AMap API key for geocoding services

Output:
    - Enhanced CSV files with comprehensive route data per city
    - Route geometries and stop information in WGS84 coordinates
    - Operational metadata (schedules, pricing, company info)

Author: Urban Transportation Research Team
License: MIT
"""

import os
import csv
import json
import time
import random
import hashlib
import logging
import traceback
from pathlib import Path
from urllib.parse import quote
from collections import defaultdict

import requests
import pandas as pd
from bs4 import BeautifulSoup
from xpinyin import Pinyin
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Third-party coordinate transformation module
import transform

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bus_crawler.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class BusDataCrawler:
    """
    Enhanced bus route data crawler for Chinese cities
    
    This class provides comprehensive functionality for collecting bus transportation
    data including route geometries, stop locations, operational schedules, and
    pricing information from Chinese mapping services.
    
    Features:
        - Robust network handling with exponential backoff retry
        - Incremental processing to avoid duplicate data collection
        - Multi-language field support (Chinese and English)
        - Coordinate transformation from GCJ02 to WGS84
        - Enhanced operational metadata collection
    """
    
    def __init__(self, api_key="Your Amap Key", output_dir=None):
        """
        Initialize the enhanced bus data crawler
        
        Args:
            api_key (str): AMap API key for geocoding services
            output_dir (str): Output directory for collected data
        """
        self.api_key = api_key
        self.session = self._create_robust_session()
        self.pinyin_converter = Pinyin()
        
        # Set up output directory structure
        if output_dir is None:
            current_dir = Path(__file__).parent
            output_dir = current_dir.parent / "dataset" / "bus"
        
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache for city code mappings
        self._city_mapping_cache = None
        
        logger.info(f"Enhanced Bus Data Crawler initialized - Output: {self.output_dir}")
    
    def _create_robust_session(self):
        """
        Create HTTP session with comprehensive retry strategy and connection pooling
        
        Returns:
            requests.Session: Configured session with retry mechanisms
        """
        session = requests.Session()
        
        # Configure retry strategy with exponential backoff
        retry_strategy = Retry(
            total=5,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        
        # Configure HTTP adapter with connection pooling
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=20,
            pool_block=False
        )
        
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def _get_random_headers(self):
        """
        Generate randomized request headers to simulate different browsers
        
        Returns:
            dict: HTTP headers with randomized User-Agent
        """
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15'
        ]
        
        headers = {
            'User-Agent': random.choice(user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
            'DNT': '1'
        }
        
        return headers
    
    def _chinese_to_pinyin(self, text):
        """
        Convert Chinese text to pinyin for English field generation
        
        Args:
            text (str): Chinese text to convert
            
        Returns:
            str: Pinyin representation of the text
        """
        if not text or not isinstance(text, str):
            return ""
        
        # Clean text, preserving parentheses but removing special characters
        import re
        cleaned_text = re.sub(r'[^\u4e00-\u9fff\w\(\)（）]', '', text)
        return self.pinyin_converter.get_pinyin(cleaned_text).replace('-', '_').lower()
    
    def _generate_stop_id(self, name, location):
        """
        Generate unique identifier for bus stops
        
        Args:
            name (str): Stop name
            location (str): Stop location coordinates
            
        Returns:
            str: Unique stop identifier
        """
        combined = f"{name}_{location}"
        return hashlib.md5(combined.encode('utf-8')).hexdigest()[:12]
    
    def load_city_mapping(self):
        """
        Load city code mapping from CSV configuration file
        
        Returns:
            dict: Mapping of city codes to city names
        """
        if self._city_mapping_cache is not None:
            return self._city_mapping_cache
        
        current_dir = Path(__file__).parent
        mapping_file = current_dir.parent / "city_list" / "AMap_adcode_citycode.csv"
        
        city_mapping = {}
        
        try:
            if not mapping_file.exists():
                logger.warning(f"City mapping file not found: {mapping_file}")
                return city_mapping
            
            logger.info(f"Loading city mapping: {mapping_file}")
            
            df = pd.read_csv(mapping_file, encoding='utf-8')
            
            if '中文名' not in df.columns or 'citycode' not in df.columns:
                logger.error("CSV file missing required columns (中文名, citycode)")
                return city_mapping
            
            processed_count = 0
            for _, row in df.iterrows():
                citycode = str(row['citycode']).strip()
                chinese_name = str(row['中文名']).strip()
                
                if citycode and citycode not in ['nan', '\\N', 'None']:
                    clean_city_name = self._clean_city_name(chinese_name)
                    if clean_city_name:
                        city_mapping[citycode] = clean_city_name
                        processed_count += 1
            
            logger.info(f"Successfully loaded {processed_count} city code mappings")
            self._city_mapping_cache = city_mapping
            
        except Exception as e:
            logger.error(f"Failed to load city mapping file: {e}")
            self._city_mapping_cache = {}
        
        return self._city_mapping_cache
    
    def _clean_city_name(self, city_name):
        """
        Clean city name by removing administrative suffixes
        
        Args:
            city_name (str): Original city name
            
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
        
        # Handle special administrative regions
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
        Retrieve city name using city code from mapping table
        
        Args:
            city_code (str): City code to lookup
            
        Returns:
            str: Corresponding city name
        """
        if not city_code:
            return "Unknown City"
        
        city_code = str(city_code).strip()
        city_mapping = self.load_city_mapping()
        
        city_name = city_mapping.get(city_code)
        
        if city_name:
            return city_name
        
        # Try alternative codes (with/without leading zeros)
        alternative_codes = []
        if city_code.startswith('0'):
            alternative_codes.append(city_code.lstrip('0'))
        elif not city_code.startswith('0') and len(city_code) <= 3:
            alternative_codes.append('0' + city_code)
        
        for alt_code in alternative_codes:
            alt_city = city_mapping.get(alt_code)
            if alt_city:
                logger.info(f"Found alternative city code mapping: {city_code} -> {alt_code} -> {alt_city}")
                return alt_city
        
        logger.warning(f"City code {city_code} not found in mapping")
        return f"City{city_code}"
    
    def get_bus_route_data(self, city_name, route_name):
        """
        Retrieve comprehensive bus route data from AMap API with enhanced retry logic
        
        Args:
            city_name (str): Target city name
            route_name (str): Bus route identifier
            
        Returns:
            list: List of processed route data dictionaries with enhanced fields
        """
        url = quote(
            f"https://restapi.amap.com/v3/bus/linename?s=rsv3&extensions=all&key={self.api_key}"
            f"&output=json&city={city_name}&offset=0&keywords={route_name}&platform=JS",
            safe=":/?&="
        )
        
        max_retries = 5
        message_list = []
        
        for attempt in range(max_retries):
            try:
                headers = self._get_random_headers()
                headers.update({
                    'Accept': 'application/json, text/javascript, */*; q=0.01',
                    'Referer': 'https://lbs.amap.com/',
                })
                
                response = self.session.get(url, timeout=20, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "1" and data.get("buslines"):
                        buslines_list = data["buslines"]
                        
                        for buslines in buslines_list:
                            # Process route polyline coordinates
                            polyline = buslines.get("polyline", "")
                            coordinates = []
                            if polyline:
                                coords = polyline.split(";")
                                coordinates = [
                                    p.split(",") for p in coords if "," in p
                                ]
                            
                            # Process enhanced bus stop data
                            enhanced_busstops = []
                            for stop in buslines.get("busstops", []):
                                stop_name_pinyin = self._chinese_to_pinyin(stop.get("name", ""))
                                enhanced_stop = {
                                    "name": stop.get("name", ""),
                                    "name_en": stop_name_pinyin,
                                    "id": stop.get("id", ""),
                                    "stop_unique_id": stop.get("id", ""),
                                    "location": stop.get("location", ""),
                                    "sequence": stop.get("sequence", 0)
                                }
                                enhanced_busstops.append(enhanced_stop)
                            
                            # Generate English route name
                            route_name_pinyin = self._chinese_to_pinyin(buslines.get("name", ""))
                            
                            # Get city information using enhanced mapping
                            city_code = buslines.get("citycode", "")
                            city_name_cn = self.get_city_name_by_code(city_code)
                            city_name_en = self._chinese_to_pinyin(city_name_cn)
                            
                            # Extract operational information
                            route_data = {
                                'route_name_cn': buslines.get("name", ""),
                                'route_name_en': route_name_pinyin,
                                "route_id": buslines.get("id", ""),
                                "city_code": city_code,
                                "route_type": buslines.get("type", ""),
                                "company_cn": buslines.get("company", ""),
                                "company_en": self._chinese_to_pinyin(buslines.get("company", "")),
                                "start_stop_cn": buslines.get("start_stop", ""),
                                "start_stop_en": self._chinese_to_pinyin(buslines.get("start_stop", "")),
                                "end_stop_cn": buslines.get("end_stop", ""),
                                "end_stop_en": self._chinese_to_pinyin(buslines.get("end_stop", "")),
                                "distance": buslines.get("distance", ""),
                                # Enhanced operational fields
                                "start_time": buslines.get("start_time", ""),
                                "end_time": buslines.get("end_time", ""),
                                "timedesc": buslines.get("timedesc", ""),
                                "loop": buslines.get("loop", ""),
                                "status": buslines.get("status", ""),
                                "basic_price": buslines.get("basic_price", ""),
                                "total_price": buslines.get("total_price", ""),
                                # Geometry and stops
                                'coordinates': coordinates,
                                'bus_stops': enhanced_busstops,
                                'total_stops': len(enhanced_busstops),
                                'city_name_cn': city_name_cn,
                                'city_name_en': city_name_en
                            }
                            
                            message_list.append(route_data)
                    
                    return message_list
                else:
                    logger.warning(f"Attempt {attempt + 1}: HTTP {response.status_code} for {city_name} {route_name}")
                    
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError,
                    requests.exceptions.RequestException) as e:
                wait_time = 2 ** attempt + random.uniform(0, 1)
                logger.warning(f"Attempt {attempt + 1}/{max_retries} failed ({city_name} {route_name}): {type(e).__name__}")
                if attempt < max_retries - 1:
                    logger.info(f"Waiting {wait_time:.2f} seconds before retry...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"{city_name} {route_name} failed after all retries")
                    
            except Exception as e:
                logger.error(f"{city_name} {route_name} failed with error: {e}")
                break
        
        return message_list
    
    def get_city_route_list(self, city_code):
        """
        Retrieve list of bus routes for a city from 8684 web source
        
        Args:
            city_code (str): City code for route lookup
            
        Returns:
            list: List of route names
        """
        bus_routes = []
        
        try:
            base_url = quote(f"https://{city_code}.8684.cn", safe=":/?&=")
            url = base_url + "/list1"
            
            max_retries = 8
            first_page_data = None
            
            # Get first page with retry logic
            for attempt in range(max_retries):
                try:
                    headers = self._get_random_headers()
                    logger.info(f"Attempting to get route list page (attempt {attempt + 1}/{max_retries}): {url}")
                    
                    response = self.session.get(url, timeout=30, headers=headers)
                    
                    if response.status_code == 200:
                        first_page_data = response.text
                        logger.info("Successfully retrieved route list page")
                        break
                    else:
                        logger.warning(f"Failed to get route list page, status code: {response.status_code}")
                        
                except (requests.exceptions.Timeout, requests.exceptions.ConnectionError,
                        requests.exceptions.SSLError) as e:
                    wait_time = min(60, 3 ** attempt + random.uniform(0, 2))
                    logger.warning(f"Network error (attempt {attempt + 1}): {type(e).__name__}")
                    if attempt < max_retries - 1:
                        logger.info(f"Waiting {wait_time:.2f} seconds before retry...")
                        time.sleep(wait_time)
                    else:
                        logger.error(f"Failed to get route list after all retries")
                        return bus_routes
                        
                except Exception as e:
                    logger.error(f"Other error: {e}")
                    break
            
            if not first_page_data:
                logger.error(f"Unable to get route list data for city {city_code}")
                return bus_routes
            
            # Parse page structure
            html = BeautifulSoup(first_page_data, "html.parser")
            div = html.find("div", {"class": "tooltip-body cc-content-tooltip"})
            if not div:
                logger.error(f"Page structure changed for city {city_code}")
                return bus_routes
                
            div = div.find("div", {"class": "tooltip-inner"})
            if not div:
                logger.error(f"Inner page structure changed for city {city_code}")
                return bus_routes
                
            # Extract route pages
            route_pages = []
            for link in div:
                if hasattr(link, 'get') and link.get("href"):
                    route_pages.append(link.get("href"))
            route_pages = [i for i in route_pages if i]
            
            logger.info(f"Found {len(route_pages)} route pages for city {city_code}")
            
            # Process each page
            failed_pages = []
            successful_pages = 0
            
            for page_index, page_path in enumerate(route_pages):
                url = base_url + page_path
                page_success = False
                
                for attempt in range(6):
                    try:
                        headers = self._get_random_headers()
                        logger.info(f"Processing page {page_index + 1}/{len(route_pages)} ({page_path}) - attempt {attempt + 1}")
                        
                        response = self.session.get(url, timeout=30, headers=headers)
                        
                        if response.status_code == 200:
                            data = response.text
                            html = BeautifulSoup(data, "html.parser")
                            div = html.find("div", {"class": "list clearfix"})
                            
                            if div:
                                page_route_count = 0
                                for link in div:
                                    if hasattr(link, 'get_text'):
                                        route_text = link.get_text().strip()
                                        if route_text:
                                            bus_routes.append(route_text)
                                            page_route_count += 1
                                
                                logger.info(f"Page {page_path} successfully retrieved {page_route_count} routes")
                                successful_pages += 1
                                page_success = True
                                break
                            else:
                                logger.warning(f"Page {page_path} structure parsing failed")
                        else:
                            logger.warning(f"Page {page_path} HTTP error: {response.status_code}")
                            
                    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError,
                            requests.exceptions.SSLError) as e:
                        wait_time = min(30, 2 ** attempt + random.uniform(0, 2))
                        logger.warning(f"Page {page_path} network error: {type(e).__name__}")
                        if attempt < 5:
                            logger.info(f"Waiting {wait_time:.2f} seconds before retry...")
                            time.sleep(wait_time)
                            
                    except Exception as e:
                        logger.error(f"Page {page_path} other error: {e}")
                        break
                
                if not page_success:
                    failed_pages.append(page_path)
                    logger.error(f"Page {page_path} finally failed")
            
            logger.info(f"Page processing completed: successful {successful_pages}/{len(route_pages)}")
            if failed_pages:
                logger.warning(f"Failed pages: {failed_pages}")
            logger.info(f"Total routes retrieved: {len(bus_routes)}")

        except Exception as e:
            logger.error(f"Overall processing failed for city {city_code}: {e}")
        
        return bus_routes
    
    def merge_duplicate_stops(self, stops_data):
        """
        Merge duplicate bus stops by calculating geometric center for same-named stops
        
        Args:
            stops_data (list): List of stop data dictionaries
            
        Returns:
            list: Merged stop data with duplicates resolved
        """
        stop_groups = defaultdict(list)
        
        for stop in stops_data:
            stop_groups[stop['name']].append(stop)
        
        merged_stops = []
        for name, group in stop_groups.items():
            if len(group) == 1:
                merged_stops.append(group[0])
            else:
                # Calculate geometric center
                total_lon = sum(float(stop['location'].split(',')[0]) for stop in group)
                total_lat = sum(float(stop['location'].split(',')[1]) for stop in group)
                avg_lon = total_lon / len(group)
                avg_lat = total_lat / len(group)
                
                merged_stop = group[0].copy()
                merged_stop['location'] = f"{avg_lon},{avg_lat}"
                if 'stop_unique_id' not in merged_stop or not merged_stop['stop_unique_id']:
                    merged_stop['stop_unique_id'] = self._generate_stop_id(name, merged_stop['location'])
                merged_stops.append(merged_stop)
        
        return merged_stops
    
    def save_enhanced_data(self, city_name, route_data_list):
        """
        Save comprehensive route data to structured CSV files
        
        Args:
            city_name (str): Target city name
            route_data_list (list): List of route data dictionaries
        """
        city_name_en = self._chinese_to_pinyin(city_name)
        
        # Create directory structure
        bus_routes_dir = self.output_dir / "bus_routes" / city_name_en
        bus_stops_dir = self.output_dir / "bus_stops" / city_name_en
        enhanced_data_dir = self.output_dir / "enhanced_data" / city_name_en
        
        for directory in [bus_routes_dir, bus_stops_dir, enhanced_data_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Enhanced CSV headers
        enhanced_headers = [
            'route_name_cn', 'route_name_en', 'route_id', 'city_code', 'route_type',
            'company_cn', 'company_en', 'start_stop_cn', 'start_stop_en',
            'end_stop_cn', 'end_stop_en', 'distance', 'start_time', 'end_time',
            'timedesc', 'loop', 'status', 'basic_price', 'total_price',
            'coordinates', 'bus_stops', 'total_stops', 'city_name_cn', 'city_name_en'
        ]
        
        enhanced_file = enhanced_data_dir / f"{city_name_en}_bus_enhanced.csv"
        
        # Load existing data
        existing_route_ids = set()
        if enhanced_file.exists():
            try:
                df = pd.read_csv(enhanced_file, encoding='utf-8')
                if 'route_id' in df.columns:
                    existing_route_ids = set(df['route_id'].dropna().astype(str))
                    logger.info(f"Found existing enhanced file with {len(existing_route_ids)} processed routes")
            except Exception as e:
                logger.error(f"Failed to read existing enhanced file: {e}")
        
        # Process new route data
        new_enhanced_data = []
        all_stops_data = []
        
        for route_data in route_data_list:
            route_id = str(route_data.get("route_id", ""))
            if route_id in existing_route_ids:
                logger.info(f"Skipping already processed route: {route_id}")
                continue
            
            # Collect stop data
            for stop_data in route_data.get('bus_stops', []):
                all_stops_data.append(stop_data)
            
            # Prepare enhanced data
            enhanced_row_data = {
                'route_name_cn': route_data.get('route_name_cn', ''),
                'route_name_en': route_data.get('route_name_en', ''),
                'route_id': route_data.get('route_id', ''),
                'city_code': route_data.get('city_code', ''),
                'route_type': route_data.get('route_type', ''),
                'company_cn': route_data.get('company_cn', ''),
                'company_en': route_data.get('company_en', ''),
                'start_stop_cn': route_data.get('start_stop_cn', ''),
                'start_stop_en': route_data.get('start_stop_en', ''),
                'end_stop_cn': route_data.get('end_stop_cn', ''),
                'end_stop_en': route_data.get('end_stop_en', ''),
                'distance': route_data.get('distance', ''),
                'start_time': route_data.get('start_time', ''),
                'end_time': route_data.get('end_time', ''),
                'timedesc': route_data.get('timedesc', ''),
                'loop': route_data.get('loop', ''),
                'status': route_data.get('status', ''),
                'basic_price': route_data.get('basic_price', ''),
                'total_price': route_data.get('total_price', ''),
                'coordinates': json.dumps(route_data.get('coordinates', [])),
                'bus_stops': json.dumps(route_data.get('bus_stops', [])),
                'total_stops': route_data.get('total_stops', 0),
                'city_name_cn': route_data.get('city_name_cn', ''),
                'city_name_en': route_data.get('city_name_en', '')
            }
            new_enhanced_data.append(enhanced_row_data)
            
            # Save individual route files
            self._save_individual_route_files(route_data, bus_routes_dir, bus_stops_dir)
        
        # Save enhanced data
        if new_enhanced_data:
            self._append_to_enhanced_file(enhanced_file, new_enhanced_data, enhanced_headers)
            logger.info(f"Saved {len(new_enhanced_data)} new route records")
        
        # Process and save merged stops
        if all_stops_data:
            self._save_merged_stops(all_stops_data, enhanced_data_dir, city_name_en)
    
    def _save_individual_route_files(self, route_data, bus_routes_dir, bus_stops_dir):
        """Save individual route and stop files"""
        route_name_en = route_data.get('route_name_en', '')
        city_name_en = route_data.get('city_name_en', '')
        
        # Save route geometry
        route_filename = f"{city_name_en}_{route_name_en}_route.csv"
        route_file_path = bus_routes_dir / route_filename
        
        if not route_file_path.exists():
            with open(route_file_path, "w", newline="", encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["name_cn", "name_en", "longitude", "latitude", "sequence", "route_id"])
                for idx, coord in enumerate(route_data.get("coordinates", [])):
                    coord_wgs84 = transform.gcj02_to_wgs84(float(coord[0]), float(coord[1]))
                    writer.writerow([
                        route_data.get("route_name_cn", ""),
                        route_name_en,
                        str(coord_wgs84[0]),
                        str(coord_wgs84[1]),
                        idx,
                        route_data.get("route_id", "")
                    ])
        
        # Save stop data
        stop_filename = f"{city_name_en}_{route_name_en}_stops.csv"
        stop_file_path = bus_stops_dir / stop_filename
        
        if not stop_file_path.exists():
            with open(stop_file_path, "w", newline="", encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    "name_cn", "name_en", "stop_id", "stop_unique_id",
                    "longitude", "latitude", "sequence", "route_cn", "route_en",
                    "route_id", "city_code", "city_cn", "city_en"
                ])
                for stop in route_data.get("bus_stops", []):
                    coords = stop["location"].split(",")
                    coord_wgs84 = transform.gcj02_to_wgs84(float(coords[0]), float(coords[1]))
                    writer.writerow([
                        stop["name"], stop["name_en"], stop["id"],
                        stop["stop_unique_id"], str(coord_wgs84[0]),
                        str(coord_wgs84[1]), stop.get("sequence", 0),
                        route_data.get("route_name_cn", ""), route_name_en,
                        route_data.get("route_id", ""), route_data.get("city_code", ""),
                        route_data.get("city_name_cn", ""), city_name_en
                    ])
    
    def _append_to_enhanced_file(self, enhanced_file_path, new_data_list, headers):
        """Append new data to enhanced file"""
        file_exists = enhanced_file_path.exists()
        
        try:
            with open(enhanced_file_path, "a", newline="", encoding='utf-8') as f:
                writer = csv.writer(f)
                
                if not file_exists:
                    writer.writerow(headers)
                
                for data in new_data_list:
                    if isinstance(data, dict):
                        row = [data.get(field, "") for field in headers]
                        writer.writerow(row)
                    else:
                        writer.writerow(data)
            
            logger.info(f"Successfully appended {len(new_data_list)} new records")
            
        except Exception as e:
            logger.error(f"Failed to append data to enhanced file: {e}")
            raise
    
    def _save_merged_stops(self, all_stops_data, enhanced_data_dir, city_name_en):
        """Save merged stop data"""
        merged_stops = self.merge_duplicate_stops(all_stops_data)
        merged_stops_file = enhanced_data_dir / f"{city_name_en}_bus_stations_enhanced.csv"
        
        existing_merged_stops = []
        if merged_stops_file.exists():
            try:
                existing_df = pd.read_csv(merged_stops_file, encoding='utf-8')
                existing_merged_stops = existing_df.to_dict('records')
                logger.info(f"Found existing merged stops file with {len(existing_merged_stops)} stops")
            except Exception as e:
                logger.error(f"Failed to read existing merged stops file: {e}")
        
        all_merged_stops = existing_merged_stops.copy()
        existing_stop_names = set([stop.get('name_cn', '') for stop in existing_merged_stops])
        
        new_stops_count = 0
        for stop in merged_stops:
            if stop['name'] not in existing_stop_names:
                coords = stop["location"].split(",")
                coord_wgs84 = transform.gcj02_to_wgs84(float(coords[0]), float(coords[1]))
                stop_record = {
                    "name_cn": stop["name"],
                    "name_en": stop["name_en"],
                    "stop_unique_id": stop["stop_unique_id"],
                    "longitude": str(coord_wgs84[0]),
                    "latitude": str(coord_wgs84[1])
                }
                all_merged_stops.append(stop_record)
                new_stops_count += 1
        
        try:
            with open(merged_stops_file, "w", newline="", encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["name_cn", "name_en", "stop_unique_id", "longitude", "latitude"])
                for stop in all_merged_stops:
                    writer.writerow([
                        stop.get("name_cn", ""), stop.get("name_en", ""),
                        stop.get("stop_unique_id", ""), stop.get("longitude", ""),
                        stop.get("latitude", "")
                    ])
            logger.info(f"Merged stops file updated, added {new_stops_count} new stops")
        except Exception as e:
            logger.error(f"Failed to save merged stops file: {e}")
    
    def crawl_city_data(self, city_name, city_code=None):
        """
        Crawl comprehensive bus data for a specific city
        
        Args:
            city_name (str): Target city name
            city_code (str): Optional city code for route lookup
        """
        logger.info(f"Starting comprehensive data crawl for city: {city_name}")
        
        if city_code:
            # Get route list
            routes = self.get_city_route_list(city_code)
            
            if not routes:
                logger.warning(f"No routes found for city {city_name}")
                return
            
            logger.info(f"Found {len(routes)} routes for {city_name}")
            
            # Process routes
            processed_count = 0
            all_route_data = []
            
            for route in routes:
                try:
                    # Clean route name
                    import re
                    cleaned_route = re.sub(r'[\-\/\.\:\↔\⇄\⇌\㳇\㙟]', '', route)
                    cleaned_route = re.sub(r'\s+', ' ', cleaned_route).strip()
                    
                    route_data_list = self.get_bus_route_data(city_name, cleaned_route)
                    
                    if route_data_list:
                        all_route_data.extend(route_data_list)
                        processed_count += len(route_data_list)
                        logger.info(f"Successfully processed route: {cleaned_route}")
                    
                    time.sleep(0.5)  # Rate limiting
                    
                except Exception as e:
                    logger.error(f"Failed to process route {route}: {e}")
                    continue
            
            # Save all collected data
            if all_route_data:
                self.save_enhanced_data(city_name, all_route_data)
                logger.info(f"Completed crawling for {city_name}: {processed_count} routes processed")
            else:
                logger.warning(f"No valid route data collected for {city_name}")
        else:
            logger.warning(f"No city code provided for {city_name}, skipping route list extraction")


def main():
    """
    Main execution function for comprehensive bus data crawling
    
    This function orchestrates the entire data collection process, including:
    - Loading city configurations
    - Processing each city with incremental data collection
    - Handling errors and logging
    - Generating comprehensive output files
    """
    logger.info("Starting Enhanced Bus Route Data Crawler")
    
    # Load city configuration
    current_dir = Path(__file__).parent
    city_list_file = current_dir.parent / "city_list" / "bus_city_list_split.csv"
    
    if not city_list_file.exists():
        logger.error(f"City list file not found: {city_list_file}")
        return
    
    # Read city mappings
    try:
        df = pd.read_csv(city_list_file, encoding='utf-8')
        
        if 'city_simple' not in df.columns or 'city_cn' not in df.columns:
            logger.error("CSV file missing required columns (city_simple, city_cn)")
            return
        
        cities = df.to_dict('records')
        logger.info(f"Loaded {len(cities)} cities from configuration")
        
    except Exception as e:
        logger.error(f"Failed to load city list: {e}")
        return
    
    # Initialize crawler
    crawler = BusDataCrawler()
    
    # Process cities with enhanced logging
    processed_cities = 0
    failed_cities = 0
    
    logger.info("=== Enhanced Processing Mode ===")
    logger.info("- Incremental processing (skips already processed routes)")
    logger.info("- Enhanced operational metadata collection")
    logger.info("- Robust network handling with retry mechanisms")
    logger.info("- Multi-language field support")
    logger.info("- Coordinate transformation to WGS84")
    logger.info("=" * 60)
    
    for city_info in cities:
        city_name = city_info.get('city_cn', '')
        city_code = city_info.get('city_simple', '')
        
        if city_name and city_code:
            try:
                logger.info(f"\nProcessing city: {city_name} ({city_code})")
                crawler.crawl_city_data(city_name, city_code)
                processed_cities += 1
                logger.info(f"Successfully completed processing for {city_name}")
                
            except Exception as e:
                logger.error(f"Failed to crawl data for {city_name}: {e}")
                failed_cities += 1
                continue
        else:
            logger.warning(f"Incomplete city information: {city_info}")
            failed_cities += 1
    
    # Final summary
    logger.info("\n" + "=" * 60)
    logger.info("CRAWLING SUMMARY")
    logger.info(f"Total cities processed: {processed_cities}")
    logger.info(f"Failed cities: {failed_cities}")
    logger.info(f"Success rate: {processed_cities/(processed_cities+failed_cities)*100:.1f}%")
    logger.info("Enhanced bus route data crawling completed successfully")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()