#!/usr/bin/env python3
"""
Bus Segment Processor

This module processes bus route data to create network segments between
consecutive stops, organized by city. Generates segment-level analysis
suitable for urban transportation network studies.

Dependencies:
    - geopandas
    - pandas
    - shapely
    - pyproj (for distance calculations)

Input:
    - Bus routes shapefile (LineString geometries)
    - Bus stops shapefile (Point geometries)

Output:
    - City-wise bus segments shapefiles
    - Deduplicated stops shapefiles per city
    - Distance calculations and route statistics

Author: Urban Transportation Research Team
License: MIT
"""

import os
import geopandas as gpd
import pandas as pd
import json
from shapely.geometry import Point, LineString
from collections import defaultdict
import re
from pathlib import Path
import logging
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BusSegmentProcessor:
    """
    Bus route segment processor for city-wise analysis
    
    Breaks bus routes into segments between consecutive stops,
    processes data by city, and generates standardized outputs
    with distance calculations and route statistics.
    
    Version: Updated to remove route-related fields from segments and stops,
    added distance field for segments with accurate geometric calculations.
    """
    
    def __init__(self, data_path=None):
        """
        Initialize the bus segment processor
        
        Args:
            data_path (str): Path to input shapefile data
        """
        if data_path is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            data_path = os.path.join(current_dir, "..", "dataset", "bus")
        
        self.data_path = data_path
        self.shapefiles_path = os.path.join(data_path, "shapefiles")
        
        # Set up logging directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.logs_dir = os.path.join(current_dir, "..", "logs")
        os.makedirs(self.logs_dir, exist_ok=True)
        
        self.global_stats = {
            'total_cities': 0,
            'processed_cities': 0,
            'failed_cities': 0,
            'total_routes': 0,
            'total_stops': 0,
            'total_segments': 0,
            'total_unique_segments': 0,
            'total_unique_stops': 0
        }
        
        logger.info(f"Bus Segment Processor initialized")
        logger.info(f"Shapefile input path: {self.shapefiles_path}")
    
    def city_name_to_pinyin(self, city_name):
        """
        Convert city English name to pinyin format for file naming
        
        Args:
            city_name (str): City name in English
            
        Returns:
            str: Standardized pinyin filename
        """
        if pd.isna(city_name) or str(city_name).strip() == '':
            return 'unknown_city'
        
        city_name = str(city_name).strip()
        
        # Handle pure English names
        if re.match(r'^[a-zA-Z\s\-\.]+$', city_name):
            pinyin_name = re.sub(r'[\s\-\.]+', '_', city_name.lower())
            pinyin_name = re.sub(r'_+', '_', pinyin_name).strip('_')
            return pinyin_name
        
        # Handle Chinese characters with pypinyin if available
        try:
            from pypinyin import lazy_pinyin, Style
            pinyin_list = lazy_pinyin(city_name, style=Style.NORMAL)
            pinyin_name = '_'.join(pinyin_list).lower()
            pinyin_name = re.sub(r'[^a-z0-9_]', '_', pinyin_name)
            pinyin_name = re.sub(r'_+', '_', pinyin_name).strip('_')
            return pinyin_name
        except ImportError:
            logger.warning("pypinyin library not installed, using basic name processing")
            pinyin_name = re.sub(r'[^a-zA-Z0-9\s]', '_', city_name)
            pinyin_name = re.sub(r'[\s_]+', '_', pinyin_name.lower()).strip('_')
            return pinyin_name if pinyin_name else 'unknown_city'
    
    def sanitize_folder_name(self, city_name):
        """
        Clean city name to make it suitable for folder naming
        
        Args:
            city_name (str): City name
            
        Returns:
            str: Sanitized folder name
        """
        if pd.isna(city_name) or str(city_name).strip() == '':
            return 'unknown_city'
        
        city_name = str(city_name).strip()
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            city_name = city_name.replace(char, '_')
        
        city_name = city_name.strip('. ')
        
        if not city_name:
            city_name = 'unknown_city'
        
        return city_name
    
    def load_shapefiles(self):
        """
        Load bus route and stop shapefile data
        
        Returns:
            tuple: (routes_gdf, stops_gdf) GeoDataFrames
        """
        routes_file = os.path.join(self.shapefiles_path, "bus_routes.shp")
        stops_file = os.path.join(self.shapefiles_path, "bus_stops.shp")
        
        logger.info("Loading bus shapefile data...")
        
        # Check file existence
        if not os.path.exists(routes_file):
            raise FileNotFoundError(f"Bus routes file not found: {routes_file}")
        
        if not os.path.exists(stops_file):
            raise FileNotFoundError(f"Bus stops file not found: {stops_file}")
        
        try:
            logger.info(f"Loading: {routes_file}")
            routes_gdf = gpd.read_file(routes_file)
            logger.info(f"Bus routes loaded: {len(routes_gdf)} routes")
            
            logger.info(f"Loading: {stops_file}")
            stops_gdf = gpd.read_file(stops_file)
            logger.info(f"Bus stops loaded: {len(stops_gdf)} stops")
            
            return routes_gdf, stops_gdf
            
        except Exception as e:
            raise Exception(f"Error loading shapefiles: {e}")
    
    def get_unique_cities(self, stops_gdf, routes_gdf):
        """
        Extract unique cities from the datasets
        
        Args:
            stops_gdf (gpd.GeoDataFrame): Stops data
            routes_gdf (gpd.GeoDataFrame): Routes data
            
        Returns:
            list: Sorted list of unique city names
        """
        stops_cities = set()
        routes_cities = set()
        
        # Extract cities from stops data
        if 'city_en' in stops_gdf.columns:
            stops_cities = set(stops_gdf['city_en'].dropna().unique())
        
        # Extract cities from routes data
        if 'city_en' in routes_gdf.columns:
            routes_cities = set(routes_gdf['city_en'].dropna().unique())
        
        # Combine and filter city lists
        all_cities = stops_cities.union(routes_cities)
        all_cities = {city for city in all_cities if city and str(city).strip() != ''}
        
        logger.info(f"Found {len(all_cities)} unique cities")
        
        return sorted(list(all_cities))
    
    def get_route_stops_ordered(self, route_id, stops_gdf):
        """
        Get stops for specified route, ordered by sequence
        
        Args:
            route_id (str): Route identifier
            stops_gdf (gpd.GeoDataFrame): Stops data
            
        Returns:
            gpd.GeoDataFrame: Ordered stops for the route
        """
        route_stops = stops_gdf[stops_gdf['route_id'] == route_id].copy()
        
        if len(route_stops) == 0:
            return route_stops
        
        # Sort by sequence if available, otherwise use data order
        if 'sequence' in route_stops.columns:
            route_stops = route_stops.sort_values('sequence')
        
        return route_stops
    
    def project_point_to_line(self, point, line):
        """
        Project point to line and return projection distance
        
        Args:
            point (Point): Point geometry
            line (LineString): Line geometry
            
        Returns:
            float: Projection distance along line
        """
        try:
            return line.project(point)
        except Exception as e:
            logger.warning(f"Projection failed: {e}")
            return None
    
    def extract_line_segment(self, line, start_distance, end_distance):
        """
        Extract line segment from specified distance range
        
        Args:
            line (LineString): Original line geometry
            start_distance (float): Start distance along line
            end_distance (float): End distance along line
            
        Returns:
            LineString: Extracted segment or None if failed
        """
        try:
            from shapely.ops import substring
            # Ensure start_distance <= end_distance
            if start_distance > end_distance:
                start_distance, end_distance = end_distance, start_distance
            
            # Extract segment
            segment = substring(line, start_distance, end_distance)
            
            # If extracted segment is empty or too short, return None
            if segment.is_empty or segment.length < 0.000001:  # Very small threshold
                return None
            
            return segment
        except Exception as e:
            logger.warning(f"Segment extraction failed: {e}")
            return None
    
    def calculate_segment_distance(self, segment_line):
        """
        Calculate segment distance in kilometers using projection
        
        Args:
            segment_line (LineString): Segment geometry
            
        Returns:
            float: Distance in kilometers (3 decimal places)
        """
        try:
            # Convert to Web Mercator for accurate distance calculation
            from shapely.ops import transform
            import pyproj
            
            project = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True).transform
            line_proj = transform(project, segment_line)
            return round(line_proj.length / 1000, 3)  # Convert to km
        except Exception as e:
            logger.error(f"Distance calculation failed: {e}")
            # Fallback to approximate calculation
            try:
                return round(segment_line.length * 111.32, 3)  # Rough conversion to km
            except:
                return 0.0
    
    def create_segments_from_route(self, route_row, stops_gdf):
        """
        Create segments from a single route using consecutive stops
        Updated version: Removed route-related fields, added distance field
        
        Args:
            route_row (pd.Series): Route data row
            stops_gdf (gpd.GeoDataFrame): Stops data
            
        Returns:
            list: List of segment data dictionaries
        """
        route_id = route_row['route_id']
        route_cn = route_row.get('route_cn', '')
        city_cn = route_row.get('city_cn', '')
        city_en = route_row.get('city_en', '')
        route_geometry = route_row.geometry
        
        # Get stops for this route
        route_stops = self.get_route_stops_ordered(route_id, stops_gdf)
        
        if len(route_stops) < 2:
            logger.warning(f"Route {route_cn} (ID: {route_id}) has insufficient stops")
            return []
        
        # Validate route geometry
        if not route_geometry or route_geometry.is_empty:
            logger.warning(f"Route {route_cn} (ID: {route_id}) has invalid geometry")
            return []
        
        segments = []
        stops_list = route_stops.reset_index(drop=True)
        
        # Project all stops to route line and get projection distances
        stop_projections = []
        for idx, stop_row in stops_list.iterrows():
            stop_point = stop_row.geometry
            projection_distance = self.project_point_to_line(stop_point, route_geometry)
            
            if projection_distance is not None:
                stop_projections.append({
                    'index': idx,
                    'stop_data': stop_row,
                    'projection_distance': projection_distance
                })
            else:
                logger.warning(f"Stop {stop_row.get('name_cn', '')} projection failed")
        
        # Sort by projection distance to ensure correct order
        stop_projections.sort(key=lambda x: x['projection_distance'])
        
        # Create segments between consecutive stops
        for i in range(len(stop_projections) - 1):
            start_stop_info = stop_projections[i]
            end_stop_info = stop_projections[i + 1]
            
            start_stop = start_stop_info['stop_data']
            end_stop = end_stop_info['stop_data']
            start_distance = start_stop_info['projection_distance']
            end_distance = end_stop_info['projection_distance']
            
            # Try to extract segment from original route
            segment_line = self.extract_line_segment(route_geometry, start_distance, end_distance)
            
            # If extraction fails, use direct line connection as fallback
            if segment_line is None:
                logger.debug(f"Using direct connection: {start_stop.get('name_cn', '')} -> {end_stop.get('name_cn', '')}")
                start_point = start_stop.geometry
                end_point = end_stop.geometry
                segment_line = LineString([start_point, end_point])
            
            # Calculate segment distance
            distance = self.calculate_segment_distance(segment_line)
            
            # Updated segment data structure - removed route fields, added distance field
            segment_data = {
                's_stop_cn': str(start_stop.get('name_cn', '')),
                's_stop_en': str(start_stop.get('name_en', '')),
                's_stopid': str(start_stop.get('stop_id', '')),
                'e_stop_cn': str(end_stop.get('name_cn', '')),
                'e_stop_en': str(end_stop.get('name_en', '')),
                'e_stopid': str(end_stop.get('stop_id', '')),
                'distance': distance,  # New field: distance in kilometers
                'city_cn': str(city_cn),
                'city_en': str(city_en),
                'geometry': segment_line
            }
            
            segments.append(segment_data)
        
        return segments
    
    def process_city_segments(self, city_en, routes_gdf, stops_gdf):
        """
        Process routes for a single city and generate segments
        
        Args:
            city_en (str): City English name
            routes_gdf (gpd.GeoDataFrame): Routes data
            stops_gdf (gpd.GeoDataFrame): Stops data
            
        Returns:
            tuple: (segments_list, city_stops)
        """
        logger.info(f"Processing city: {city_en}")
        
        # Filter city data
        city_routes = routes_gdf[routes_gdf['city_en'] == city_en].copy()
        city_stops = stops_gdf[stops_gdf['city_en'] == city_en].copy()
        
        logger.info(f"City routes: {len(city_routes)}, City stops: {len(city_stops)}")
        
        if len(city_routes) == 0:
            logger.warning(f"No route data for city {city_en}, skipping")
            return [], []
        
        logger.info("Generating route segments...")
        
        all_segments = []
        processed_routes = 0
        failed_routes = 0
        
        for idx, route_row in city_routes.iterrows():
            try:
                route_segments = self.create_segments_from_route(route_row, city_stops)
                all_segments.extend(route_segments)
                processed_routes += 1
                
                if processed_routes % 50 == 0:
                    logger.info(f"Processed {processed_routes}/{len(city_routes)} routes")
                    
            except Exception as e:
                failed_routes += 1
                logger.error(f"Failed to process route: {route_row.get('route_cn', 'Unknown')} - {e}")
                continue
        
        logger.info(f"Route processing complete: Success {processed_routes}, Failed {failed_routes}")
        logger.info(f"Generated segments total: {len(all_segments)}")
        
        return all_segments, city_stops
    
    def aggregate_segments(self, segments_list):
        """
        Aggregate segments by start and end stops, calculating statistics
        Updated version: Removed route fields, kept distance calculations
        
        Args:
            segments_list (list): List of segment data
            
        Returns:
            list: Aggregated segment data with statistics
        """
        logger.info("Aggregating segments...")
        
        # Group segments by (start_stop_id, end_stop_id)
        segment_groups = defaultdict(lambda: {
            'distances': [],
            'first_segment': None,
            'cities': set(),
            'count': 0
        })
        
        for segment in segments_list:
            key = (segment['s_stopid'], segment['e_stopid'])
            
            group = segment_groups[key]
            
            # Store first segment as template
            if group['first_segment'] is None:
                group['first_segment'] = segment.copy()
            
            # Collect distance information
            group['distances'].append(segment['distance'])
            group['cities'].add(segment['city_cn'])
            group['count'] += 1
        
        # Generate aggregated segments
        aggregated_segments = []
        
        for key, group in segment_groups.items():
            segment = group['first_segment'].copy()
            
            # Calculate average distance
            avg_distance = round(sum(group['distances']) / len(group['distances']), 3) if group['distances'] else 0.0
            
            # Update segment data
            segment['num'] = group['count']
            segment['distance'] = avg_distance
            segment['city_cn'] = '; '.join(list(group['cities']))
            
            aggregated_segments.append(segment)
        
        logger.info(f"Aggregation complete: {len(segments_list)} -> {len(aggregated_segments)} segments")
        
        return aggregated_segments
    
    def create_unique_stops(self, stops_gdf):
        """
        Create deduplicated stops with route count statistics
        Updated version: Removed route-related fields
        
        Args:
            stops_gdf (gpd.GeoDataFrame): Stops data
            
        Returns:
            list: Unique stops with statistics
        """
        logger.info("Processing stop deduplication and statistics...")
        
        # Group stops by stop_id
        stop_groups = defaultdict(lambda: {
            'route_ids': set(),
            'first_stop': None,
            'cities': set()
        })
        
        for idx, stop_row in stops_gdf.iterrows():
            stop_id = str(stop_row.get('stop_id', ''))
            route_id = str(stop_row.get('route_id', ''))
            city_cn = str(stop_row.get('city_cn', ''))
            
            if not stop_id:
                continue
            
            group = stop_groups[stop_id]
            
            # Store first stop as template
            if group['first_stop'] is None:
                group['first_stop'] = stop_row.copy()
            
            # Collect route information
            if route_id:
                group['route_ids'].add(route_id)
                group['cities'].add(city_cn)
        
        # Generate unique stops
        unique_stops = []
        
        for stop_id, group in stop_groups.items():
            stop = group['first_stop'].copy()
            
            # Updated stop record - removed route-related fields
            stop_data = {
                'stop_cn': str(stop.get('name_cn', '')),
                'stop_en': str(stop.get('name_en', '')),
                'stop_id': stop_id,
                'num': len(group['route_ids']),  # Number of routes using this stop
                'city_cn': '; '.join(list(group['cities'])),
                'city_en': str(stop.get('city_en', '')),
                'geometry': stop.geometry
            }
            
            unique_stops.append(stop_data)
        
        logger.info(f"Stop deduplication complete: {len(stops_gdf)} -> {len(unique_stops)} stops")
        
        return unique_stops
    
    def save_city_shapefiles(self, city_en, segments_list, stops_list):
        """
        Save city-specific segments and stops as shapefiles
        Updated version: Updated field descriptions for removed route fields and added distance field
        
        Args:
            city_en (str): City English name
            segments_list (list): Segment data
            stops_list (list): Stop data
            
        Returns:
            dict: Results of save operations
        """
        logger.info(f"Saving shapefiles for city: {city_en}")
        
        # Generate file paths
        city_pinyin = self.city_name_to_pinyin(city_en)
        folder_name = self.sanitize_folder_name(city_en)
        
        # Create city output directory
        city_output_path = os.path.join(self.shapefiles_path, folder_name)
        os.makedirs(city_output_path, exist_ok=True)
        
        results = {'segments': None, 'stops': None}
        
        # Save segments shapefile
        if segments_list:
            segments_gdf = gpd.GeoDataFrame(segments_list)
            segments_gdf.crs = "EPSG:4326"  # WGS84 coordinate system
            
            # Ensure field lengths comply with shapefile limits
            for col in ['s_stop_cn', 's_stop_en', 'e_stop_cn', 'e_stop_en']:
                if col in segments_gdf.columns:
                    segments_gdf[col] = segments_gdf[col].astype(str).str[:80]
            
            for col in ['s_stopid', 'e_stopid']:
                if col in segments_gdf.columns:
                    segments_gdf[col] = segments_gdf[col].astype(str).str[:50]
            
            for col in ['city_cn', 'city_en']:
                if col in segments_gdf.columns:
                    segments_gdf[col] = segments_gdf[col].astype(str).str[:30]
            
            # Save segments shapefile
            segments_file = os.path.join(city_output_path, f"{city_pinyin}_bus_segments.shp")
            
            try:
                segments_gdf.to_file(segments_file, encoding='utf-8')
                logger.info(f"Segments shapefile saved: {segments_file}")
                results['segments'] = segments_gdf
            except Exception as e:
                logger.error(f"Failed to save segments shapefile: {e}")
        
        # Save stops shapefile
        if stops_list:
            stops_gdf = gpd.GeoDataFrame(stops_list)
            stops_gdf.crs = "EPSG:4326"  # WGS84 coordinate system
            
            # Ensure field lengths comply with shapefile limits
            for col in ['stop_cn', 'stop_en']:
                if col in stops_gdf.columns:
                    stops_gdf[col] = stops_gdf[col].astype(str).str[:80]
            
            for col in ['stop_id']:
                if col in stops_gdf.columns:
                    stops_gdf[col] = stops_gdf[col].astype(str).str[:50]
            
            for col in ['city_cn', 'city_en']:
                if col in stops_gdf.columns:
                    stops_gdf[col] = stops_gdf[col].astype(str).str[:30]
            
            # Save stops shapefile
            stops_file = os.path.join(city_output_path, f"{city_pinyin}_bus_stops_unique.shp")
            
            try:
                stops_gdf.to_file(stops_file, encoding='utf-8')
                logger.info(f"Unique stops shapefile saved: {stops_file}")
                results['stops'] = stops_gdf
            except Exception as e:
                logger.error(f"Failed to save stops shapefile: {e}")
        
        # Create city information file - updated field descriptions
        try:
            info_file = os.path.join(city_output_path, "segment_info.txt")
            with open(info_file, 'w', encoding='utf-8') as f:
                f.write(f"Bus City Segment Information (Updated Version)\n")
                f.write(f"=" * 50 + "\n")
                f.write(f"City English Name: {city_en}\n")
                f.write(f"City Pinyin: {city_pinyin}\n")
                f.write(f"Folder Name: {folder_name}\n")
                f.write(f"Processing Time: {pd.Timestamp.now().isoformat()}\n")
                f.write(f"Coordinate System: WGS84 (EPSG:4326)\n\n")
                
                f.write(f"Data Statistics:\n")
                f.write(f"  Generated segments: {len(segments_list) if segments_list else 0}\n")
                f.write(f"  Unique stops: {len(stops_list) if stops_list else 0}\n\n")
                
                f.write(f"Output Files:\n")
                f.write(f"  {city_pinyin}_bus_segments.shp (route segments)\n")
                f.write(f"  {city_pinyin}_bus_stops_unique.shp (unique stops)\n\n")
                
                f.write(f"Field Descriptions:\n")
                f.write(f"Segments Fields:\n")
                f.write(f"  s_stop_cn: Start stop Chinese name\n")
                f.write(f"  s_stop_en: Start stop English name\n")
                f.write(f"  s_stopid: Start stop ID\n")
                f.write(f"  e_stop_cn: End stop Chinese name\n")
                f.write(f"  e_stop_en: End stop English name\n")
                f.write(f"  e_stopid: End stop ID\n")
                f.write(f"  distance: Segment distance (kilometers)\n")
                f.write(f"  num: Number of routes using this segment\n")
                f.write(f"  city_cn: City (Chinese)\n")
                f.write(f"  city_en: City (English)\n\n")
                
                f.write(f"Unique Stops Fields:\n")
                f.write(f"  stop_cn: Stop Chinese name\n")
                f.write(f"  stop_en: Stop English name\n")
                f.write(f"  stop_id: Stop ID\n")
                f.write(f"  num: Number of routes using this stop\n")
                f.write(f"  city_cn: City (Chinese)\n")
                f.write(f"  city_en: City (English)\n\n")
                
                f.write(f"Version Updates:\n")
                f.write(f"  - Removed route-related fields from segments and stops\n")
                f.write(f"  - Added distance field to segments (calculated using projection)\n")
                f.write(f"  - Distance unit: kilometers (3 decimal places)\n")
            
            logger.info(f"City information file saved: {info_file}")
            
        except Exception as e:
            logger.error(f"Failed to save city information file: {e}")
        
        return results
    
    def save_global_summary_report(self, city_results):
        """
        Save global processing summary report
        Updated version: Updated field descriptions for version changes
        
        Args:
            city_results (list): City processing results
            
        Returns:
            dict: Summary report data
        """
        logger.info("Generating global processing summary report...")
        
        report = {
            'processing_info': {
                'title': 'Bus Network City Segment Analysis Report (Updated Version)',
                'description': 'Analysis of bus route segments and stop aggregation by city (route fields removed, distance field added)',
                'coordinate_system': 'WGS-84 (EPSG:4326)',
                'processing_time': pd.Timestamp.now().isoformat(),
                'input_data': {
                    'routes_file': os.path.join(self.shapefiles_path, "bus_routes.shp"),
                    'stops_file': os.path.join(self.shapefiles_path, "bus_stops.shp")
                },
                'version_changes': 'Removed route_cn, route_en, route_id from segments; removed route_cn, route_en from stops; added distance field to segments'
            },
            'global_statistics': self.global_stats,
            'city_results': city_results,
            'file_structure': {
                'naming_format': {
                    'segments': '{city_pinyin}_bus_segments.shp',
                    'unique_stops': '{city_pinyin}_bus_stops_unique.shp'
                },
                'folder_structure': 'shapefiles/{city_folder_name}/'
            }
        }
        
        # Save JSON format report
        report_file = os.path.join(self.shapefiles_path, "city_segment_analysis_report.json")
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        # Save text format report - updated field descriptions
        txt_report_file = os.path.join(self.shapefiles_path, "city_segment_analysis_report.txt")
        with open(txt_report_file, 'w', encoding='utf-8') as f:
            f.write("Bus City Route Segment Analysis Report (Updated Version)\n")
            f.write("=" * 70 + "\n\n")
            
            f.write(f"Processing Time: {pd.Timestamp.now().isoformat()}\n")
            f.write(f"Input Data Path: {self.shapefiles_path}\n")
            f.write(f"Version Update: Removed segments route fields, added distance field; removed stops route fields\n\n")
            
            f.write("Global Statistics:\n")
            f.write(f"  Total Cities: {self.global_stats['total_cities']}\n")
            f.write(f"  Successfully Processed: {self.global_stats['processed_cities']}\n")
            f.write(f"  Processing Failed: {self.global_stats['failed_cities']}\n")
            f.write(f"  Original Routes Total: {self.global_stats['total_routes']}\n")
            f.write(f"  Original Stops Total: {self.global_stats['total_stops']}\n")
            f.write(f"  Generated Segments Total: {self.global_stats['total_segments']}\n")
            f.write(f"  Unique Segments After Deduplication: {self.global_stats['total_unique_segments']}\n")
            f.write(f"  Unique Stops After Deduplication: {self.global_stats['total_unique_stops']}\n\n")
            
            f.write("File Naming Format:\n")
            f.write("  Route segments: {city_pinyin}_bus_segments.shp\n")
            f.write("  Unique stops: {city_pinyin}_bus_stops_unique.shp\n")
            f.write("  Storage path: shapefiles/{city_folder_name}/\n\n")
            
            f.write("City Processing Results:\n")
            for city_info in city_results:
                city_en = city_info['city_en']
                city_pinyin = city_info['city_pinyin']
                segments_count = city_info['segments_count']
                stops_count = city_info['stops_count']
                success = city_info['success']
                
                status = "✓" if success else "✗"
                f.write(f"  {status} {city_en} (pinyin: {city_pinyin})\n")
                f.write(f"      Segments: {segments_count}, Unique stops: {stops_count}\n")
            
            f.write(f"\nField Update Description:\n")
            f.write("=== Segments Field Changes ===\n")
            f.write("Removed fields: route_cn, route_en, route_id\n")
            f.write("Added fields: distance (segment distance in kilometers)\n")
            f.write("Retained fields: s_stop_cn, s_stop_en, s_stopid, e_stop_cn, e_stop_en, e_stopid, num, city_cn, city_en\n\n")
            
            f.write("=== Unique Stops Field Changes ===\n")
            f.write("Removed fields: route_cn, route_en\n")
            f.write("Retained fields: stop_cn, stop_en, stop_id, num, city_cn, city_en\n\n")
            
            f.write(f"Data Description:\n")
            f.write("- Segment is a line between two consecutive stops\n")
            f.write("- Segments with same start and end stops are merged, counting routes\n")
            f.write("- Stops are deduplicated by ID, counting routes per stop\n")
            f.write("- Processing and storage by city\n")
            f.write("- Coordinate system: WGS84 (EPSG:4326)\n")
            f.write("- distance field: Calculated using projected coordinates, unit: kilometers\n")
            f.write("- num field: Number of routes using this segment or stop\n")
        
        logger.info(f"Global report saved: {report_file}")
        logger.info(f"Global report saved: {txt_report_file}")
        
        return report
    
    def process_all_cities(self):
        """
        Execute complete city segment processing pipeline
        
        Returns:
            dict: Processing results and statistics
        """
        logger.info("Starting bus city segment processing pipeline...")
        logger.info(f"Input path: {self.shapefiles_path}")
        logger.info("=" * 60)
        
        try:
            # 1. Load shapefile data
            logger.info("Loading bus route and stop data...")
            routes_gdf, stops_gdf = self.load_shapefiles()
            
            self.global_stats['total_routes'] = len(routes_gdf)
            self.global_stats['total_stops'] = len(stops_gdf)
            
            # 2. Get city list
            logger.info("Extracting city list...")
            cities = self.get_unique_cities(stops_gdf, routes_gdf)
            self.global_stats['total_cities'] = len(cities)
            
            if not cities:
                logger.error("No city data found!")
                return None
            
            logger.info(f"Processing {len(cities)} cities")
            
            # 3. Process cities individually
            logger.info("Starting city-wise processing...")
            city_results = []
            
            for i, city_en in enumerate(cities, 1):
                logger.info(f"Progress: {i}/{len(cities)} - {city_en}")
                
                try:
                    # Process city segments
                    segments_list, city_stops = self.process_city_segments(city_en, routes_gdf, stops_gdf)
                    
                    if not segments_list:
                        logger.warning(f"City {city_en} generated no segments, skipping")
                        city_results.append({
                            'city_en': city_en,
                            'city_pinyin': self.city_name_to_pinyin(city_en),
                            'segments_count': 0,
                            'stops_count': 0,
                            'success': False
                        })
                        self.global_stats['failed_cities'] += 1
                        continue
                    
                    # Aggregate segments
                    aggregated_segments = self.aggregate_segments(segments_list)
                    
                    # Create unique stops
                    unique_stops = self.create_unique_stops(city_stops)
                    
                    # Save city results
                    save_result = self.save_city_shapefiles(city_en, aggregated_segments, unique_stops)
                    
                    # Update statistics
                    if save_result['segments'] is not None or save_result['stops'] is not None:
                        city_results.append({
                            'city_en': city_en,
                            'city_pinyin': self.city_name_to_pinyin(city_en),
                            'segments_count': len(aggregated_segments),
                            'stops_count': len(unique_stops),
                            'success': True
                        })
                        
                        self.global_stats['processed_cities'] += 1
                        self.global_stats['total_segments'] += len(segments_list)
                        self.global_stats['total_unique_segments'] += len(aggregated_segments)
                        self.global_stats['total_unique_stops'] += len(unique_stops)
                        
                        logger.info(f"City {city_en} processing completed")
                    else:
                        city_results.append({
                            'city_en': city_en,
                            'city_pinyin': self.city_name_to_pinyin(city_en),
                            'segments_count': 0,
                            'stops_count': 0,
                            'success': False
                        })
                        self.global_stats['failed_cities'] += 1
                        logger.error(f"City {city_en} save failed")
                
                except Exception as e:
                    logger.error(f"Error processing city {city_en}: {e}")
                    city_results.append({
                        'city_en': city_en,
                        'city_pinyin': self.city_name_to_pinyin(city_en),
                        'segments_count': 0,
                        'stops_count': 0,
                        'success': False
                    })
                    self.global_stats['failed_cities'] += 1
                    continue
            
            # 4. Generate summary report
            logger.info("Generating summary report...")
            report = self.save_global_summary_report(city_results)
            
            logger.info("=" * 60)
            logger.info("Bus city segment processing completed!")
            logger.info(f"Processing summary:")
            logger.info(f"  Successfully processed cities: {self.global_stats['processed_cities']}/{self.global_stats['total_cities']}")
            logger.info(f"  Total segments generated: {self.global_stats['total_segments']}")
            logger.info(f"  Unique segments: {self.global_stats['total_unique_segments']}")
            logger.info(f"  Unique stops: {self.global_stats['total_unique_stops']}")
            logger.info(f"  Output directory: {self.shapefiles_path}/[city_folder]/")
            logger.info("=" * 60)
            
            return {
                'city_results': city_results,
                'global_stats': self.global_stats,
                'report': report
            }
            
        except Exception as e:
            logger.error(f"Processing pipeline error: {e}")
            return None


def main():
    """Main execution function for bus segment processing"""
    logger.info("=" * 60)
    logger.info("Bus City Segment Processor (Updated Version)")
    logger.info("Breaks routes into segments between consecutive stops")
    logger.info("Output format: [city_pinyin]_bus_segments.shp, [city_pinyin]_bus_stops_unique.shp")
    logger.info("Updates: Removed route fields from segments/stops, added distance field to segments")
    logger.info("=" * 60)
    
    # Check input path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    shapefiles_path = os.path.join(current_dir, "..", "dataset", "bus", "shapefiles")
    
    if not os.path.exists(shapefiles_path):
        logger.error(f"Shapefile directory not found: {shapefiles_path}")
        logger.error("Please run Bus_Data_Processor.py first to generate bus shapefile data")
        return
    
    # Check required files
    routes_file = os.path.join(shapefiles_path, "bus_routes.shp")
    stops_file = os.path.join(shapefiles_path, "bus_stops.shp")
    
    if not os.path.exists(routes_file):
        logger.error(f"Bus routes file not found: {routes_file}")
        return
    
    if not os.path.exists(stops_file):
        logger.error(f"Bus stops file not found: {stops_file}")
        return
    
    # Create processor and execute
    try:
        processor = BusSegmentProcessor()
        results = processor.process_all_cities()
        
        if results:
            logger.info("City segment processing completed!")
            logger.info("Output structure:")
            logger.info("  shapefiles/")
            logger.info("  ├── {city_folder}/")
            logger.info("  │   ├── {city_pinyin}_bus_segments.shp      (city bus segments)")
            logger.info("  │   ├── {city_pinyin}_bus_stops_unique.shp  (city unique stops)")
            logger.info("  │   └── segment_info.txt                    (city processing info)")
            logger.info("  ├── city_segment_analysis_report.json")
            logger.info("  └── city_segment_analysis_report.txt")
            
            logger.info("Output fields (updated version):")
            logger.info("Segments fields:")
            logger.info("  - s_stop_cn, s_stop_en, s_stopid: start stop information")
            logger.info("  - e_stop_cn, e_stop_en, e_stopid: end stop information")
            logger.info("  - distance: segment distance (km, 3 decimal places)")
            logger.info("  - num: number of routes using this segment")
            logger.info("  - city_cn, city_en: city information")
            logger.info("  ✗ Removed fields: route_cn, route_en, route_id")
            
            logger.info("Unique stops fields:")
            logger.info("  - stop_cn, stop_en, stop_id: stop basic information")
            logger.info("  - num: number of routes using this stop")
            logger.info("  - city_cn, city_en: city information")
            logger.info("  ✗ Removed fields: route_cn, route_en")
            
            logger.info("=== Main Updates ===")
            logger.info("✓ Segments added distance field: accurate segment distance in kilometers")
            logger.info("✓ Distance calculation: projected to Web Mercator for real distance")
            logger.info("✓ Field simplification: removed unnecessary route-related fields")
            logger.info("✓ Data aggregation: segments with same start-end points aggregated by average distance")
            logger.info("✓ Compatibility: maintains original processing logic and file structure")
        else:
            logger.error("City segment processing failed, please check error messages.")
            
    except Exception as e:
        logger.error(f"Program execution failed: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()