# State outlines

U.S. Census Bureau, 2024 cartographic boundary files, 1:20,000,000 scale.
Source: https://www2.census.gov/geo/tiger/GENZ2024/shp/cb_2024_us_state_20m.zip
Documentation: https://www.census.gov/geographies/mapping-files/time-series/geo/carto-boundary-file.html

Converted from the Census shapefile to GeoJSON with `tools/convert_states.py`.
Only state abbreviation/name and geometry are retained. These are generalized
cartographic outlines for visualization, not legal or survey boundaries.
Coordinates are NAD83 geographic coordinates, displayed on the web basemap as
longitude/latitude; datum differences are negligible at this display scale.
U.S. federal government geographic data; attribution: U.S. Census Bureau.
