#!/usr/bin/env python3
"""
Bus City Shapefile Organizer (Fixed Version)

This module organizes bus network shapefile data by city, creating separate
folders for each city containing their respective bus stops and routes data.
Fixed to handle duplicate city names with different cases.

Dependencies:
    - geopandas
    - pandas
    - pathlib
    - shutil

Input:
    - bus_routes.shp (consolidated bus routes shapefile)
    - bus_stops.shp (consolidated bus stops shapefile)

Output:
    - City-organized folder structure with individual shapefiles
    - Standardized file naming convention
    - Processing summary reports

Author: Urban Transportation Research Team
License: MIT
"""

import os
import geopandas as gpd
import pandas as pd
import shutil
import json
from pathlib import Path
import re
import logging
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BusCityShapefileOrganizer:
    """
    Bus city shapefile data organizer
    
    Organizes bus network shapefile data by city into separate folders
    with standardized naming conventions for urban transportation research.
    
    Features:
    - City-based data organization with case-insensitive city name handling
    - Standardized file naming using pinyin conversion
    - Comprehensive processing reports
    - Data validation and error handling
    """
    
    def __init__(self, data_path=None):
        """
        Initialize the bus city shapefile organizer
        
        Args:
            data_path (str, optional): Path to shapefile data directory
        """
        # Use relative path if not provided
        if data_path is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            data_path = os.path.join(current_dir, "..", "dataset", "bus")
        
        self.data_path = Path(data_path)
        self.shapefiles_path = self.data_path / "shapefiles"
        
        self.stats = {
            'total_cities': 0,
            'total_routes': 0,
            'total_stops': 0,
            'cities_processed': [],
            'failed_cities': []
        }
        
        # Store city name mapping (lowercase -> standardized name)
        self.city_name_map = {}
        
        logger.info(f"Bus shapefile organizer initialized")
        logger.info(f"Shapefiles path: {self.shapefiles_path}")
    
    def normalize_city_name(self, city_name):
        """
        Normalize city name to standard format (Title Case)
        
        Handles case inconsistencies in city names to avoid duplicates.
        
        Args:
            city_name (str): Original city name
            
        Returns:
            str: Normalized city name in Title Case
        """
        if pd.isna(city_name) or str(city_name).strip() == '':
            return None
        
        city_name = str(city_name).strip()
        
        # Convert to Title Case for standardization
        # This handles "beijing" -> "Beijing", "BEIJING" -> "Beijing"
        normalized = city_name.title()
        
        return normalized
    
    def city_name_to_pinyin(self, city_name):
        """
        Convert city English name to pinyin format for file naming
        
        Handles both English and Chinese city names, converting them to
        standardized lowercase pinyin format suitable for file naming.
        
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
            # Remove excessive underscores
            pinyin_name = re.sub(r'_+', '_', pinyin_name).strip('_')
            return pinyin_name
        
        # Handle Chinese characters with pypinyin if available
        try:
            from pypinyin import lazy_pinyin, Style
            # Get pinyin without tone marks
            pinyin_list = lazy_pinyin(city_name, style=Style.NORMAL)
            # Join pinyin and convert to lowercase
            pinyin_name = '_'.join(pinyin_list).lower()
            # Clean special characters
            pinyin_name = re.sub(r'[^a-z0-9_]', '_', pinyin_name)
            pinyin_name = re.sub(r'_+', '_', pinyin_name).strip('_')
            return pinyin_name
        except ImportError:
            logger.warning("pypinyin library not installed, using basic processing for Chinese city names")
            # Fallback: keep alphanumeric and replace others with underscores
            pinyin_name = re.sub(r'[^a-zA-Z0-9\s]', '_', city_name)
            pinyin_name = re.sub(r'[\s_]+', '_', pinyin_name.lower()).strip('_')
            return pinyin_name if pinyin_name else 'unknown_city'
    
    def sanitize_folder_name(self, city_name):
        """
        Clean city name to make it suitable for folder naming
        
        Removes invalid filesystem characters and ensures compatibility
        across different operating systems.
        
        Args:
            city_name (str): Original city name
            
        Returns:
            str: Sanitized folder name
        """
        if pd.isna(city_name) or str(city_name).strip() == '':
            return 'unknown_city'
        
        # Clean special characters
        city_name = str(city_name).strip()
        # Replace Windows/Linux unsupported folder name characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            city_name = city_name.replace(char, '_')
        
        # Remove leading/trailing spaces and dots
        city_name = city_name.strip('. ')
        
        # Use default name if empty
        if not city_name:
            city_name = 'unknown_city'
        
        return city_name
    
    def load_shapefiles(self):
        """
        Load input bus shapefile data
        
        Returns:
            tuple: (stops_gdf, routes_gdf) GeoDataFrames
            
        Raises:
            FileNotFoundError: If required shapefile not found
            Exception: If data loading fails
        """
        stops_file = self.shapefiles_path / "bus_stops.shp"
        routes_file = self.shapefiles_path / "bus_routes.shp"
        
        logger.info("Loading bus shapefile data...")
        
        # Check file existence
        if not stops_file.exists():
            raise FileNotFoundError(f"Bus stops file not found: {stops_file}")
        
        if not routes_file.exists():
            raise FileNotFoundError(f"Bus routes file not found: {routes_file}")
        
        # Load data
        try:
            logger.info(f"Loading: {stops_file}")
            stops_gdf = gpd.read_file(stops_file)
            logger.info(f"Bus stops data loaded: {len(stops_gdf)} records")
            
            logger.info(f"Loading: {routes_file}")
            routes_gdf = gpd.read_file(routes_file)
            logger.info(f"Bus routes data loaded: {len(routes_gdf)} records")
            
            return stops_gdf, routes_gdf
            
        except Exception as e:
            raise Exception(f"Error loading bus shapefiles: {e}")
    
    def get_unique_cities(self, stops_gdf, routes_gdf):
        """
        Extract unique cities from the datasets with case normalization
        
        Args:
            stops_gdf (gpd.GeoDataFrame): Bus stops data
            routes_gdf (gpd.GeoDataFrame): Bus routes data
            
        Returns:
            list: Sorted list of unique normalized city names
        """
        normalized_cities = {}  # normalized_name -> original_names
        
        # Extract and normalize cities from stops data
        if 'city_en' in stops_gdf.columns:
            for city in stops_gdf['city_en'].dropna().unique():
                normalized = self.normalize_city_name(city)
                if normalized:
                    if normalized not in normalized_cities:
                        normalized_cities[normalized] = []
                    normalized_cities[normalized].append(city)
        
        # Extract and normalize cities from routes data
        if 'city_en' in routes_gdf.columns:
            for city in routes_gdf['city_en'].dropna().unique():
                normalized = self.normalize_city_name(city)
                if normalized:
                    if normalized not in normalized_cities:
                        normalized_cities[normalized] = []
                    if city not in normalized_cities[normalized]:
                        normalized_cities[normalized].append(city)
        
        # Build city name mapping and log duplicates
        for normalized, originals in normalized_cities.items():
            if len(originals) > 1:
                logger.warning(f"Found duplicate city names (case variations): {normalized} <- {originals}")
            # Store the mapping: lowercase -> normalized
            self.city_name_map[normalized.lower()] = normalized
            for orig in originals:
                self.city_name_map[orig.lower()] = normalized
        
        unique_cities = sorted(list(normalized_cities.keys()))
        
        logger.info(f"Found {len(unique_cities)} unique cities (after normalization)")
        logger.info(f"Total city name variations before normalization: {sum(len(v) for v in normalized_cities.values())}")
        
        return unique_cities
    
    def process_city_data(self, city_normalized, stops_gdf, routes_gdf):
        """
        Process bus data for a single city (using normalized name)
        
        Creates city-specific folder and saves filtered bus data with
        standardized naming convention. Handles case-insensitive matching.
        
        Args:
            city_normalized (str): Normalized city name
            stops_gdf (gpd.GeoDataFrame): Bus stops data
            routes_gdf (gpd.GeoDataFrame): Bus routes data
            
        Returns:
            bool: True if processing successful, False otherwise
        """
        logger.info(f"Processing city: {city_normalized}")
        
        # Clean city name for folder naming
        folder_name = self.sanitize_folder_name(city_normalized)
        city_output_path = self.shapefiles_path / folder_name
        
        # Get city pinyin name for file naming
        city_pinyin = self.city_name_to_pinyin(city_normalized)
        logger.info(f"City pinyin: {city_pinyin}")
        
        # Create city folder
        city_output_path.mkdir(parents=True, exist_ok=True)
        
        # Filter city stops data (case-insensitive)
        city_stops = None
        if 'city_en' in stops_gdf.columns:
            # Use case-insensitive matching
            mask = stops_gdf['city_en'].str.lower() == city_normalized.lower()
            city_stops = stops_gdf[mask].copy()
            logger.info(f"City bus stops count: {len(city_stops)}")
        
        # Filter city routes data (case-insensitive)
        city_routes = None
        if 'city_en' in routes_gdf.columns:
            # Use case-insensitive matching
            mask = routes_gdf['city_en'].str.lower() == city_normalized.lower()
            city_routes = routes_gdf[mask].copy()
            logger.info(f"City bus routes count: {len(city_routes)}")
        
        success_count = 0
        
        # Save stops data
        if city_stops is not None and len(city_stops) > 0:
            try:
                # Use standardized file naming format
                stops_output = city_output_path / f"{city_pinyin}_bus_stops.shp"
                city_stops.to_file(stops_output, encoding='utf-8')
                logger.info(f"Bus stops data saved: {stops_output}")
                success_count += 1
                self.stats['total_stops'] += len(city_stops)
            except Exception as e:
                logger.error(f"Failed to save bus stops data: {e}")
        else:
            logger.info("No bus stops data for this city")
        
        # Save routes data
        if city_routes is not None and len(city_routes) > 0:
            try:
                # Use standardized file naming format
                routes_output = city_output_path / f"{city_pinyin}_bus_routes.shp"
                city_routes.to_file(routes_output, encoding='utf-8')
                logger.info(f"Bus routes data saved: {routes_output}")
                success_count += 1
                self.stats['total_routes'] += len(city_routes)
            except Exception as e:
                logger.error(f"Failed to save bus routes data: {e}")
        else:
            logger.info("No bus routes data for this city")
        
        # Create city information file
        try:
            info_file = city_output_path / "city_info.txt"
            with open(info_file, 'w', encoding='utf-8') as f:
                f.write(f"Bus City Information\n")
                f.write(f"=" * 40 + "\n")
                f.write(f"City English Name: {city_normalized}\n")
                f.write(f"City Pinyin: {city_pinyin}\n")
                f.write(f"Folder Name: {folder_name}\n")
                f.write(f"Transportation Type: Bus/Public Transit\n")
                f.write(f"Bus Stops Count: {len(city_stops) if city_stops is not None else 0}\n")
                f.write(f"Bus Routes Count: {len(city_routes) if city_routes is not None else 0}\n")
                
                # Add file naming description
                f.write(f"\nFile Naming Format:\n")
                f.write(f"  Stops file: {city_pinyin}_bus_stops.shp\n")
                f.write(f"  Routes file: {city_pinyin}_bus_routes.shp\n")
                
                f.write(f"\nCreation Time: {pd.Timestamp.now().isoformat()}\n")
                f.write(f"Coordinate System: WGS84 (EPSG:4326)\n")
                
                # Add data extent information
                if city_stops is not None and len(city_stops) > 0:
                    bounds = city_stops.total_bounds
                    f.write(f"\nBus Stops Data Extent:\n")
                    f.write(f"  Longitude Range: {bounds[0]:.6f} ~ {bounds[2]:.6f}\n")
                    f.write(f"  Latitude Range: {bounds[1]:.6f} ~ {bounds[3]:.6f}\n")
                
                if city_routes is not None and len(city_routes) > 0:
                    bounds = city_routes.total_bounds
                    f.write(f"\nBus Routes Data Extent:\n")
                    f.write(f"  Longitude Range: {bounds[0]:.6f} ~ {bounds[2]:.6f}\n")
                    f.write(f"  Latitude Range: {bounds[1]:.6f} ~ {bounds[3]:.6f}\n")
            
            logger.info(f"City information file saved: {info_file}")
            
        except Exception as e:
            logger.error(f"Failed to save city information file: {e}")
        
        if success_count > 0:
            self.stats['cities_processed'].append(city_normalized)
            logger.info(f"City {city_normalized} processing completed")
            return True
        else:
            self.stats['failed_cities'].append(city_normalized)
            logger.error(f"City {city_normalized} processing failed")
            return False
    
    def create_summary_report(self):
        """
        Create comprehensive processing summary report
        
        Generates both JSON and text format reports with processing
        statistics and file organization details.
        
        Returns:
            dict: Report data dictionary
        """
        logger.info("Generating summary report...")
        
        report_data = {
            'processing_summary': {
                'dataset_type': 'Bus/Public Transit Network Data',
                'total_cities_found': self.stats['total_cities'],
                'cities_successfully_processed': len(self.stats['cities_processed']),
                'cities_failed': len(self.stats['failed_cities']),
                'total_routes_organized': self.stats['total_routes'],
                'total_stops_organized': self.stats['total_stops'],
                'processing_time': pd.Timestamp.now().isoformat(),
                'file_naming_format': {
                    'stops': '{city_pinyin}_bus_stops.shp',
                    'routes': '{city_pinyin}_bus_routes.shp'
                },
                'coordinate_system': 'WGS84 (EPSG:4326)',
                'organization_method': 'City-based folder structure with standardized naming (case-insensitive)'
            },
            'successfully_processed_cities': self.stats['cities_processed'],
            'failed_cities': self.stats['failed_cities'],
            'data_structure': {
                'folder_naming': 'Based on normalized city_en field (Title Case)',
                'file_naming': 'Based on pinyin conversion of city names',
                'original_data_location': 'shapefiles root directory',
                'organized_data_location': 'shapefiles/{city_folder}/',
                'case_handling': 'Case-insensitive city name matching to avoid duplicates'
            }
        }
        
        # Save JSON format report
        report_file = self.shapefiles_path / "bus_organization_summary.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        # Save text format report
        txt_report_file = self.shapefiles_path / "bus_organization_summary.txt"
        with open(txt_report_file, 'w', encoding='utf-8') as f:
            f.write("Bus City Shapefile Data Organization Report\n")
            f.write("=" * 60 + "\n\n")
            
            f.write(f"Dataset Type: {report_data['processing_summary']['dataset_type']}\n")
            f.write(f"Processing Time: {pd.Timestamp.now().isoformat()}\n")
            f.write(f"Bus Shapefiles Path: {self.shapefiles_path}\n")
            f.write(f"Coordinate System: {report_data['processing_summary']['coordinate_system']}\n\n")
            
            f.write("Processing Statistics:\n")
            f.write(f"  Total Cities Found: {self.stats['total_cities']}\n")
            f.write(f"  Successfully Processed Cities: {len(self.stats['cities_processed'])}\n")
            f.write(f"  Failed Processing Cities: {len(self.stats['failed_cities'])}\n")
            f.write(f"  Total Bus Routes Organized: {self.stats['total_routes']}\n")
            f.write(f"  Total Bus Stops Organized: {self.stats['total_stops']}\n\n")
            
            f.write("File Naming Convention:\n")
            f.write(f"  Stops files: [city_pinyin]_bus_stops.shp\n")
            f.write(f"  Routes files: [city_pinyin]_bus_routes.shp\n")
            f.write(f"  Examples: beijing_bus_stops.shp, shanghai_bus_routes.shp\n\n")
            
            f.write("Organization Structure:\n")
            f.write(f"  Folder naming: Based on normalized city_en field (Title Case)\n")
            f.write(f"  File naming: Based on pinyin conversion\n")
            f.write(f"  Case handling: Case-insensitive matching to avoid duplicates\n")
            f.write(f"  Original data: Preserved in shapefiles root directory\n")
            f.write(f"  Organized data: Located in shapefiles/{{city_folder}}/\n\n")
            
            if self.stats['cities_processed']:
                f.write("Successfully Processed Cities:\n")
                for city in self.stats['cities_processed']:
                    city_pinyin = self.city_name_to_pinyin(city)
                    f.write(f"  - {city} (pinyin: {city_pinyin})\n")
                f.write("\n")
            
            if self.stats['failed_cities']:
                f.write("Failed Processing Cities:\n")
                for city in self.stats['failed_cities']:
                    f.write(f"  - {city}\n")
                f.write("\n")
            
            f.write("Data Description:\n")
            f.write("  - Transportation Type: Bus/Public Transit\n")
            f.write("  - Coordinate System: WGS84 (EPSG:4326)\n")
            f.write("  - Each city folder contains:\n")
            f.write("    * [city_pinyin]_bus_stops.shp (city bus stops)\n")
            f.write("    * [city_pinyin]_bus_routes.shp (city bus routes)\n")
            f.write("    * city_info.txt (city information and metadata)\n")
            f.write("  - Folder naming: Based on normalized city_en field\n")
            f.write("  - File naming: Based on English-to-pinyin conversion of city names\n")
            f.write("  - Case handling: Normalized to Title Case to prevent duplicates\n")
            f.write("  - Original consolidated data preserved in shapefiles root directory\n")
            f.write("  - Quality assurance: Data validation and error handling implemented\n")
        
        logger.info(f"Summary report saved: {report_file}")
        logger.info(f"Summary report saved: {txt_report_file}")
        
        return report_data
    
    def organize_by_city(self):
        """
        Main processing function: organize bus shapefile data by city
        
        Executes the complete workflow of loading data, extracting cities,
        processing each city's data, and generating summary reports.
        
        Returns:
            dict: Processing results and statistics, None if failed
        """
        logger.info("Starting bus shapefile data organization by city...")
        logger.info("=" * 60)
        
        try:
            # Check shapefiles directory existence
            if not self.shapefiles_path.exists():
                raise FileNotFoundError(f"Bus shapefiles directory not found: {self.shapefiles_path}")
            
            # 1. Load data
            stops_gdf, routes_gdf = self.load_shapefiles()
            
            # 2. Get city list (normalized, without duplicates)
            cities = self.get_unique_cities(stops_gdf, routes_gdf)
            self.stats['total_cities'] = len(cities)
            
            if not cities:
                logger.error("No city data found!")
                return None
            
            logger.info(f"Starting processing of {len(cities)} cities...")
            logger.info(f"City list preview: {cities[:10] if len(cities) > 10 else cities}")
            if len(cities) > 10:
                logger.info(f"... and {len(cities) - 10} more cities")
            
            # 3. Process cities individually
            success_count = 0
            for i, city_normalized in enumerate(cities, 1):
                logger.info(f"Progress: {i}/{len(cities)}")
                
                try:
                    if self.process_city_data(city_normalized, stops_gdf, routes_gdf):
                        success_count += 1
                except Exception as e:
                    logger.error(f"Error processing city {city_normalized}: {e}")
                    self.stats['failed_cities'].append(city_normalized)
            
            # 4. Generate reports
            logger.info("=" * 60)
            logger.info("Bus data organization completed!")
            report = self.create_summary_report()
            
            # 5. Display results summary
            logger.info("Processing Results Summary:")
            logger.info(f"  Successfully processed cities: {success_count}/{len(cities)}")
            logger.info(f"  Total bus routes organized: {self.stats['total_routes']}")
            logger.info(f"  Total bus stops organized: {self.stats['total_stops']}")
            logger.info(f"  Output directory: {self.shapefiles_path}")
            logger.info(f"  File naming format: [city_pinyin]_bus_stops.shp, [city_pinyin]_bus_routes.shp")
            
            if self.stats['failed_cities']:
                logger.warning(f"Failed processing cities: {len(self.stats['failed_cities'])}")
                logger.warning(f"Failed cities: {', '.join(self.stats['failed_cities'][:5])}")
                if len(self.stats['failed_cities']) > 5:
                    logger.warning(f"... and {len(self.stats['failed_cities']) - 5} more")
            
            logger.info("=" * 60)
            
            return report
            
        except Exception as e:
            logger.error(f"Error during processing: {e}")
            traceback.print_exc()
            return None


def main():
    """
    Main execution function for bus city shapefile organization
    
    Validates input requirements and executes the complete organization
    workflow with comprehensive error handling and user feedback.
    """
    logger.info("=" * 60)
    logger.info("Bus City Shapefile Data Organizer (Fixed Version)")
    logger.info("Organizes bus network data by city with case-insensitive matching")
    logger.info("File naming format: [city_pinyin]_bus_stops.shp, [city_pinyin]_bus_routes.shp")
    logger.info("=" * 60)
    
    # Check input path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    shapefiles_path = os.path.join(current_dir, "..", "dataset", "bus", "shapefiles")
    
    if not os.path.exists(shapefiles_path):
        logger.error(f"Bus shapefiles directory not found: {shapefiles_path}")
        logger.error("Please ensure Bus_Data_Processor.py has been run to generate bus shapefile data")
        return
    
    # Check required files
    required_files = ["bus_stops.shp", "bus_routes.shp"]
    missing_files = []
    
    for file_name in required_files:
        file_path = os.path.join(shapefiles_path, file_name)
        if not os.path.exists(file_path):
            missing_files.append(file_name)
    
    if missing_files:
        logger.error(f"Required files missing: {', '.join(missing_files)}")
        logger.error("Please ensure all required shapefiles are present")
        return
    
    # Create organizer and execute
    try:
        organizer = BusCityShapefileOrganizer()
        results = organizer.organize_by_city()
        
        if results:
            logger.info("Organization completed! City-specific bus data saved to respective folders.")
            logger.info("File Structure:")
            logger.info("  shapefiles/")
            logger.info("  ├── bus_stops.shp           (original consolidated bus stops)")
            logger.info("  ├── bus_routes.shp          (original consolidated bus routes)")
            logger.info("  ├── {city_name}/")
            logger.info("  │   ├── {city_pinyin}_bus_stops.shp      (city bus stops)")
            logger.info("  │   ├── {city_pinyin}_bus_routes.shp     (city bus routes)")
            logger.info("  │   └── city_info.txt                    (city metadata)")
            logger.info("  ├── bus_organization_summary.json")
            logger.info("  └── bus_organization_summary.txt")
            logger.info("")
            logger.info("File Naming Examples:")
            logger.info("  - beijing_bus_stops.shp")
            logger.info("  - shanghai_bus_routes.shp")
            logger.info("  - new_york_bus_stops.shp")
            logger.info("")
            logger.info("Features:")
            logger.info("  ✓ Standardized pinyin-based file naming")
            logger.info("  ✓ City-based folder organization")
            logger.info("  ✓ Case-insensitive city name matching (prevents duplicates)")
            logger.info("  ✓ Comprehensive metadata and reports")
            logger.info("  ✓ Data validation and error handling")
            logger.info("  ✓ Cross-platform compatibility")
        else:
            logger.error("Organization process failed. Please check error messages.")
            
    except Exception as e:
        logger.error(f"Program execution failed: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()