# CPTOND - China Public Transport Operation Network Dataset

## Overview

The **China Public Transport Operation Network Dataset (CPTOND-2025)** is a comprehensive open dataset of China's public transport operation networks, systematically integrating bus networks from 350 cities and metro systems from 46 cities across mainland China, Hong Kong, Macao, and Taiwan regions.

This repository hosts an interactive web visualization platform that allows users to explore and preview the dataset online before downloading.

## Dataset Features

- **High-precision geographic coordinates**: WGS-84 coordinate system with 5.08m average spatial accuracy
- **Comprehensive coverage**: 3,408,000 km of operational routes (Bus: ~3,375,000 km; Metro: ~33,000 km)
- **Rich attribute information**: Operating hours, fares, operating companies, and more
- **Standardized format**: Uniform Shapefile data structure and naming conventions
- **Bilingual support**: Chinese and English attribute records
- **Multi-transport modes**: Bus and metro systems
- **National coverage**: All provinces and major cities across China

## Web Platform Features

- **Interactive Map Visualization**: Real-time loading and visualization of transport network data
- **Dual Language Support**: Full Chinese/English interface
- **Transport Mode Switching**: Toggle between bus and metro systems
- **Layer Control**: Switch between stops, routes, or overlay views
- **Multiple Basemaps**: OpenStreetMap, CartoDB, Esri, and Stamen options
- **City Selection**: 350+ cities available for exploration
- **Data Attribute Display**: Detailed information about dataset properties

## Data Structure

### File Naming Convention
```
{city_en}_bus_routes.shp    # Bus route data
{city_en}_bus_stops.shp     # Bus stop data
{city_en}_metro_routes.shp  # Metro line data
{city_en}_metro_stops.shp   # Metro station data
```

### Key Attributes
- **Spatial Data**: Point and LineString geometries in WGS-84
- **Route Information**: Route IDs, names, operators
- **Stop Information**: Stop names, coordinates, route associations
- **Operational Data**: Operating hours, fare information
- **Multilingual**: Chinese and English naming support

## Repository Structure

```
CPTOND/
├── index.html              # Main web interface
├── geojson/                  # Sample GeoJSON files
└── README.md              # This file
```

## Usage

### Online Preview
Visit the [interactive web platform](https://jean89091515.github.io/CPTOND/) to:
1. Select a city from the dropdown menu
2. Choose transport type (Bus/Metro)
3. Toggle between stops, routes, or combined view
4. Click on features to view detailed information

### Local Development
```bash
# Clone the repository
git clone https://github.com/jean89091515/CPTOND.git
cd CPTOND

# Serve locally (Python 3)
python -m http.server 8000

# Or use Node.js
npx serve .

# Access at http://localhost:8000
```

## Data Download

The complete dataset is available through:
- **Primary Source**: [Figshare Repository](https://figshare.com/articles/dataset/CPTOND-2025/29377427)
- **Raw GeoJSON**: [Data Server](https://test.bgyoa.xyz/geojson/)

### Download Instructions
1. Visit the Figshare link above
2. Register for free access (if required)
3. Download the complete dataset (Shapefile format)
4. For GeoJSON previews, use the raw data server

## Applications

- **Urban Planning**: Transport network analysis and planning
- **Academic Research**: Urban mobility and accessibility studies
- **Policy Making**: Evidence-based transport policy development
- **Operation Analysis**: Public transport efficiency assessment
- **Spatial Analysis**: GIS-based transportation research

## Technical Specifications

- **Coordinate System**: WGS-84 (EPSG:4326)
- **Data Format**: Shapefile (.shp) and GeoJSON
- **Encoding**: UTF-8 with bilingual support
- **Spatial Accuracy**: 5.08m average positioning accuracy
- **Data Collection**: June 2025 using professional APIs and platforms

## Citation

If you use this dataset in your research, please cite:

```bibtex
@dataset{wang_liang_2025_cptond,
  author    = {Wang, Liang and Wei, He and Guan, Yu and Ouyang, Libin and 
               Xu, DanDan and Han, Xuehua and Zhang, Min and Chen, Meng and 
               Sun, Daosheng and Gong, Daqing and Zhang, Zhenji and 
               Zhang, Xinghua and Zhang, Xiaodong},
  title     = {China Public Transport Operation Network Dataset (CPTOND-2025)},
  year      = {2025},
  publisher = {Figshare},
  doi       = {10.6084/m9.figshare.29377427},
  url       = {https://figshare.com/articles/dataset/CPTOND-2025/29377427}
}
```

## Authors & Affiliations

**Primary Authors:**
- Liang Wang¹² - Beijing Jiaotong University & Beijing Municipal Institute of City Planning and Design
- Xiaodong Zhang*²⁴ - Beijing Municipal Institute of City Planning and Design & Tsinghua University
- Xinghua Zhang*³ - Beijing Jiaotong University

**Contributing Authors:**
He Wei², Yu Guan², Libin Ouyang², DanDan Xu², Xuehua Han², Min Zhang², Meng Chen², Daosheng Sun², Daqing Gong¹, Zhenji Zhang¹

**Affiliations:**
1. School of Economics and Management, Beijing Jiaotong University
2. Beijing Municipal Institute of City Planning and Design  
3. School of Physical Science and Engineering, Beijing Jiaotong University
4. School of Architecture, Tsinghua University

*Corresponding authors

## Contact

For questions, suggestions, or collaboration inquiries:
- **Email**: wljean@126.com
- **Dataset Issues**: [GitHub Issues](https://github.com/yourusername/CPTOND/issues)
- **Dataset Repository**: [Figshare](https://figshare.com/articles/dataset/CPTOND-2025/29377427)

## License

This project and dataset are released under open access principles. Please refer to the [Figshare repository](https://figshare.com/articles/dataset/CPTOND-2025/29377427) for detailed licensing information.

## Acknowledgments

We thank all the data providers, open source communities, and institutions that made this comprehensive dataset possible. Special thanks to the urban planning and transportation research communities for their continued support of open science initiatives.

---

**Disclaimer**: This dataset is provided for research and educational purposes. Users are responsible for ensuring appropriate use and compliance with local regulations when applying the data.
