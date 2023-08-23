# TriMet Trip Game
## Purpose
The purpose of the game is to learn TriMet bus and MAX routes. It's easy to _get somewhere_ by transit. One can look up transit directions on Trimet.org or Google Maps. This does not help to _learn_ transit in a city. In fact, city dwellers generally stay in localized areas so they are not exposed to all routes. This game helps all users engage with TriMet's service and learn by guessing the correct itinerary. Play every day and you'll be surprised at what you learn!

## Underlying Data
The game has several elements described below:
- **route paths** - routes are built from the gtfs shapes.txt file.
- **itineraries** - itineraries and "leg" geometries are provided by TriMet's trip planner.
- **origin | destination** - origin and destination points are randomly generated points within 0.5 miles of a TriMet route shape.
- **basemap** - [Stanem Design](http://stamen.com) basemap is used to remove a lot of detail and focus mainly on the origin and destination relative location.

## Creation Steps
1. Download gtfs.zip file from TriMet. Something like this:
```python
from zipfile import ZipFile
from urllib.request import urlopen
resp = urlopen("https://developer.trimet.org/schedule/gtfs.zip")
myzip = ZipFile(BytesIO(resp.read()))
myzip.extractall('gtfs/')
```
2. Create shapely LineStrings from the `shapes.txt` gtfs file. Something like this:
```python
gtfs_shapes = pd.read_csv('gtfs/shapes.txt')
gtfs_shapes['vertex_point'] = [Point(x, y) 
                                for x, y in zip(gtfs_shapes['shape_pt_lon'].to_numpy()
                                ,gtfs_shapes['shape_pt_lat'].to_numpy())]
gtfs_shape_lines = (gtfs_shapes.groupby('shape_id')[['vertex_point']]
                                .agg(lambda x: LineString(list(x)))
                                .reset_index()
                                .rename(columns={'vertex_point':'route_line'}))
gtfs_shape_lines_gdf = gpd.GeoDataFrame(gtfs_shape_lines, crs="EPSG:4326", geometry='route_line')
```

