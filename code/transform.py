#!/usr/bin/env python3
"""
Coordinate Transformation Module

This module provides coordinate system transformations commonly used in 
Chinese mapping services and GPS applications. Supports conversion between
WGS84, GCJ02 (Mars Coordinate System), and BD09 (Baidu Coordinate System).

Coordinate Systems:
    - WGS84: World Geodetic System 1984 (GPS standard)
    - GCJ02: Mars Coordinate System (used by Chinese mapping services)
    - BD09: Baidu Coordinate System (used by Baidu Maps)

Dependencies:
    - math (standard library)
    - json (standard library)
    - urllib (standard library)

Author: Geographic Data Processing Team
License: MIT
"""

import json
import urllib
import math

# Coordinate transformation constants
X_PI = 3.14159265358979324 * 3000.0 / 180.0
PI = 3.1415926535897932384626  # π
A = 6378245.0  # Semi-major axis
EE = 0.00669342162296594323  # Eccentricity squared


def gcj02_to_bd09(lng, lat):
    """
    Convert GCJ02 (Mars) coordinates to BD09 (Baidu) coordinates
    
    Used for converting Google Maps, Amap coordinates to Baidu Maps format
    
    Args:
        lng (float): Longitude in GCJ02 system
        lat (float): Latitude in GCJ02 system
        
    Returns:
        list: [longitude, latitude] in BD09 system
    """
    z = math.sqrt(lng * lng + lat * lat) + 0.00002 * math.sin(lat * X_PI)
    theta = math.atan2(lat, lng) + 0.000003 * math.cos(lng * X_PI)
    bd_lng = z * math.cos(theta) + 0.0065
    bd_lat = z * math.sin(theta) + 0.006
    return [bd_lng, bd_lat]


def bd09_to_gcj02(bd_lon, bd_lat):
    """
    Convert BD09 (Baidu) coordinates to GCJ02 (Mars) coordinates
    
    Used for converting Baidu Maps coordinates to Google Maps, Amap format
    
    Args:
        bd_lon (float): Longitude in BD09 system
        bd_lat (float): Latitude in BD09 system
        
    Returns:
        list: [longitude, latitude] in GCJ02 system
    """
    x = bd_lon - 0.0065
    y = bd_lat - 0.006
    z = math.sqrt(x * x + y * y) - 0.00002 * math.sin(y * X_PI)
    theta = math.atan2(y, x) - 0.000003 * math.cos(x * X_PI)
    gg_lng = z * math.cos(theta)
    gg_lat = z * math.sin(theta)
    return [gg_lng, gg_lat]


def wgs84_to_gcj02(lng, lat):
    """
    Convert WGS84 coordinates to GCJ02 (Mars) coordinates
    
    Used for converting GPS coordinates to Chinese mapping service format
    
    Args:
        lng (float): Longitude in WGS84 system
        lat (float): Latitude in WGS84 system
        
    Returns:
        list: [longitude, latitude] in GCJ02 system
    """
    if out_of_china(lng, lat):  # Check if coordinates are outside China
        return [lng, lat]
    
    dlat = _transform_lat(lng - 105.0, lat - 35.0)
    dlng = _transform_lng(lng - 105.0, lat - 35.0)
    radlat = lat / 180.0 * PI
    magic = math.sin(radlat)
    magic = 1 - EE * magic * magic
    sqrtmagic = math.sqrt(magic)
    dlat = (dlat * 180.0) / ((A * (1 - EE)) / (magic * sqrtmagic) * PI)
    dlng = (dlng * 180.0) / (A / sqrtmagic * math.cos(radlat) * PI)
    mglat = lat + dlat
    mglng = lng + dlng
    return [mglng, mglat]


def gcj02_to_wgs84(lng, lat):
    """
    Convert GCJ02 (Mars) coordinates to WGS84 coordinates
    
    Used for converting Chinese mapping service coordinates to GPS format
    
    Args:
        lng (float): Longitude in GCJ02 system
        lat (float): Latitude in GCJ02 system
        
    Returns:
        list: [longitude, latitude] in WGS84 system
    """
    if out_of_china(lng, lat):
        return [lng, lat]
    
    dlat = _transform_lat(lng - 105.0, lat - 35.0)
    dlng = _transform_lng(lng - 105.0, lat - 35.0)
    radlat = lat / 180.0 * PI
    magic = math.sin(radlat)
    magic = 1 - EE * magic * magic
    sqrtmagic = math.sqrt(magic)
    dlat = (dlat * 180.0) / ((A * (1 - EE)) / (magic * sqrtmagic) * PI)
    dlng = (dlng * 180.0) / (A / sqrtmagic * math.cos(radlat) * PI)
    mglat = lat + dlat
    mglng = lng + dlng
    return [lng * 2 - mglng, lat * 2 - mglat]


def bd09_to_wgs84(bd_lon, bd_lat):
    """
    Convert BD09 (Baidu) coordinates to WGS84 coordinates
    
    Two-step conversion: BD09 -> GCJ02 -> WGS84
    
    Args:
        bd_lon (float): Longitude in BD09 system
        bd_lat (float): Latitude in BD09 system
        
    Returns:
        list: [longitude, latitude] in WGS84 system
    """
    lon, lat = bd09_to_gcj02(bd_lon, bd_lat)
    return gcj02_to_wgs84(lon, lat)


def wgs84_to_bd09(lon, lat):
    """
    Convert WGS84 coordinates to BD09 (Baidu) coordinates
    
    Two-step conversion: WGS84 -> GCJ02 -> BD09
    
    Args:
        lon (float): Longitude in WGS84 system
        lat (float): Latitude in WGS84 system
        
    Returns:
        list: [longitude, latitude] in BD09 system
    """
    lon, lat = wgs84_to_gcj02(lon, lat)
    return gcj02_to_bd09(lon, lat)


def _transform_lat(lng, lat):
    """
    Internal function for latitude transformation calculations
    
    Args:
        lng (float): Longitude offset
        lat (float): Latitude offset
        
    Returns:
        float: Transformed latitude value
    """
    ret = -100.0 + 2.0 * lng + 3.0 * lat + 0.2 * lat * lat + \
          0.1 * lng * lat + 0.2 * math.sqrt(math.fabs(lng))
    ret += (20.0 * math.sin(6.0 * lng * PI) + 20.0 *
            math.sin(2.0 * lng * PI)) * 2.0 / 3.0
    ret += (20.0 * math.sin(lat * PI) + 40.0 *
            math.sin(lat / 3.0 * PI)) * 2.0 / 3.0
    ret += (160.0 * math.sin(lat / 12.0 * PI) + 320 *
            math.sin(lat * PI / 30.0)) * 2.0 / 3.0
    return ret


def _transform_lng(lng, lat):
    """
    Internal function for longitude transformation calculations
    
    Args:
        lng (float): Longitude offset
        lat (float): Latitude offset
        
    Returns:
        float: Transformed longitude value
    """
    ret = 300.0 + lng + 2.0 * lat + 0.1 * lng * lng + \
          0.1 * lng * lat + 0.1 * math.sqrt(math.fabs(lng))
    ret += (20.0 * math.sin(6.0 * lng * PI) + 20.0 *
            math.sin(2.0 * lng * PI)) * 2.0 / 3.0
    ret += (20.0 * math.sin(lng * PI) + 40.0 *
            math.sin(lng / 3.0 * PI)) * 2.0 / 3.0
    ret += (150.0 * math.sin(lng / 12.0 * PI) + 300.0 *
            math.sin(lng / 30.0 * PI)) * 2.0 / 3.0
    return ret


def out_of_china(lng, lat):
    """
    Check if coordinates are outside Chinese territory
    
    No coordinate transformation needed for locations outside China
    
    Args:
        lng (float): Longitude
        lat (float): Latitude
        
    Returns:
        bool: True if outside China, False if inside China
    """
    return not (lng > 73.66 and lng < 135.05 and lat > 3.86 and lat < 53.55)


class GeocodingAmap:
    """
    Amap (Gaode Maps) geocoding service interface
    
    Provides address-to-coordinate conversion using Amap API
    """
    
    def __init__(self, api_key):
        """
        Initialize Amap geocoding service
        
        Args:
            api_key (str): Amap API key for service access
        """
        self.api_key = api_key

    def geocode_amap(self, address):
        """
        Convert address to coordinates using Amap geocoding service
        
        Args:
            address (str): Address to be geocoded
            
        Returns:
            list: [longitude, latitude] or None if failed
        """
        geocoding_params = {
            'key': self.api_key,
            'city': 'nationwide',
            'address': address
        }
        geocoding_query = urllib.parse.urlencode(geocoding_params)
        
        try:
            url = f"http://restapi.amap.com/v3/geocode/geo?{geocoding_query}"
            response = urllib.request.urlopen(url)
            
            if response.getcode() == 200:
                result = response.read()
                json_obj = json.loads(result)
                
                if json_obj['status'] == '1' and int(json_obj['count']) >= 1:
                    geocodes = json_obj['geocodes'][0]
                    location = geocodes.get('location').split(',')
                    lng = float(location[0])
                    lat = float(location[1])
                    return [lng, lat]
                else:
                    return None
            else:
                return None
                
        except Exception as e:
            print(f"Geocoding error: {e}")
            return None


class GeocodingBaidu:
    """
    Baidu Maps geocoding service interface
    
    Provides address-to-coordinate conversion using Baidu API
    """
    
    def __init__(self, api_key):
        """
        Initialize Baidu geocoding service
        
        Args:
            api_key (str): Baidu API key for service access
        """
        self.api_key = api_key

    def geocode_baidu(self, address):
        """
        Convert address to coordinates using Baidu geocoding service
        
        Args:
            address (str): Address to be geocoded
            
        Returns:
            list: [longitude, latitude] or None if failed
        """
        geocoding_params = {
            'ak': self.api_key,
            'city': 'nationwide',
            'address': address,
            'output': 'json',
            'ret_coordtype': 'gcj02ll'
        }
        geocoding_query = urllib.parse.urlencode(geocoding_params)
        
        try:
            url = f"http://api.map.baidu.com/geocoding/v3/?{geocoding_query}"
            response = urllib.request.urlopen(url)
            
            if response.getcode() == 200:
                result = response.read()
                json_obj = json.loads(result)
                
                if json_obj['status'] == 0:
                    location = json_obj['result']['location']
                    lng = float(location['lng'])
                    lat = float(location['lat'])
                    return [lng, lat]
                else:
                    return None
            else:
                return None
                
        except Exception as e:
            print(f"Geocoding error: {e}")
            return None


# Example usage and testing
if __name__ == '__main__':
    """
    Example coordinate transformations for testing
    """
    # Test coordinates (Beijing area)
    lng = 116.359824
    lat = 39.94762
    
    print("Coordinate Transformation Examples:")
    print(f"Original coordinates (WGS84): {lng}, {lat}")
    print()
    
    # Test all transformation functions
    result1 = gcj02_to_bd09(lng, lat)
    print(f"GCJ02 to BD09: {result1}")
    
    result2 = bd09_to_gcj02(lng, lat)
    print(f"BD09 to GCJ02: {result2}")
    
    result3 = wgs84_to_gcj02(lng, lat)
    print(f"WGS84 to GCJ02: {result3}")
    
    result4 = gcj02_to_wgs84(lng, lat)
    print(f"GCJ02 to WGS84: {result4}")
    
    result5 = bd09_to_wgs84(lng, lat)
    print(f"BD09 to WGS84: {result5}")
    
    result6 = wgs84_to_bd09(lng, lat)
    print(f"WGS84 to BD09: {result6}")
    
    print()
    print("Coordinate system usage:")
    print("- WGS84: GPS devices, international mapping")
    print("- GCJ02: Amap, Google Maps China, most Chinese mapping services")
    print("- BD09: Baidu Maps and related services")