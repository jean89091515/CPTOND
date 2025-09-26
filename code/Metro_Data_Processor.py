#!/usr/bin/env python3
"""
Metro Data Processor for Shapefile Generation

This module processes collected metro route and stop data to generate
standardized shapefiles for GIS analysis and visualization. Includes
coordinate validation, deduplication, and Taiwan coordinate correction.

Dependencies:
    - pandas
    - geopandas
    - shapely
    - transform (coordinate conversion module)

Input:
    - Metro route CSV files organized by city
    - Metro stop CSV files organized by city  
    - Enhanced data CSV files with operational information

Output:
    - Metro routes shapefile (LineString geometries)
    - Metro stops shapefile (Point geometries)
    - Processing summary report

Author: Urban Transportation Research Team
License: MIT
"""

import os
import geopandas as gpd
from shapely.geometry import Point, LineString
import pandas as pd
import json
import transform
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MetroDataProcessor:
    """
    Metro data processor for shapefile generation
    
    Converts collected CSV data into GIS-ready formats with:
    - Route geometries as LineString features
    - Stop locations as Point features
    - Enhanced operational information
    - Coordinate validation and Taiwan correction
    """
    
    def __init__(self, data_path=None):
        """
        Initialize the metro data processor
        
        Args:
            data_path (str): Path to input data directory
        """
        if data_path is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            data_path = os.path.join(current_dir, "..", "dataset", "metro")
        
        self.data_path = data_path
        self.metro_routes_path = os.path.join(data_path, "metro_routes")
        self.metro_stops_path = os.path.join(data_path, "metro_stops")
        self.enhanced_data_path = os.path.join(data_path, "enhanced_data")
        self.output_shp_path = os.path.join(data_path, "shapefiles")
        
        # Create output directory
        os.makedirs(self.output_shp_path, exist_ok=True)
        
        self.stats = {
            'cities_processed': 0,
            'total_routes': 0,
            'total_stops': 0,
            'invalid_coordinates': 0,
            'taiwan_coords_fixed': 0,
            'duplicated_routes_removed': 0,
            'duplicated_stops_removed': 0
        }
        
        logger.info(f"Metro Data Processor initialized")
        logger.info(f"Input path: {self.data_path}")
        logger.info(f"Output path: {self.output_shp_path}")
    
    def is_taiwan_province(self, city_cn):
        """
        Check if the city belongs to Taiwan Province
        
        Args:
            city_cn (str): Chinese city name
            
        Returns:
            bool: True if Taiwan Province
        """
        return city_cn and "台湾" in str(city_cn)
    
    def fix_taiwan_coordinates(self, lon, lat, city_cn):
        """
        Fix Taiwan coordinate system issues
        
        Taiwan metro stations were incorrectly converted from WGS84 to GCJ02,
        need to convert back using wgs84_to_gcj02
        
        Args:
            lon (float): Longitude
            lat (float): Latitude  
            city_cn (str): Chinese city name
            
        Returns:
            tuple: (corrected_lon, corrected_lat)
        """
        if self.is_taiwan_province(city_cn):
            try:
                corrected_coords = transform.wgs84_to_gcj02(lon, lat)
                return corrected_coords[0], corrected_coords[1]
            except Exception as e:
                logger.error(f"Taiwan coordinate conversion failed: {e}, using original coordinates")
                return lon, lat
        else:
            return lon, lat
    
    def validate_coordinates(self, lon, lat, city_cn=None):
        """
        Validate coordinate validity with Taiwan correction
        
        Args:
            lon (float): Longitude
            lat (float): Latitude
            city_cn (str): Chinese city name for Taiwan detection
            
        Returns:
            tuple: (is_valid, corrected_lon, corrected_lat)
        """
        try:
            lon, lat = float(lon), float(lat)
            
            # Check WGS84 coordinate bounds
            if -180 <= lon <= 180 and -90 <= lat <= 90:
                # Apply Taiwan coordinate correction if needed
                if city_cn and self.is_taiwan_province(city_cn):
                    lon, lat = self.fix_taiwan_coordinates(lon, lat, city_cn)
                    logger.info(f"Taiwan coordinates corrected: converted to ({lon:.6f}, {lat:.6f})")
                
                # Additional validation for China territory (optional)
                if 73 <= lon <= 135 and 18 <= lat <= 54:
                    return True, lon, lat
                # Accept valid coordinates even if outside China bounds
                return True, lon, lat
                    
            return False, None, None
        except (ValueError, TypeError):
            return False, None, None
    
    def format_city_code(self, city_code):
        """
        Format city code to preserve leading zeros
        
        Args:
            city_code (str/int): Raw city code
            
        Returns:
            str: Formatted city code with leading zeros
        """
        if pd.isna(city_code) or city_code == '' or city_code is None:
            return ''
        
        city_code_str = str(city_code).strip()
        
        # Pad with leading zeros if numeric and less than 3 digits
        if city_code_str.isdigit() and len(city_code_str) < 3:
            city_code_str = city_code_str.zfill(3)
        
        return city_code_str
    
    def get_city_directories(self):
        """
        Get list of all city directories
        
        Returns:
            list: List of city English names
        """
        cities = set()
        
        # Collect cities from different data directories
        for base_path in [self.metro_routes_path, self.metro_stops_path, self.enhanced_data_path]:
            if os.path.exists(base_path):
                for item in os.listdir(base_path):
                    item_path = os.path.join(base_path, item)
                    if os.path.isdir(item_path):
                        cities.add(item)
        
        return list(cities)
    
    def load_enhanced_data_by_city(self):
        """
        Load enhanced data organized by city
        
        Returns:
            dict: Enhanced data indexed by city and route_id
        """
        enhanced_data_by_city = {}
        
        if not os.path.exists(self.enhanced_data_path):
            logger.warning(f"Enhanced data directory not found: {self.enhanced_data_path}")
            return enhanced_data_by_city
        
        cities = self.get_city_directories()
        
        for city_en in cities:
            city_enhanced_path = os.path.join(self.enhanced_data_path, city_en)
            if not os.path.isdir(city_enhanced_path):
                continue
                
            enhanced_data_by_city[city_en] = {}
            
            # Find enhanced files for this city
            enhanced_files = [f for f in os.listdir(city_enhanced_path) if f.endswith('_enhanced.csv')]
            
            for enhanced_file in enhanced_files:
                enhanced_file_path = os.path.join(city_enhanced_path, enhanced_file)
                
                try:
                    logger.info(f"Reading enhanced data file: {enhanced_file} (city: {city_en})")
                    
                    # Define data types to preserve city_code format
                    dtype_dict = {
                        'city_code': str,
                        'route_id': str,
                        'route_name_cn': str,
                        'route_name_en': str,
                        'route_type': str,
                        'company_cn': str,
                        'company_en': str,
                        'start_stop_cn': str,
                        'start_stop_en': str,
                        'end_stop_cn': str,
                        'end_stop_en': str,
                        'distance': str,
                        'start_time': str,
                        'end_time': str,
                        'timedesc': str,
                        'loop': str,
                        'status': str,
                        'basic_price': str,
                        'total_price': str,
                        'city_name_cn': str,
                        'city_name_en': str
                    }
                    
                    df = pd.read_csv(enhanced_file_path, encoding='utf-8', dtype=dtype_dict)
                    
                    # Remove duplicate header rows
                    if len(df) > 0:
                        header_values = df.columns.tolist()
                        mask = ~df.apply(lambda row: row.tolist() == header_values, axis=1)
                        df = df[mask]
                    
                    logger.info(f"Read {len(df)} valid records from {enhanced_file}")
                    
                    for _, row in df.iterrows():
                        route_id = str(row.get('route_id', ''))
                        if route_id and route_id != 'route_id':  # Skip header rows
                            city_code = self.format_city_code(row.get('city_code', ''))
                            
                            enhanced_data_by_city[city_en][route_id] = {
                                'route_name_cn': str(row.get('route_name_cn', '')),
                                'route_name_en': str(row.get('route_name_en', '')),
                                'city_code': city_code,
                                'route_type': str(row.get('route_type', '地铁')),
                                'company_cn': str(row.get('company_cn', '')),
                                'company_en': str(row.get('company_en', '')),
                                'start_stop_cn': str(row.get('start_stop_cn', '')),
                                'start_stop_en': str(row.get('start_stop_en', '')),
                                'end_stop_cn': str(row.get('end_stop_cn', '')),
                                'end_stop_en': str(row.get('end_stop_en', '')),
                                'distance': str(row.get('distance', '0')),
                                'start_time': str(row.get('start_time', '')),
                                'end_time': str(row.get('end_time', '')),
                                'timedesc': str(row.get('timedesc', '')),
                                'loop': str(row.get('loop', '')),
                                'status': str(row.get('status', '')),
                                'basic_price': str(row.get('basic_price', '')),
                                'total_price': str(row.get('total_price', '')),
                                'total_stops': int(row.get('total_stops', 0)) if str(row.get('total_stops', 0)).isdigit() else 0,
                                'city_name_cn': str(row.get('city_name_cn', '')),
                                'city_name_en': str(row.get('city_name_en', ''))
                            }
                            
                except Exception as e:
                    logger.error(f"Failed to read enhanced file {enhanced_file}: {e}")
                    continue
        
        total_routes = sum(len(city_data) for city_data in enhanced_data_by_city.values())
        logger.info(f"Loaded enhanced data for {len(enhanced_data_by_city)} cities, {total_routes} routes")
        
        return enhanced_data_by_city
    
    def process_metro_stops(self):
        """
        Process metro stop data with deduplication and Taiwan coordinate correction
        
        Returns:
            gpd.GeoDataFrame: Processed stops as Point geometries
        """
        logger.info("Starting metro stops processing...")
        logger.info("Deduplication strategy: by name_cn, route_cn, city_cn, sequence combination")
        logger.info("Taiwan coordinate correction: enabled for Taiwan Province metro stations")
        
        all_stops = []
        invalid_coords_count = 0
        taiwan_coords_fixed = 0
        
        if not os.path.exists(self.metro_stops_path):
            logger.warning(f"Metro stops directory not found: {self.metro_stops_path}")
            return None
        
        # Load enhanced data organized by city
        enhanced_data_by_city = self.load_enhanced_data_by_city()
        
        cities = self.get_city_directories()
        
        for city_en in cities:
            city_stops_path = os.path.join(self.metro_stops_path, city_en)
            if not os.path.isdir(city_stops_path):
                continue
            
            logger.info(f"Processing city: {city_en}")
            
            # Get enhanced data for this city
            city_enhanced_data = enhanced_data_by_city.get(city_en, {})
            
            # Process all stop files for this city
            stop_files = [f for f in os.listdir(city_stops_path) if f.endswith('_stops.csv')]
            
            for file in stop_files:
                file_path = os.path.join(city_stops_path, file)
                
                try:
                    # Define data types to preserve string fields
                    dtype_dict = {
                        'city_code': str,
                        'route_id': str,
                        'stop_id': str,
                        'stop_unique_id': str,
                        'name_cn': str,
                        'name_en': str,
                        'route_cn': str,
                        'route_en': str,
                        'city_cn': str,
                        'city_en': str
                    }
                    
                    df = pd.read_csv(file_path, encoding='utf-8', dtype=dtype_dict)
                    
                    # Validate required columns
                    required_cols = ['name_cn', 'name_en', 'longitude', 'latitude']
                    if not all(col in df.columns for col in required_cols):
                        logger.warning(f"File {file} missing required columns, skipping")
                        continue
                    
                    # Process each stop
                    for _, row in df.iterrows():
                        city_cn = str(row.get('city_cn', ''))
                        
                        # Validate and correct coordinates
                        is_valid, lon, lat = self.validate_coordinates(
                            row['longitude'], row['latitude'], city_cn
                        )
                        
                        if is_valid:
                            # Count Taiwan coordinate corrections
                            if self.is_taiwan_province(city_cn):
                                taiwan_coords_fixed += 1
                            
                            # Get route information from enhanced data
                            route_id = str(row.get('route_id', ''))
                            route_info = city_enhanced_data.get(route_id, {})
                            
                            # Process city_code
                            city_code_from_file = row.get('city_code', '')
                            city_code_from_enhanced = route_info.get('city_code', '')
                            city_code = city_code_from_enhanced if city_code_from_enhanced else str(city_code_from_file)
                            city_code = self.format_city_code(city_code)
                            
                            # Preserve stop names with parentheses
                            stop_name_cn = str(row['name_cn'])
                            stop_name_en = str(row['name_en'])
                            
                            stop_data = {
                                'name_cn': stop_name_cn[:80],
                                'name_en': stop_name_en[:80],
                                'stop_id': str(row.get('stop_id', ''))[:20],
                                'route_cn': str(row.get('route_cn', route_info.get('route_name_cn', '')))[:50],
                                'route_en': str(row.get('route_en', route_info.get('route_name_en', '')))[:150],
                                'route_id': route_id[:30],
                                'city_code': city_code[:20],
                                'city_cn': str(row.get('city_cn', route_info.get('city_name_cn', '')))[:30],
                                'city_en': str(row.get('city_en', route_info.get('city_name_en', '')))[:30],
                                'sequence': int(row.get('sequence', 0)),
                                'merged_cnt': 1,  # Initial value for deduplication
                                'geometry': Point(lon, lat)  # Use corrected coordinates
                            }
                            all_stops.append(stop_data)
                        else:
                            invalid_coords_count += 1
                            
                except Exception as e:
                    logger.error(f"Failed to process file {file}: {e}")
                    continue
        
        if not all_stops:
            logger.warning("No valid stop data found")
            return None
        
        # Record counts before deduplication
        original_count = len(all_stops)
        logger.info(f"Stops before deduplication: {original_count}")
        logger.info(f"Taiwan coordinates fixed: {taiwan_coords_fixed}")
        
        # Deduplicate by name_cn, route_cn, city_cn, sequence
        logger.info("Starting deduplication by name_cn, route_cn, city_cn, sequence...")
        
        # Group stops for deduplication
        dedup_groups = {}
        for stop in all_stops:
            dedup_key = f"{stop['name_cn']}|{stop['route_cn']}|{stop['city_cn']}|{stop['sequence']}"
            if dedup_key not in dedup_groups:
                dedup_groups[dedup_key] = []
            dedup_groups[dedup_key].append(stop)
        
        # Create deduplicated stops
        dedup_stops = []
        for key, group in dedup_groups.items():
            # Keep first stop and set merge count
            first_stop = group[0].copy()
            first_stop['merged_cnt'] = len(group)
            dedup_stops.append(first_stop)
        
        # Create GeoDataFrame
        stops_gdf = gpd.GeoDataFrame(dedup_stops, crs="EPSG:4326")
        
        logger.info(f"Stops after deduplication: {len(stops_gdf)}")
        logger.info(f"Duplicates removed: {original_count - len(stops_gdf)}")
        
        # Save to shapefile
        output_file = os.path.join(self.output_shp_path, "metro_stops.shp")
        stops_gdf.to_file(output_file, encoding='utf-8')
        
        # Update statistics
        self.stats['total_stops'] = len(stops_gdf)
        self.stats['duplicated_stops_removed'] = original_count - len(stops_gdf)
        self.stats['invalid_coordinates'] = invalid_coords_count
        self.stats['taiwan_coords_fixed'] = taiwan_coords_fixed
        
        logger.info(f"Metro stops processing complete: {len(stops_gdf)} stops (deduplicated, Taiwan corrected)")
        
        return stops_gdf
    
    def process_metro_routes(self):
        """
        Process metro route data with deduplication and operational information
        
        Returns:
            gpd.GeoDataFrame: Processed routes as LineString geometries
        """
        logger.info("Starting metro routes processing...")
        logger.info("Deduplication strategy: by route_cn and city_cn combination")
        logger.info("Operational info: extracting schedule and pricing data")
        
        all_routes = []
        invalid_routes_count = 0
        
        if not os.path.exists(self.metro_routes_path):
            logger.warning(f"Metro routes directory not found: {self.metro_routes_path}")
            return None
        
        # Load enhanced data organized by city
        enhanced_data_by_city = self.load_enhanced_data_by_city()
        
        cities = self.get_city_directories()
        
        for city_en in cities:
            city_routes_path = os.path.join(self.metro_routes_path, city_en)
            if not os.path.isdir(city_routes_path):
                continue
            
            logger.info(f"Processing city: {city_en}")
            
            # Get enhanced data for this city
            city_enhanced_data = enhanced_data_by_city.get(city_en, {})
            
            # Process all route files for this city
            route_files = [f for f in os.listdir(city_routes_path) if f.endswith('_route.csv')]
            
            for file in route_files:
                file_path = os.path.join(city_routes_path, file)
                
                try:
                    # Define data types
                    dtype_dict = {
                        'route_id': str,
                        'city_code': str,
                        'name_cn': str,
                        'name_en': str
                    }
                    
                    df = pd.read_csv(file_path, encoding='utf-8', dtype=dtype_dict)
                    
                    # Validate required columns
                    required_cols = ['longitude', 'latitude', 'route_id']
                    if not all(col in df.columns for col in required_cols):
                        logger.warning(f"File {file} missing required columns, skipping")
                        continue
                    
                    # Get route_id (should be same for all rows)
                    route_ids = df['route_id'].dropna().unique()
                    if len(route_ids) == 0:
                        logger.warning(f"File {file} has no valid route_id, skipping")
                        continue
                        
                    route_id = str(route_ids[0])
                    
                    # Get enhanced information for this route
                    route_info = city_enhanced_data.get(route_id, {})
                    
                    if not route_info:
                        logger.warning(f"Enhanced data not found for route_id: {route_id}")
                        # Create basic route info from filename
                        base_name = os.path.splitext(file)[0]
                        parts = base_name.replace('_route', '').split('_')
                        metro_line = '_'.join(parts[1:]) if len(parts) > 1 else "unknown"
                        
                        route_info = {
                            'route_name_cn': metro_line,
                            'route_name_en': metro_line,
                            'city_code': '',
                            'route_type': '地铁',
                            'company_cn': '',
                            'company_en': '',
                            'start_stop_cn': '',
                            'start_stop_en': '',
                            'end_stop_cn': '',
                            'end_stop_en': '',
                            'distance': '0',
                            'start_time': '',
                            'end_time': '',
                            'timedesc': '',
                            'loop': '',
                            'status': '',
                            'basic_price': '',
                            'total_price': '',
                            'total_stops': 0,
                            'city_name_cn': '',
                            'city_name_en': city_en
                        }
                    
                    # Sort by sequence if available
                    if 'sequence' in df.columns:
                        df = df.sort_values('sequence')
                    
                    # Validate coordinates and create points
                    valid_points = []
                    for _, row in df.iterrows():
                        is_valid, lon, lat = self.validate_coordinates(row['longitude'], row['latitude'])
                        if is_valid:
                            valid_points.append(Point(lon, lat))
                    
                    # Need at least 2 points for a line
                    if len(valid_points) >= 2:
                        try:
                            line = LineString(valid_points)
                            
                            # Format city_code properly
                            city_code = self.format_city_code(route_info.get('city_code', ''))
                            
                            # Process operational information fields
                            start_time = str(route_info.get('start_time', ''))[:10]
                            end_time = str(route_info.get('end_time', ''))[:10]
                            loop = str(route_info.get('loop', ''))[:10]
                            status = str(route_info.get('status', ''))[:10]
                            basic_price = str(route_info.get('basic_price', ''))[:10]
                            total_price = str(route_info.get('total_price', ''))[:10]
                            
                            # Preserve route names with parentheses
                            route_name_cn = route_info.get('route_name_cn', 'Unknown')
                            route_name_en = route_info.get('route_name_en', 'unknown')
                            
                            # Build route data with operational info
                            route_data = {
                                'route_cn': str(route_name_cn)[:50],
                                'route_en': str(route_name_en)[:150],
                                'route_id': route_id[:30],
                                'city_code': city_code[:20],
                                'route_type': str(route_info.get('route_type', '地铁'))[:20],
                                'company_cn': str(route_info.get('company_cn', ''))[:50],
                                'company_en': str(route_info.get('company_en', ''))[:150],
                                's_stop_cn': str(route_info.get('start_stop_cn', ''))[:50],
                                's_stop_en': str(route_info.get('start_stop_en', ''))[:150],
                                'e_stop_cn': str(route_info.get('end_stop_cn', ''))[:50],
                                'e_stop_en': str(route_info.get('end_stop_en', ''))[:150],
                                'distance': route_info.get('distance', '0'),
                                'total_stop': route_info.get('total_stops', len(valid_points)),
                                'start_time': start_time,
                                'end_time': end_time,
                                'loop': loop,
                                'status': status,
                                'basic_prc': basic_price,
                                'total_prc': total_price,
                                'city_cn': str(route_info.get('city_name_cn', ''))[:30],
                                'city_en': str(route_info.get('city_name_en', ''))[:30],
                                'geometry': line
                            }
                            all_routes.append(route_data)
                            
                        except Exception as e:
                            logger.error(f"Failed to create geometry for route {file}: {e}")
                            invalid_routes_count += 1
                    else:
                        logger.warning(f"Insufficient points for route: {file} has only {len(valid_points)} valid points")
                        invalid_routes_count += 1
                        
                except Exception as e:
                    logger.error(f"Failed to process file {file}: {e}")
                    invalid_routes_count += 1
                    continue
        
        if not all_routes:
            logger.warning("No valid route data found")
            return None
        
        # Record counts before deduplication
        original_count = len(all_routes)
        logger.info(f"Routes before deduplication: {original_count}")
        
        # Deduplicate by route_cn and city_cn
        logger.info("Starting deduplication by route_cn and city_cn...")
        
        dedup_groups = {}
        for route in all_routes:
            dedup_key = f"{route['route_cn']}|{route['city_cn']}"
            if dedup_key not in dedup_groups:
                dedup_groups[dedup_key] = []
            dedup_groups[dedup_key].append(route)
        
        # Create deduplicated routes
        dedup_routes = []
        for key, group in dedup_groups.items():
            # Keep first route and set merge count
            first_route = group[0].copy()
            first_route['merged_cnt'] = len(group)
            dedup_routes.append(first_route)
        
        # Create GeoDataFrame
        routes_gdf = gpd.GeoDataFrame(dedup_routes, crs="EPSG:4326")
        
        logger.info(f"Routes after deduplication: {len(routes_gdf)}")
        logger.info(f"Duplicates removed: {original_count - len(routes_gdf)}")
        
        # Save to shapefile
        output_file = os.path.join(self.output_shp_path, "metro_routes.shp")
        routes_gdf.to_file(output_file, encoding='utf-8')
        
        # Calculate operational info coverage
        routes_with_time = len(routes_gdf[routes_gdf['start_time'] != '']) if 'start_time' in routes_gdf.columns else 0
        routes_with_price = len(routes_gdf[routes_gdf['basic_prc'] != '']) if 'basic_prc' in routes_gdf.columns else 0
        
        # Update statistics
        self.stats['total_routes'] = len(routes_gdf)
        self.stats['duplicated_routes_removed'] = original_count - len(routes_gdf)
        self.stats['invalid_routes'] = invalid_routes_count
        self.stats['routes_with_time_info'] = routes_with_time
        self.stats['routes_with_price_info'] = routes_with_price
        self.stats['time_info_coverage'] = (routes_with_time / len(routes_gdf) * 100) if len(routes_gdf) > 0 else 0
        self.stats['price_info_coverage'] = (routes_with_price / len(routes_gdf) * 100) if len(routes_gdf) > 0 else 0
        
        logger.info(f"Metro routes processing complete: {len(routes_gdf)} routes")
        logger.info(f"Operational time info coverage: {self.stats['time_info_coverage']:.2f}%")
        logger.info(f"Price info coverage: {self.stats['price_info_coverage']:.2f}%")
        
        return routes_gdf
    
    def generate_summary_report(self):
        """
        Generate comprehensive processing summary report
        
        Returns:
            dict: Summary report data
        """
        logger.info("Generating metro dataset summary report...")
        
        report = {
            'dataset_info': {
                'title': 'China Metro Network Vector Dataset 2024 (Enhanced with Operational Info & Deduplication & Taiwan Coordinate Fix)',
                'description': 'Comprehensive metro/subway network data for Chinese cities in WGS84 coordinate system with operational information, deduplication, and Taiwan coordinate correction',
                'coordinate_system': 'WGS-84 (EPSG:4326)',
                'data_format': 'ESRI Shapefile',
                'transport_type': 'Metro/Subway',
                'taiwan_coordinate_fix': 'Taiwan Province metro station coordinates corrected using transform.wgs84_to_gcj02',
                'deduplication': {
                    'routes': 'Deduplicated by route_cn and city_cn combination',
                    'stops': 'Deduplicated by name_cn, route_cn, city_cn, and sequence combination'
                },
                'creation_date': pd.Timestamp.now().isoformat()
            },
            'data_statistics': self.stats,
            'data_quality': {
                'coordinate_validation': 'Applied with Taiwan correction',
                'duplicate_removal': 'Applied for both routes and stops',
                'operational_info_coverage': {
                    'time_info': f"{self.stats.get('time_info_coverage', 0):.2f}%",
                    'price_info': f"{self.stats.get('price_info_coverage', 0):.2f}%"
                },
                'taiwan_coordinate_correction': f"Applied to {self.stats.get('taiwan_coords_fixed', 0)} stations"
            }
        }
        
        # Save report
        report_file = os.path.join(self.output_shp_path, "metro_dataset_summary_report.json")
        with open(report_file, "w", encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        # Save readable text format
        txt_report_file = os.path.join(self.output_shp_path, "metro_dataset_summary_report.txt")
        with open(txt_report_file, "w", encoding='utf-8') as f:
            f.write("=== China Metro Network Vector Dataset 2024 ===\n\n")
            f.write(f"Dataset Title: {report['dataset_info']['title']}\n")
            f.write(f"Coordinate System: {report['dataset_info']['coordinate_system']}\n")
            f.write(f"Data Format: {report['dataset_info']['data_format']}\n")
            f.write(f"Transport Type: {report['dataset_info']['transport_type']}\n")
            f.write(f"Creation Date: {report['dataset_info']['creation_date']}\n\n")
            
            f.write("=== Processing Statistics ===\n")
            f.write(f"Cities Processed: {self.stats.get('cities_processed', 0)}\n")
            f.write(f"Total Metro Routes: {self.stats.get('total_routes', 0)}\n")
            f.write(f"Total Metro Stops: {self.stats.get('total_stops', 0)}\n")
            f.write(f"Routes Deduplicated: {self.stats.get('duplicated_routes_removed', 0)}\n")
            f.write(f"Stops Deduplicated: {self.stats.get('duplicated_stops_removed', 0)}\n")
            f.write(f"Taiwan Coordinates Fixed: {self.stats.get('taiwan_coords_fixed', 0)}\n")
            f.write(f"Invalid Coordinates: {self.stats.get('invalid_coordinates', 0)}\n\n")
            
            f.write("=== Data Quality Features ===\n")
            f.write("- Coordinate validation with Taiwan Province correction\n")
            f.write("- Intelligent deduplication for routes and stops\n")
            f.write("- Operational information extraction (schedules, pricing)\n")
            f.write("- Preserved parentheses in route and stop names\n")
            f.write("- City code format preservation with leading zeros\n\n")
            
            f.write("=== Operational Information Coverage ===\n")
            f.write(f"Time Information: {self.stats.get('time_info_coverage', 0):.2f}%\n")
            f.write(f"Price Information: {self.stats.get('price_info_coverage', 0):.2f}%\n")
            f.write(f"Routes with Time Info: {self.stats.get('routes_with_time_info', 0)}\n")
            f.write(f"Routes with Price Info: {self.stats.get('routes_with_price_info', 0)}\n\n")
            
            f.write("=== Taiwan Coordinate Correction ===\n")
            f.write("Problem: Taiwan metro stations incorrectly converted from WGS84 to GCJ02\n")
            f.write("Solution: Applied transform.wgs84_to_gcj02 to correct coordinates\n")
            f.write(f"Stations Fixed: {self.stats.get('taiwan_coords_fixed', 0)}\n")
            f.write("Detection: Based on city_cn field containing '台湾'\n\n")
            
            f.write("=== Output Files ===\n")
            f.write("- metro_routes.shp: Metro route geometries with operational info\n")
            f.write("- metro_stops.shp: Metro stop locations (deduplicated)\n")
            f.write("- metro_dataset_summary_report.json: Processing report\n")
        
        logger.info(f"Metro dataset summary report saved to: {report_file}")
        
        return report
    
    def process_all(self):
        """
        Execute complete metro data processing pipeline
        
        Returns:
            dict: Processing results and statistics
        """
        logger.info("Starting complete metro data processing pipeline...")
        logger.info("Features: Taiwan coordinate correction, deduplication, operational info extraction")
        
        # Process stops with Taiwan coordinate correction
        stops_gdf = self.process_metro_stops()
        
        # Process routes with operational information
        routes_gdf = self.process_metro_routes()
        
        # Update cities processed count
        self.stats['cities_processed'] = len(self.get_city_directories())
        
        # Generate summary report
        report = self.generate_summary_report()
        
        logger.info("Metro data processing completed successfully!")
        logger.info(f"Output directory: {self.output_shp_path}")
        logger.info("Features applied:")
        logger.info("  - Taiwan Province coordinate correction")
        logger.info("  - Intelligent deduplication for routes and stops")
        logger.info("  - Operational information preservation")
        logger.info("  - City code format preservation")
        logger.info("  - Name format preservation (with parentheses)")
        
        return {
            'stops': stops_gdf,
            'routes': routes_gdf,
            'report': report,
            'stats': self.stats
        }


def main():
    """Main execution function for metro data processing"""
    logger.info("Starting Metro Data Processor")
    
    # Check input data availability
    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(current_dir, "..", "dataset", "metro")
    
    if not os.path.exists(data_path):
        logger.error(f"Input data path not found: {data_path}")
        logger.error("Please run the crawler first to collect data")
        return
    
    # Check city folder structure
    metro_routes_path = os.path.join(data_path, "metro_routes")
    metro_stops_path = os.path.join(data_path, "metro_stops")
    enhanced_data_path = os.path.join(data_path, "enhanced_data")
    
    # Verify city folders exist
    cities_found = set()
    for base_path in [metro_routes_path, metro_stops_path, enhanced_data_path]:
        if os.path.exists(base_path):
            for item in os.listdir(base_path):
                item_path = os.path.join(base_path, item)
                if os.path.isdir(item_path):
                    cities_found.add(item)
    
    if not cities_found:
        logger.error("No city folder structure found")
        logger.error("Please ensure data contains city folders (metro_routes/city_en, metro_stops/city_en, enhanced_data/city_en)")
        return
    
    logger.info(f"Using data path: {data_path}")
    logger.info("Processing mode: City folder structure with deduplication and Taiwan coordinate correction")
    logger.info(f"Found {len(cities_found)} cities: {sorted(cities_found)}")
    
    # Check for Taiwan cities
    taiwan_cities = [city for city in cities_found if 'taiwan' in city.lower() or 'tai_wan' in city.lower()]
    if taiwan_cities:
        logger.info(f"Detected Taiwan-related cities: {taiwan_cities}")
        logger.info("Taiwan metro station coordinates will be corrected")
    
    # Initialize and execute processor
    processor = MetroDataProcessor(data_path)
    
    try:
        results = processor.process_all()
        
        if results:
            logger.info("Processing completed successfully")
            logger.info(f"Processing summary:")
            if results['stops'] is not None:
                logger.info(f"  Metro stops: {len(results['stops'])} (deduplicated, Taiwan corrected)")
            if results['routes'] is not None:
                logger.info(f"  Metro routes: {len(results['routes'])} (with operational info, deduplicated)")
            
            logger.info(f"Output shapefiles saved to: {processor.output_shp_path}")
            
            # Display key statistics
            stats = results['stats']
            logger.info("Key Statistics:")
            logger.info(f"  Taiwan coordinates fixed: {stats.get('taiwan_coords_fixed', 0)}")
            logger.info(f"  Duplicate routes removed: {stats.get('duplicated_routes_removed', 0)}")
            logger.info(f"  Duplicate stops removed: {stats.get('duplicated_stops_removed', 0)}")
            logger.info(f"  Operational time coverage: {stats.get('time_info_coverage', 0):.2f}%")
            logger.info(f"  Price information coverage: {stats.get('price_info_coverage', 0):.2f}%")
            
        else:
            logger.error("Processing failed - no results generated")
            
    except Exception as e:
        logger.error(f"Processing failed with error: {e}")
        raise


if __name__ == "__main__":
    main()