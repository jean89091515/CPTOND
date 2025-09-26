#!/usr/bin/env python3
"""
Metro City Shapefile Organizer

This module organizes metro network shapefile data by city into separate
folders for better data management and analysis. Creates standardized
file naming and folder structure for metro transportation data.

Dependencies:
    - geopandas
    - pandas
    - pathlib

Input:
    - Metro routes shapefile (metro_routes.shp)
    - Metro stops shapefile (metro_stops.shp)
    - Metro merged stations shapefile (metro_merged_stations.shp, optional)

Output:
    - City-wise organized shapefiles
    - Standardized file naming convention
    - City information files

Author: Urban Transportation Research Team
License: MIT
"""

import os
import geopandas as gpd
import pandas as pd
from pathlib import Path
import re
import json
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MetroCityShapefileOrganizer:
    """
    Metro city shapefile data organizer
    
    Organizes metro network shapefile data by city into separate folders
    with standardized naming conventions and metadata generation.
    """
    
    def __init__(self):
        """
        Initialize the metro shapefile organizer with fixed relative paths
        """
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.shapefiles_path = Path(os.path.join(current_dir, "..", "dataset", "metro", "shapefiles"))
        
        self.stats = {
            'total_cities': 0,
            'total_routes': 0,
            'total_stops': 0,
            'total_merged_stations': 0,
            'cities_processed': [],
            'failed_cities': []
        }
        
        logger.info(f"Metro Shapefile Organizer initialized")
        logger.info(f"Shapefile path: {self.shapefiles_path}")
    
    def city_name_to_pinyin(self, city_name):
        """
        Convert city English name to pinyin format
        
        Args:
            city_name (str): City name in English or Chinese
            
        Returns:
            str: Standardized pinyin filename
        """
        if pd.isna(city_name) or str(city_name).strip() == '':
            return 'unknown_city'
        
        city_name = str(city_name).strip()
        
        # Handle pure English names
        if re.match(r'^[a-zA-Z\s\-\.]+$', city_name):
            # Convert to lowercase and replace spaces/special chars with underscores
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
            logger.warning("pypinyin library not installed, using basic name processing for Chinese city names")
            # Basic processing for Chinese characters
            pinyin_name = re.sub(r'[^a-zA-Z0-9\s]', '_', city_name)
            pinyin_name = re.sub(r'[\s_]+', '_', pinyin_name.lower()).strip('_')
            return pinyin_name if pinyin_name else 'unknown_city'
    
    def sanitize_folder_name(self, city_name):
        """
        Clean city name to make it suitable as folder name
        
        Args:
            city_name (str): Raw city name
            
        Returns:
            str: Sanitized folder name
        """
        if pd.isna(city_name) or str(city_name).strip() == '':
            return 'unknown_city'
        
        city_name = str(city_name).strip()
        
        # Replace invalid folder name characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            city_name = city_name.replace(char, '_')
        
        # Remove leading/trailing dots and spaces
        city_name = city_name.strip('. ')
        
        if not city_name:
            city_name = 'unknown_city'
        
        return city_name
    
    def load_shapefiles(self):
        """
        Load input metro shapefile data
        
        Returns:
            tuple: (stops_gdf, routes_gdf, merged_stations_gdf)
        """
        stops_file = self.shapefiles_path / "metro_stops.shp"
        routes_file = self.shapefiles_path / "metro_routes.shp"
        merged_stations_file = self.shapefiles_path / "metro_merged_stations.shp"
        
        logger.info("Loading metro shapefile data...")
        
        # Load stops data
        if not stops_file.exists():
            logger.warning(f"Metro stops file not found: {stops_file}")
            stops_gdf = None
        else:
            try:
                logger.info(f"Loading: {stops_file}")
                stops_gdf = gpd.read_file(stops_file)
                logger.info(f"Metro stops data loaded: {len(stops_gdf)} records")
                logger.info(f"Stops data columns: {list(stops_gdf.columns)}")
            except Exception as e:
                logger.error(f"Failed to load metro stops data: {e}")
                stops_gdf = None
        
        # Load routes data
        if not routes_file.exists():
            logger.warning(f"Metro routes file not found: {routes_file}")
            routes_gdf = None
        else:
            try:
                logger.info(f"Loading: {routes_file}")
                routes_gdf = gpd.read_file(routes_file)
                logger.info(f"Metro routes data loaded: {len(routes_gdf)} records")
                logger.info(f"Routes data columns: {list(routes_gdf.columns)}")
            except Exception as e:
                logger.error(f"Failed to load metro routes data: {e}")
                routes_gdf = None
        
        # Load merged stations data (optional)
        if merged_stations_file.exists():
            try:
                logger.info(f"Loading: {merged_stations_file}")
                merged_stations_gdf = gpd.read_file(merged_stations_file)
                logger.info(f"Metro merged stations data loaded: {len(merged_stations_gdf)} records")
            except Exception as e:
                logger.error(f"Failed to load metro merged stations data: {e}")
                merged_stations_gdf = None
        else:
            logger.info("Metro merged stations file not found")
            merged_stations_gdf = None
        
        if stops_gdf is None and routes_gdf is None:
            raise Exception("No valid metro data files found")
        
        return stops_gdf, routes_gdf, merged_stations_gdf
    
    def get_unique_cities(self, stops_gdf, routes_gdf, merged_stations_gdf):
        """
        Get all unique cities from the datasets
        
        Args:
            stops_gdf (gpd.GeoDataFrame): Stops data
            routes_gdf (gpd.GeoDataFrame): Routes data
            merged_stations_gdf (gpd.GeoDataFrame): Merged stations data
            
        Returns:
            list: Sorted list of unique city names
        """
        stops_cities = set()
        routes_cities = set()
        merged_cities = set()
        
        # Extract cities from stops data
        if stops_gdf is not None and 'city_en' in stops_gdf.columns:
            stops_cities = set(stops_gdf['city_en'].dropna().unique())
        
        # Extract cities from routes data
        if routes_gdf is not None and 'city_en' in routes_gdf.columns:
            routes_cities = set(routes_gdf['city_en'].dropna().unique())
        
        # Extract cities from merged stations data
        if merged_stations_gdf is not None:
            if 'city_name' in merged_stations_gdf.columns:
                merged_cities = set(merged_stations_gdf['city_name'].dropna().unique())
            elif 'city_en' in merged_stations_gdf.columns:
                merged_cities = set(merged_stations_gdf['city_en'].dropna().unique())
        
        # Combine city lists
        all_cities = stops_cities.union(routes_cities).union(merged_cities)
        
        # Filter empty values
        all_cities = {city for city in all_cities if city and str(city).strip() != ''}
        
        logger.info(f"Found cities: {len(all_cities)}")
        logger.info(f"Cities from stops data: {len(stops_cities)}")
        logger.info(f"Cities from routes data: {len(routes_cities)}")
        logger.info(f"Cities from merged stations data: {len(merged_cities)}")
        
        return sorted(list(all_cities))
    
    def process_city_data(self, city_en, stops_gdf, routes_gdf, merged_stations_gdf):
        """
        Process metro data for a single city
        
        Args:
            city_en (str): City English name
            stops_gdf (gpd.GeoDataFrame): Stops data
            routes_gdf (gpd.GeoDataFrame): Routes data
            merged_stations_gdf (gpd.GeoDataFrame): Merged stations data
            
        Returns:
            bool: True if processing successful
        """
        logger.info(f"Processing city: {city_en}")
        
        # Clean city name for folder
        folder_name = self.sanitize_folder_name(city_en)
        city_output_path = self.shapefiles_path / folder_name
        
        # Get city pinyin name for file naming
        city_pinyin = self.city_name_to_pinyin(city_en)
        logger.info(f"City pinyin: {city_pinyin}")
        
        # Create city folder
        city_output_path.mkdir(parents=True, exist_ok=True)
        
        success_count = 0
        
        # Filter and save city stops data
        if stops_gdf is not None and 'city_en' in stops_gdf.columns:
            city_stops = stops_gdf[stops_gdf['city_en'] == city_en].copy()
            logger.info(f"City metro stops: {len(city_stops)}")
            
            if len(city_stops) > 0:
                try:
                    stops_output = city_output_path / f"{city_pinyin}_metro_stops.shp"
                    city_stops.to_file(stops_output, encoding='utf-8')
                    logger.info(f"Metro stops data saved: {stops_output}")
                    success_count += 1
                    self.stats['total_stops'] += len(city_stops)
                except Exception as e:
                    logger.error(f"Failed to save metro stops data: {e}")
            else:
                logger.info(f"No metro stops data for this city")
        
        # Filter and save city routes data
        if routes_gdf is not None and 'city_en' in routes_gdf.columns:
            city_routes = routes_gdf[routes_gdf['city_en'] == city_en].copy()
            logger.info(f"City metro routes: {len(city_routes)}")
            
            if len(city_routes) > 0:
                try:
                    routes_output = city_output_path / f"{city_pinyin}_metro_routes.shp"
                    city_routes.to_file(routes_output, encoding='utf-8')
                    logger.info(f"Metro routes data saved: {routes_output}")
                    success_count += 1
                    self.stats['total_routes'] += len(city_routes)
                except Exception as e:
                    logger.error(f"Failed to save metro routes data: {e}")
            else:
                logger.info(f"No metro routes data for this city")
        
        # Filter and save city merged stations data (if available)
        if merged_stations_gdf is not None:
            city_merged = None
            
            # Try different city field names
            if 'city_name' in merged_stations_gdf.columns:
                city_merged = merged_stations_gdf[merged_stations_gdf['city_name'] == city_en].copy()
            elif 'city_en' in merged_stations_gdf.columns:
                city_merged = merged_stations_gdf[merged_stations_gdf['city_en'] == city_en].copy()
            
            if city_merged is not None and len(city_merged) > 0:
                logger.info(f"City merged stations: {len(city_merged)}")
                try:
                    merged_output = city_output_path / f"{city_pinyin}_metro_merged_stations.shp"
                    city_merged.to_file(merged_output, encoding='utf-8')
                    logger.info(f"Metro merged stations data saved: {merged_output}")
                    success_count += 1
                    self.stats['total_merged_stations'] += len(city_merged)
                except Exception as e:
                    logger.error(f"Failed to save metro merged stations data: {e}")
            else:
                logger.info(f"No metro merged stations data for this city")
        
        # Create city information file
        try:
            info_file = city_output_path / "city_info.txt"
            with open(info_file, 'w', encoding='utf-8') as f:
                f.write(f"Metro City Information\n")
                f.write(f"=" * 40 + "\n")
                f.write(f"City English Name: {city_en}\n")
                f.write(f"City Pinyin: {city_pinyin}\n")
                f.write(f"Folder Name: {folder_name}\n")
                f.write(f"Transport Type: Metro/Subway\n")
                
                # Calculate statistics
                stops_count = len(stops_gdf[stops_gdf['city_en'] == city_en]) if stops_gdf is not None and 'city_en' in stops_gdf.columns else 0
                routes_count = len(routes_gdf[routes_gdf['city_en'] == city_en]) if routes_gdf is not None and 'city_en' in routes_gdf.columns else 0
                merged_count = 0
                
                if merged_stations_gdf is not None:
                    if 'city_name' in merged_stations_gdf.columns:
                        merged_count = len(merged_stations_gdf[merged_stations_gdf['city_name'] == city_en])
                    elif 'city_en' in merged_stations_gdf.columns:
                        merged_count = len(merged_stations_gdf[merged_stations_gdf['city_en'] == city_en])
                
                f.write(f"Metro stops count: {stops_count}\n")
                f.write(f"Metro routes count: {routes_count}\n")
                f.write(f"Metro merged stations count: {merged_count}\n")
                
                # Add file naming description
                f.write(f"\nFile naming format:\n")
                f.write(f"  Stops file: {city_pinyin}_metro_stops.shp\n")
                f.write(f"  Routes file: {city_pinyin}_metro_routes.shp\n")
                
                if merged_count > 0:
                    f.write(f"  Merged stations file: {city_pinyin}_metro_merged_stations.shp\n")
                
                f.write(f"\nCreation time: {pd.Timestamp.now().isoformat()}\n")
                f.write(f"Coordinate system: WGS84 (EPSG:4326)\n")
                
                # Add data bounds information
                if stops_gdf is not None and 'city_en' in stops_gdf.columns:
                    city_stops_bounds = stops_gdf[stops_gdf['city_en'] == city_en]
                    if len(city_stops_bounds) > 0:
                        bounds = city_stops_bounds.total_bounds
                        f.write(f"\nMetro stops data bounds:\n")
                        f.write(f"  Longitude range: {bounds[0]:.6f} ~ {bounds[2]:.6f}\n")
                        f.write(f"  Latitude range: {bounds[1]:.6f} ~ {bounds[3]:.6f}\n")
                
                if routes_gdf is not None and 'city_en' in routes_gdf.columns:
                    city_routes_bounds = routes_gdf[routes_gdf['city_en'] == city_en]
                    if len(city_routes_bounds) > 0:
                        bounds = city_routes_bounds.total_bounds
                        f.write(f"\nMetro routes data bounds:\n")
                        f.write(f"  Longitude range: {bounds[0]:.6f} ~ {bounds[2]:.6f}\n")
                        f.write(f"  Latitude range: {bounds[1]:.6f} ~ {bounds[3]:.6f}\n")
            
            logger.info(f"City information file saved: {info_file}")
            
        except Exception as e:
            logger.error(f"Failed to save city information file: {e}")
        
        if success_count > 0:
            self.stats['cities_processed'].append(city_en)
            logger.info(f"City {city_en} processing completed")
        else:
            self.stats['failed_cities'].append(city_en)
            logger.error(f"City {city_en} processing failed")
        
        return success_count > 0
    
    def create_summary_report(self):
        """
        Create summary report
        
        Returns:
            dict: Summary report data
        """
        logger.info("Generating summary report...")
        
        report_data = {
            'processing_summary': {
                'dataset_type': 'Metro/Subway Network Data',
                'total_cities_found': self.stats['total_cities'],
                'cities_successfully_processed': len(self.stats['cities_processed']),
                'cities_failed': len(self.stats['failed_cities']),
                'total_routes_organized': self.stats['total_routes'],
                'total_stops_organized': self.stats['total_stops'],
                'total_merged_stations_organized': self.stats['total_merged_stations'],
                'processing_time': pd.Timestamp.now().isoformat(),
                'file_naming_format': {
                    'stops': '{city_pinyin}_metro_stops.shp',
                    'routes': '{city_pinyin}_metro_routes.shp',
                    'merged_stations': '{city_pinyin}_metro_merged_stations.shp'
                }
            },
            'successfully_processed_cities': self.stats['cities_processed'],
            'failed_cities': self.stats['failed_cities']
        }
        
        # Save JSON format report
        report_file = self.shapefiles_path / "metro_organization_summary.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        # Save text format report
        txt_report_file = self.shapefiles_path / "metro_organization_summary.txt"
        with open(txt_report_file, 'w', encoding='utf-8') as f:
            f.write("Metro City Shapefile Data Organization Report\n")
            f.write("=" * 60 + "\n\n")
            
            f.write(f"Dataset Type: {report_data['processing_summary']['dataset_type']}\n")
            f.write(f"Processing Time: {pd.Timestamp.now().isoformat()}\n")
            f.write(f"Metro Shapefile Path: {self.shapefiles_path}\n\n")
            
            f.write("Processing Statistics:\n")
            f.write(f"  Total cities found: {self.stats['total_cities']}\n")
            f.write(f"  Successfully processed cities: {len(self.stats['cities_processed'])}\n")
            f.write(f"  Failed cities: {len(self.stats['failed_cities'])}\n")
            f.write(f"  Total metro routes organized: {self.stats['total_routes']}\n")
            f.write(f"  Total metro stops organized: {self.stats['total_stops']}\n")
            f.write(f"  Total merged stations organized: {self.stats['total_merged_stations']}\n\n")
            
            f.write("File Naming Format:\n")
            f.write(f"  Stops file: [city_pinyin]_metro_stops.shp\n")
            f.write(f"  Routes file: [city_pinyin]_metro_routes.shp\n")
            f.write(f"  Merged stations file: [city_pinyin]_metro_merged_stations.shp\n")
            f.write(f"  Example: beijing_metro_stops.shp, shanghai_metro_routes.shp\n\n")
            
            if self.stats['cities_processed']:
                f.write("Successfully Processed Cities:\n")
                for city in self.stats['cities_processed']:
                    city_pinyin = self.city_name_to_pinyin(city)
                    f.write(f"  - {city} (pinyin: {city_pinyin})\n")
                f.write("\n")
            
            if self.stats['failed_cities']:
                f.write("Failed Cities:\n")
                for city in self.stats['failed_cities']:
                    f.write(f"  - {city}\n")
                f.write("\n")
            
            f.write("Data Description:\n")
            f.write("  - Transport Type: Metro/Subway\n")
            f.write("  - Coordinate System: WGS84 (EPSG:4326)\n")
            f.write("  - Each city folder contains:\n")
            f.write("    * [city_pinyin]_metro_stops.shp (city metro stops)\n")
            f.write("    * [city_pinyin]_metro_routes.shp (city metro routes)\n")
            f.write("    * [city_pinyin]_metro_merged_stations.shp (merged stations, if available)\n")
            f.write("    * city_info.txt (city information)\n")
            f.write("  - Folder naming: Based on city_en field, cleaned special characters\n")
            f.write("  - File naming: Based on pinyin conversion of English city names\n")
            f.write("  - Original data preserved in shapefiles root directory\n")
        
        logger.info(f"Report saved: {report_file}")
        logger.info(f"Report saved: {txt_report_file}")
        
        return report_data
    
    def organize_by_city(self):
        """
        Main processing function: organize metro shapefiles by city
        
        Returns:
            dict: Processing results and statistics
        """
        logger.info("Starting metro shapefile organization by city...")
        logger.info("=" * 60)
        
        try:
            # Check if shapefiles directory exists
            if not self.shapefiles_path.exists():
                raise FileNotFoundError(f"Metro shapefile directory not found: {self.shapefiles_path}")
            
            # 1. Load data
            stops_gdf, routes_gdf, merged_stations_gdf = self.load_shapefiles()
            
            # 2. Get city list
            cities = self.get_unique_cities(stops_gdf, routes_gdf, merged_stations_gdf)
            self.stats['total_cities'] = len(cities)
            
            if not cities:
                logger.error("No city data found!")
                return None
            
            logger.info(f"Starting to process {len(cities)} cities...")
            logger.info(f"City list: {cities[:10] if len(cities) > 10 else cities}")
            if len(cities) > 10:
                logger.info(f"... and {len(cities) - 10} more cities")
            
            # 3. Process cities individually
            success_count = 0
            for i, city_en in enumerate(cities, 1):
                logger.info(f"Progress: {i}/{len(cities)}")
                
                try:
                    if self.process_city_data(city_en, stops_gdf, routes_gdf, merged_stations_gdf):
                        success_count += 1
                except Exception as e:
                    logger.error(f"Error processing city {city_en}: {e}")
                    self.stats['failed_cities'].append(city_en)
            
            # 4. Generate report
            logger.info("=" * 60)
            logger.info("Metro data organization completed!")
            report = self.create_summary_report()
            
            # 5. Display result summary
            logger.info(f"Processing Results Summary:")
            logger.info(f"  ✓ Successfully processed cities: {success_count}/{len(cities)}")
            logger.info(f"  ✓ Total metro routes: {self.stats['total_routes']}")
            logger.info(f"  ✓ Total metro stops: {self.stats['total_stops']}")
            logger.info(f"  ✓ Total merged stations: {self.stats['total_merged_stations']}")
            logger.info(f"  ✓ Output directory: {self.shapefiles_path}")
            logger.info(f"  ✓ File naming format: [city_pinyin]_metro_stops.shp, [city_pinyin]_metro_routes.shp")
            
            if self.stats['failed_cities']:
                logger.warning(f"  ⚠️  Failed cities: {len(self.stats['failed_cities'])}")
                logger.warning(f"     Failed cities: {', '.join(self.stats['failed_cities'][:5])}")
                if len(self.stats['failed_cities']) > 5:
                    logger.warning(f"     ... and {len(self.stats['failed_cities']) - 5} more")
            
            logger.info("=" * 60)
            
            return report
            
        except Exception as e:
            logger.error(f"Error during processing: {e}")
            import traceback
            traceback.print_exc()
            return None


def main():
    """
    Main function
    """
    logger.info("=" * 60)
    logger.info("Metro City Shapefile Data Organizer")
    logger.info("Classify metro network data by city")
    logger.info("File naming format: [city_pinyin]_metro_stops.shp, [city_pinyin]_metro_routes.shp")
    logger.info("=" * 60)
    
    # Check input path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    shapefiles_path = os.path.join(current_dir, "..", "dataset", "metro", "shapefiles")
    
    if not os.path.exists(shapefiles_path):
        logger.error(f"Error: Metro shapefile directory not found: {shapefiles_path}")
        logger.error("Please ensure Metro_Data_Processor.py has been run to generate metro shapefile data")
        return
    
    # Create organizer and execute
    try:
        organizer = MetroCityShapefileOrganizer()
        results = organizer.organize_by_city()
        
        if results:
            logger.info("Organization completed! Metro data for each city has been saved to corresponding folders.")
            logger.info("File structure:")
            logger.info("  shapefiles/")
            logger.info("  ├── metro_stops.shp           (original metro stops data)")
            logger.info("  ├── metro_routes.shp          (original metro routes data)")
            logger.info("  ├── metro_merged_stations.shp (original merged stations data, if available)")
            logger.info("  ├── {city_name}/")
            logger.info("  │   ├── {city_pinyin}_metro_stops.shp      (city metro stops)")
            logger.info("  │   ├── {city_pinyin}_metro_routes.shp     (city metro routes)")
            logger.info("  │   ├── {city_pinyin}_metro_merged_stations.shp (city merged stations, if available)")
            logger.info("  │   └── city_info.txt                      (city information)")
            logger.info("  ├── metro_organization_summary.json")
            logger.info("  └── metro_organization_summary.txt")
            logger.info("File naming examples:")
            logger.info("  - beijing_metro_stops.shp")
            logger.info("  - shanghai_metro_routes.shp")
            logger.info("  - new_york_metro_stops.shp")
        else:
            logger.error("Organization process failed, please check error messages.")
            
    except Exception as e:
        logger.error(f"Program execution failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()