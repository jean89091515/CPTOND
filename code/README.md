# Urban Transportation Data Processing Toolkit

A comprehensive Python toolkit for collecting, processing, and analyzing urban public transportation data (bus and metro networks) from Chinese cities. This toolkit enables researchers to build standardized datasets for urban transportation network analysis and visualization.

## Overview

This toolkit provides end-to-end processing capabilities for urban transportation data:

- **Data Collection**: Automated crawling of bus and metro route data from Chinese mapping APIs
- **Data Processing**: Conversion of raw data into standardized GIS formats (shapefiles)
- **Network Analysis**: Generation of route segments between consecutive stops for network analysis
- **City Organization**: Data organized by individual cities for comparative analysis
- **Data Organization**: Automated city-based shapefile organization with standardized naming
- **Coordinate Transformation**: Support for Chinese coordinate systems (WGS84, GCJ02, BD09)

## Features

### Core Functionality
- 🚌 **Bus Route Data Crawling**: Collect comprehensive bus route geometries and operational information
- 🚇 **Metro Route Data Crawling**: Collect metro/subway network data with operational details
- 🗺️ **Shapefile Generation**: Convert collected data into GIS-ready ESRI shapefiles
- 📊 **Network Segmentation**: Break routes into segments between consecutive stops
- 📁 **City-based Organization**: Organize shapefiles by city with standardized naming conventions
- 🔄 **Coordinate Transformation**: Handle Chinese coordinate system conversions
- 🏙️ **City-wise Processing**: Organize data by individual cities for comparative analysis
- 🎯 **Taiwan Coordinate Correction**: Automatic correction for Taiwan Province coordinate issues
- 📋 **Automated Reporting**: Generate comprehensive processing and organization reports

### Data Outputs
- **Route Geometries**: LineString features with operational metadata
- **Stop Locations**: Point features with service statistics
- **Network Segments**: Detailed segment-level analysis with distance calculations
- **City-organized Shapefiles**: Individual city folders with standardized file naming
- **Processing Reports**: Comprehensive documentation of data processing steps

## Installation

### Prerequisites
- Python 3.7 or higher
- Git (for cloning the repository)

### Required Dependencies
Install the required Python packages:

```bash
pip install -r requirements.txt
```

#### Core Dependencies:
```
pandas>=1.3.0
geopandas>=0.10.0
shapely>=1.8.0
requests>=2.25.0
beautifulsoup4>=4.9.0
pyproj>=3.2.0
matplotlib>=3.3.0
xpinyin>=0.7.6
```

#### Optional Dependencies:
```
pypinyin>=0.44.0  # For Chinese city name processing
```

### Installation Steps

1. **Clone the repository:**
```bash
git clone <repository-url>
cd urban-transportation-toolkit
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Verify installation:**
```bash
python -c "import geopandas, pandas, shapely; print('Installation successful')"
```

## Quick Start

### Bus Data Processing

```python
# 1. Bus Data Collection (requires API key)
from Bus_Route_Data_Crawler import BusDataCrawler

crawler = BusDataCrawler(api_key="your_amap_api_key")
crawler.crawl_city_data("Beijing", "bj")

# 2. Bus Data Processing
from Bus_Data_Processor import BusDataProcessor

processor = BusDataProcessor()
results = processor.process_all()

# 3. Bus Network Segmentation
from Bus_Segment_Processor import BusSegmentProcessor

segment_processor = BusSegmentProcessor()
segment_results = segment_processor.process_all_cities()

# 4. Bus City Organization
from Bus_City_Shapefile_Organizer import BusCityShapefileOrganizer

organizer = BusCityShapefileOrganizer()
organization_results = organizer.organize_by_city()
```

### Metro Data Processing

```python
# 1. Metro Data Collection
from Metro_Route_Data_Crawler import MetroDataCrawler

metro_crawler = MetroDataCrawler(api_key="your_amap_api_key")
metro_crawler.crawl_city_data("Beijing", metro_cities_dict)

# 2. Metro Data Processing
from Metro_Data_Processor import MetroDataProcessor

metro_processor = MetroDataProcessor()
metro_results = metro_processor.process_all()

# 3. Metro Network Segmentation
from Metro_Segment_Processor import MetroSegmentProcessor

metro_segment_processor = MetroSegmentProcessor()
metro_segment_results = metro_segment_processor.process_all_cities()

# 4. Metro City Organization
from Metro_City_Shapefile_Organizer import MetroCityShapefileOrganizer

metro_organizer = MetroCityShapefileOrganizer()
metro_organization_results = metro_organizer.organize_by_city()
```

### Command Line Usage

```bash
# Process bus data into shapefiles
python Bus_Data_Processor.py

# Generate bus network segments
python Bus_Segment_Processor.py

# Organize bus data by city
python Bus_City_Shapefile_Organizer.py

# Process metro data into shapefiles
python Metro_Data_Processor.py

# Generate metro network segments
python Metro_Segment_Processor.py

# Organize metro data by city
python Metro_City_Shapefile_Organizer.py
```

## File Structure

```
urban-transportation-toolkit/
├── code/
│   ├── Bus_Route_Data_Crawler.py     # Bus data collection from APIs
│   ├── Bus_Data_Processor.py         # Bus shapefile generation
│   ├── Bus_Segment_Processor.py      # Bus network segmentation
│   ├── Bus_City_Shapefile_Organizer.py  # Bus city-based organization
│   ├── Metro_Route_Data_Crawler.py   # Metro data collection from APIs
│   ├── Metro_Data_Processor.py       # Metro shapefile generation
│   ├── Metro_Segment_Processor.py    # Metro network segmentation
│   ├── Metro_City_Shapefile_Organizer.py  # Metro city-based organization
│   ├── transform.py                  # Coordinate transformations
│   └── box_test.py                   # Testing utilities
├── city_list/
│   ├── bus_city_list_split.csv       # Bus city configuration file
│   └── metro_city_list_split.csv     # Metro city configuration file
├── dataset/
│   ├── bus/
│   │   ├── enhanced_data/            # Raw bus data collected
│   │   └── shapefiles/               # Processed bus GIS data
│   │       ├── bus_routes.shp        # Consolidated bus routes
│   │       ├── bus_stops.shp         # Consolidated bus stops
│   │       ├── [city_name]/          # City-specific folders
│   │       │   ├── [city_pinyin]_bus_stops.shp
│   │       │   ├── [city_pinyin]_bus_routes.shp
│   │       │   └── city_info.txt
│   │       └── bus_organization_summary.txt
│   ├── metro/
│   │   ├── enhanced_data/            # Raw metro data collected
│   │   └── shapefiles/               # Processed metro GIS data
│   │       ├── metro_routes.shp      # Consolidated metro routes
│   │       ├── metro_stops.shp       # Consolidated metro stops
│   │       ├── metro_merged_stations.shp  # Merged stations (optional)
│   │       ├── [city_name]/          # City-specific folders
│   │       │   ├── [city_pinyin]_metro_stops.shp
│   │       │   ├── [city_pinyin]_metro_routes.shp
│   │       │   ├── [city_pinyin]_metro_merged_stations.shp
│   │       │   └── city_info.txt
│   │       └── metro_organization_summary.txt
│   └── logs/                         # Processing logs
├── requirements.txt                  # Python dependencies
└── README.md                        # This file
```

## Input/Output Formats

### Input Requirements

1. **City Configuration Files**:
   - `city_list/bus_city_list_split.csv`: Bus cities configuration
   - `city_list/metro_city_list_split.csv`: Metro cities configuration
   ```csv
   city_cn,city_en,city_simple
   北京,Beijing,bj
   上海,Shanghai,sh
   ```

2. **API Access**:
   - AMap (Gaode Maps) API key for data collection
   - Internet connection for web scraping route lists

### Output Formats

#### Bus Data Outputs

1. **Enhanced CSV Data** (`dataset/bus/enhanced_data/`):
   - Route information with coordinates and stops
   - JSON-encoded geometry and metadata

2. **Bus Shapefiles** (`dataset/bus/shapefiles/`):
   - `bus_routes.shp`: Bus route geometries (LineString)
   - `bus_stops.shp`: Bus stop locations (Point)

3. **City-wise Bus Shapefiles** (`dataset/bus/shapefiles/[city]/`):
   - `[city]_bus_segments.shp`: Bus segments between stops
   - `[city]_bus_stops_unique.shp`: Deduplicated bus stops

4. **City-organized Bus Shapefiles** (`dataset/bus/shapefiles/[city_name]/`):
   - `[city_pinyin]_bus_stops.shp`: City-specific bus stops
   - `[city_pinyin]_bus_routes.shp`: City-specific bus routes
   - `city_info.txt`: City metadata and statistics

#### Metro Data Outputs

1. **Enhanced CSV Data** (`dataset/metro/enhanced_data/`):
   - Metro route information with operational details
   - Coordinate data and stop information

2. **Metro Shapefiles** (`dataset/metro/shapefiles/`):
   - `metro_routes.shp`: Metro route geometries (LineString)
   - `metro_stops.shp`: Metro stop locations (Point)

3. **City-wise Metro Shapefiles** (`dataset/metro/shapefiles/[city]/`):
   - `[city]_metro_segments.shp`: Metro segments between stations
   - `[city]_metro_stops_unique.shp`: Deduplicated metro stations

4. **City-organized Metro Shapefiles** (`dataset/metro/shapefiles/[city_name]/`):
   - `[city_pinyin]_metro_stops.shp`: City-specific metro stops
   - `[city_pinyin]_metro_routes.shp`: City-specific metro routes
   - `[city_pinyin]_metro_merged_stations.shp`: Merged stations (if available)
   - `city_info.txt`: City metadata and statistics

### Field Descriptions

#### Bus Route Shapefiles
| Field | Type | Description |
|-------|------|-------------|
| route_id | String | Unique route identifier |
| route_name | String | Route name/number |
| city_code | String | City administrative code |
| company | String | Operating company |
| start_stop | String | Starting stop name |
| end_stop | String | Terminal stop name |
| distance | Float | Route length (meters) |
| geometry | LineString | Route path coordinates |

#### Metro Route Shapefiles
| Field | Type | Description |
|-------|------|-------------|
| route_cn | String | Route name (Chinese) |
| route_en | String | Route name (English) |
| route_id | String | Unique route identifier |
| city_code | String | City administrative code |
| route_type | String | Metro line type |
| start_time | String | First train time |
| end_time | String | Last train time |
| basic_prc | String | Basic fare price |
| total_prc | String | Maximum fare price |
| geometry | LineString | Route path coordinates |

#### Segment Shapefiles (Bus & Metro)
| Field | Type | Description |
|-------|------|-------------|
| s_stopid | String | Start stop/station ID |
| e_stopid | String | End stop/station ID |
| distance | Float | Segment distance (km) |
| num | Integer | Number of routes using segment |
| city_cn | String | City name (Chinese) |
| city_en | String | City name (English) |
| geometry | LineString | Segment path |

## City-based Data Organization

### File Naming Convention

The toolkit uses standardized pinyin-based naming for city-organized files:

#### Bus Files
- **Stops**: `{city_pinyin}_bus_stops.shp`
- **Routes**: `{city_pinyin}_bus_routes.shp`
- **Example**: `beijing_bus_stops.shp`, `shanghai_bus_routes.shp`

#### Metro Files
- **Stops**: `{city_pinyin}_metro_stops.shp`
- **Routes**: `{city_pinyin}_metro_routes.shp`
- **Merged Stations**: `{city_pinyin}_metro_merged_stations.shp`
- **Example**: `beijing_metro_stops.shp`, `shanghai_metro_routes.shp`

### Organization Features

- **Automatic City Detection**: Extracts cities from `city_en` field in shapefiles
- **Pinyin Conversion**: Converts English city names to pinyin format for consistent naming
- **Folder Sanitization**: Cleans city names to ensure cross-platform compatibility
- **Metadata Generation**: Creates `city_info.txt` with detailed city statistics
- **Processing Reports**: Generates comprehensive organization summary reports

### City Organization Example

```python
# Organize bus data by city
from Bus_City_Shapefile_Organizer import BusCityShapefileOrganizer

organizer = BusCityShapefileOrganizer()
results = organizer.organize_by_city()

# Output structure:
# shapefiles/
# ├── bus_routes.shp (original consolidated data)
# ├── bus_stops.shp
# ├── Beijing/
# │   ├── beijing_bus_stops.shp
# │   ├── beijing_bus_routes.shp
# │   └── city_info.txt
# ├── Shanghai/
# │   ├── shanghai_bus_stops.shp
# │   ├── shanghai_bus_routes.shp
# │   └── city_info.txt
# └── bus_organization_summary.txt
```

## Testing

### Unit Testing

Run individual module tests:

```bash
# Test coordinate transformations
python transform.py

# Test logging utilities
python box_test.py
```

### Integration Testing

Test the complete pipeline with sample data:

```bash
# 1. Prepare test city configuration
echo "city_cn,city_en,city_simple" > test_cities.csv
echo "测试市,Test City,test" >> test_cities.csv

# 2. Run bus processing pipeline
python Bus_Data_Processor.py
python Bus_City_Shapefile_Organizer.py

# 3. Run metro processing pipeline
python Metro_Data_Processor.py
python Metro_City_Shapefile_Organizer.py

# 4. Verify outputs
ls dataset/bus/shapefiles/
ls dataset/metro/shapefiles/
```

### Sample Data Testing

Use the provided sample dataset to test functionality without API access:

```python
# Test bus data processing and organization
from Bus_Data_Processor import BusDataProcessor
from Bus_City_Shapefile_Organizer import BusCityShapefileOrganizer

processor = BusDataProcessor("sample_data/bus/")
results = processor.process_all()

organizer = BusCityShapefileOrganizer("sample_data/bus/")
org_results = organizer.organize_by_city()

# Test metro data processing and organization
from Metro_Data_Processor import MetroDataProcessor
from Metro_City_Shapefile_Organizer import MetroCityShapefileOrganizer

metro_processor = MetroDataProcessor("sample_data/metro/")
metro_results = metro_processor.process_all()

metro_organizer = MetroCityShapefileOrganizer()
metro_org_results = metro_organizer.organize_by_city()
```

## Configuration

### API Configuration

Set your AMap API key in the crawlers:

```python
# For bus data
bus_crawler = BusDataCrawler(api_key="your_api_key_here")

# For metro data
metro_crawler = MetroDataCrawler(api_key="your_api_key_here")
```

### Processing Options

Customize processing behavior:

```python
# Custom input/output paths for bus data
bus_processor = BusDataProcessor(
    data_path="custom/bus/input/path",
    output_path="custom/bus/output/path"
)

# Custom paths for bus city organization
bus_organizer = BusCityShapefileOrganizer(
    data_path="custom/bus/path"
)

# Custom input/output paths for metro data
metro_processor = MetroDataProcessor(
    data_path="custom/metro/input/path"
)

# Metro city organization (uses default paths)
metro_organizer = MetroCityShapefileOrganizer()
```

### Logging Configuration

Control logging output:

```python
import logging
logging.basicConfig(level=logging.INFO)

# Or use the testing utilities
from box_test import set_print_mode
set_print_mode(False)
```

## Coordinate Systems

The toolkit handles three coordinate systems commonly used in Chinese mapping:

- **WGS84** (EPSG:4326): GPS standard, international compatibility
- **GCJ02**: Mars Coordinate System, used by most Chinese mapping services  
- **BD09**: Baidu Coordinate System, used by Baidu Maps

### Coordinate Transformation Example

```python
from transform import wgs84_to_gcj02, gcj02_to_bd09

# Convert GPS coordinates to Chinese mapping format
gps_coords = [116.3974, 39.9093]  # Beijing Tiananmen
gcj02_coords = wgs84_to_gcj02(*gps_coords)
bd09_coords = gcj02_to_bd09(*gcj02_coords)

print(f"GPS: {gps_coords}")
print(f"GCJ02: {gcj02_coords}")
print(f"BD09: {bd09_coords}")
```

### Taiwan Coordinate Correction

The toolkit includes automatic correction for Taiwan Province coordinate issues:

```python
# Taiwan metro stations are automatically detected and corrected
# Based on city_cn field containing '台湾'
# Applies transform.wgs84_to_gcj02 to fix coordinate misalignment
```

## Transportation-Specific Features

### Bus Network Processing
- **Operational filtering**: Removes inactive or temporary routes
- **Route type classification**: Distinguishes between regular, express, and special services
- **Stop deduplication**: Handles multiple routes serving the same stops
- **Distance validation**: Validates route distances against stop sequences
- **City-based organization**: Automatic organization by city with standardized naming

### Metro Network Processing  
- **Line type filtering**: Processes only metro/subway/light rail systems
- **Operational status filtering**: Excludes unopened or planned lines
- **Station merging**: Handles transfer stations and station complexes
- **Taiwan coordinate correction**: Automatic coordinate system correction for Taiwan Province
- **Operational information**: Extracts schedule and pricing data where available
- **City-based organization**: Automatic organization by city with merged station support

## Troubleshooting

### Common Issues

1. **API Rate Limiting**:
   ```
   Error: Too many requests
   Solution: Add delays between API calls or use multiple API keys
   ```

2. **Taiwan Coordinate Issues**:
   ```
   Issue: Taiwan metro stations misaligned with map data
   Solution: Automatic correction applied based on city detection
   ```

3. **Coordinate Validation Failures**:
   ```
   Error: Invalid coordinates outside China bounds
   Solution: Check coordinate system and transformation accuracy
   ```

4. **Shapefile Field Length Errors**:
   ```
   Error: Field truncation in shapefile
   Solution: Automatic truncation is applied, check field mappings
   ```

5. **City Organization Issues**:
   ```
   Error: No cities found for organization
   Solution: Ensure city_en field exists in input shapefiles
   ```

6. **Missing Pypinyin Library**:
   ```
   Warning: pypinyin library not installed
   Solution: pip install pypinyin for better Chinese name handling
   ```

### Debug Mode

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Or use the testing utilities
from box_test import log, test

@test("Debug Function")
def debug_function():
    log("Debug information here")
```

### Memory Optimization

For large datasets:

```python
# Process cities individually to reduce memory usage
for city in cities:
    processor.process_single_city(city)
    # Clear intermediate data
    del processor.temp_data
```

## Contributing

We welcome contributions to improve the toolkit. Please follow these guidelines:

1. **Code Style**: Follow PEP 8 standards
2. **Documentation**: Add docstrings for all functions in English
3. **Testing**: Include unit tests for new features
4. **Logging**: Use English for all log messages and comments

### Development Setup

```bash
# Clone for development
git clone <repository-url>
cd urban-transportation-toolkit

# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
python -m pytest tests/
```

## License

This project is licensed under the MIT License. See LICENSE file for details.

## Citation

If you use this toolkit in your research, please cite:

```
Urban Transportation Data Processing Toolkit
[Authors], [Year]
[Journal/Conference]
DOI: [DOI if available]
```

## Support

For questions and support:

- **Issues**: Create an issue on the project repository
- **Documentation**: Check the inline code documentation
- **Examples**: See the `examples/` directory for detailed usage examples

## Changelog

### Version 1.1.0
- Added city-based shapefile organization functionality
- Implemented Bus_City_Shapefile_Organizer for automated bus data organization
- Implemented Metro_City_Shapefile_Organizer for automated metro data organization
- Added standardized pinyin-based file naming convention
- Enhanced processing reports with organization statistics
- Improved cross-platform compatibility for folder and file naming

### Version 1.0.0
- Initial release with bus and metro data processing capabilities
- Support for Chinese coordinate systems with Taiwan correction
- City-wise processing and segmentation for both transportation modes
- Comprehensive testing utilities and English documentation
- Operational information extraction for both bus and metro systems
- Intelligent deduplication algorithms for routes and stops

---

**Note**: This toolkit is designed for research purposes. Please ensure compliance with API terms of service and local regulations when collecting transportation data.