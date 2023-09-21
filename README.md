# TriMet Trip Game

## Current Version
The current version of the game is playable [here](https://d1tu6vkegvnwyd.cloudfront.net/trimet_trip_game.html).

## Purpose
The purpose of the game is to learn TriMet bus and MAX routes. It's easy to _get somewhere_ by transit. One can look up transit directions on Trimet.org or Google Maps. This does not help to _learn_ transit in a city. In fact, city dwellers generally stay in localized areas so they are not exposed to all routes. This game helps all users engage with TriMet's service and learn by guessing the correct itinerary. Play every day and you'll be surprised at what you learn!

## Underlying Data
The game has several elements described below:
- **route paths** - routes are built from the gtfs shapes.txt file.
- **itineraries** - itineraries and "leg" geometries are provided by TriMet's trip planner.
- **origin | destination** - origin and destination points are randomly generated points within 0.5 miles of a TriMet route shape.
- **basemap** - [Stanem Design](http://stamen.com) basemap is used to remove a lot of detail and focus mainly on the origin and destination relative location.

## Backend Workflow
_Semi-regular (when GTFS changes)_:
1.	Download the latest gtfs.zip file from TriMet
  ```python
from zipfile import ZipFile
from urllib.request import urlopen
resp = urlopen("https://developer.trimet.org/schedule/gtfs.zip")
myzip = ZipFile(BytesIO(resp.read()))
myzip.extractall('gtfs/')
```
2.	Create route list for game dropdown from routes.txt
3.	Create route lines from shapes.txt, buffer the lines, union all lines together and save as geojson
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
_3x Daily_:
1.	Generate a random origin and destination point within the route shape from step #3 above.
2.	Submit the origin and destination points to the TriMet trip planner API
3.	Verify that there is a viable itinerary
4.	Return all possible itineraries to populate the game
5.	Submit the origin and destination points to Mapbox’s API and return traffic driving time to the game



## Gameplay
The game starts with a red circle for the origin and destination point. The goal of the game is to select the route(s) to get from the origin point to the destination point via a searchable dropdown.

![image](https://github.com/sidetrackedmind/trimet_trip_game/assets/24400820/ca23e86d-9bcb-4a38-81b5-ca40c3450404)

For every correct guess, the route will show up on the map in a bright color and the corresponding route circle within the itinerary bubble will turn blue. 

![image](https://github.com/sidetrackedmind/trimet_trip_game/assets/24400820/f6effc54-d818-4857-922b-defbb027f2d7)

For every incorrect guess, the corresponding route will show up in a dark red line on the map and the bad guess tracker count will increment up by one. 

![image](https://github.com/sidetrackedmind/trimet_trip_game/assets/24400820/d49e9b65-520a-4ef4-8c3c-87c8d0ea4777)

When all routes within an itinerary bubble are guessed correctly, the whole itinerary bubble turns blue and says “You WIN!” with the full travel time of the itinerary.

![image](https://github.com/sidetrackedmind/trimet_trip_game/assets/24400820/b4d82ff0-1ca3-40e7-801b-5491735c8aed)

