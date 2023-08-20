import os
import requests
import pandas as pd
import geopandas as gpd
import datetime
import polyline
from shapely.geometry import LineString, Point
import boto3
import random
import seaborn as sns

aws_access_key = os.environ['aws_access_key']
aws_secret_key = os.environ['aws_secret_key']

def load_trimet_boundary_from_s3():
    '''
    future function to load boundary from s3 so we can run this as a github action 
    NOTE: we may not need to load from s3 because we can load from the github repo..
    '''
    pass

def random_points_within(poly, num_points):
    min_x, min_y, max_x, max_y = poly.bounds

    points = []

    while len(points) < num_points:
        random_point = Point((random.uniform(min_x, max_x), random.uniform(min_y, max_y)))
        if (random_point.within(poly)):
            points.append(random_point)

    return points

def generate_points_within_tm_boundary(tm_boundary, trimet_crs):
    '''
    generate 2 points and make sure they are > 1 mile apart
    '''
    
    #the length of the line connecting the two points is the 
    #distance between them (as crow flies)
    #convert crs if not already
    tm_boundary_proj = tm_boundary.to_crs(trimet_crs)
    dist_btw_points = 0
    while dist_btw_points < 1:
        points_list = random_points_within(tm_boundary_proj.unary_union, 2)
        dist_btw_points = LineString(points_list).length/5280

    df = pd.DataFrame(zip(points_list,['origin', 'destination']), columns=['points','point_type'])
    gdf_points = gpd.GeoDataFrame(df,crs=trimet_crs ,geometry='points')
    
    gdf_points_reproject = gdf_points.to_crs("EPSG:4326")

    gdf_points_reproject['points_str'] = gdf_points_reproject['points'].apply(lambda x: f"{round(x.y,6)}, {round(x.x,6)}")

    return (gdf_points_reproject, dist_btw_points)

def call_planner(fromPlace, toPlace):
    ''' 
    fromPlace = "lat, lon"
    toPlace = "lat,lon"
    '''
    date = datetime.datetime.now().strftime("%Y-%m-%d")
    base_url = "https://maps.trimet.org/otp_mod/plan"
    time="12:00"
    mode="WALK,BUS,TRAM,RAIL,GONDOLA"
    maxWalkDistance=5280/2
    walkSpeed=1.34
    numItineraries=3
    r = requests.get(url=base_url, params={'fromPlace':fromPlace, 'toPlace':toPlace, 'date':date, 'time':time
                                    ,'mode':mode, 'maxWalkDistance':maxWalkDistance, 'walkSpeed':walkSpeed
                                    ,'numItineraries':numItineraries})
    assert(r.status_code==200)
    return r.json()

def decode_create_leg_line(encoded_linestring):
    '''google polyline encoded linestring'''
    reformatted_coords = []
    original_coords = polyline.decode(encoded_linestring)
    for coord in original_coords:
        reformatted_coords.append((coord[1],coord[0]))
    return LineString(reformatted_coords)

def get_itinerary_paths(planner_response):
    ''' 
    planner_response = json_response from TriMet trip planner
    '''
    itineraries_df = pd.DataFrame()
    for itin_idx, itinerary in enumerate(planner_response['plan']['itineraries']):
        totalTime = itinerary['duration']
        walkTime = itinerary['walkTime']
        transitTime = itinerary['transitTime']
        waitingTime = itinerary['waitingTime']
        walkDistance = itinerary['walkDistance']
        for leg_idx, leg in enumerate(itinerary['legs']):
            route_id = leg.get('routeId','WALK').split(":")[-1]
            mode = leg['mode']
            fromName = leg['from']['name']
            toName = leg['to']['name']
            fromStopCode = leg['from'].get('stopCode','')
            toStopCode = leg['to'].get('stopCode','')
            legGeometry = decode_create_leg_line(leg['legGeometry']['points'])
            leg_df = pd.DataFrame([[itin_idx, totalTime, walkTime, transitTime, waitingTime, walkDistance,
                                   leg_idx, route_id, mode, fromStopCode, fromName, toStopCode, toName,
                                   legGeometry]],
                                   columns=['itin_idx', 'totalTime', 'walkTime', 'transitTime', 'waitingTime', 'walkDistance',
                                   'leg_id', 'route_id', 'mode', 'fromStopCode', 'fromName', 'toStopCode', 'toName',
                                   'legGeometry'])
            itineraries_df = pd.concat([itineraries_df,leg_df])
    return itineraries_df

def create_intinerary_gdf_and_reduce(itineraries_df):
    ''' '''
    itineraries_gdf = gpd.GeoDataFrame(itineraries_df, crs="4326", geometry="legGeometry")

    #reduce "stay on" routes
    itineraries_reduce_stayon_routes = itineraries_gdf.drop_duplicates(subset=['itin_idx','route_id'])

    unique_combinations = itineraries_reduce_stayon_routes[itineraries_reduce_stayon_routes['route_id']!='WALK'].groupby('itin_idx').agg(route_id_list=('route_id',list)).reset_index().drop_duplicates(subset='route_id_list')
    unique_combinations['route_id_combo'] = unique_combinations['route_id_list'].apply(lambda x: " to ".join(x))

    itineraries_reduced = itineraries_reduce_stayon_routes.merge(unique_combinations[['itin_idx','route_id_combo']], how='inner', on='itin_idx')

    itinerary_routes_reduced = itineraries_reduced[itineraries_reduced['route_id']!='WALK'].drop_duplicates(subset='route_id').copy()

    return (itineraries_reduced, itinerary_routes_reduced)

def generate_random_points_make_itinerary(tm_boundary, trimet_crs):
    ''' 
    function to make sure the itinerary has a path
    '''
    error_length = 5
    tries = 1
    while error_length > 0:
        gdf_points, dist_btw_points = generate_points_within_tm_boundary(tm_boundary, trimet_crs)
        fromplace = gdf_points[gdf_points['point_type']=='origin']['points_str'].to_numpy()[0]
        toplace = gdf_points[gdf_points['point_type']=='destination']['points_str'].to_numpy()[0]
        json_content = call_planner(fromplace, toplace)
        error_length = len(json_content.get('error',''))
        if error_length == 0:
            #adding logic to make sure the trip planning is not crazy long
            #this is a crude way of making sure there is 1 itinerary with 2 routes
            num_routes_in_itin = []
            for itinerary in json_content['plan']['itineraries']:
                num_routes = len([leg for leg in itinerary['legs'] if 'TriMet' in leg.get('routeId','')])
                num_routes_in_itin.append(num_routes)
            if min(num_routes_in_itin) > 2:
                error_length = 1
        tries += 1
    print(f"number of tries {tries}")
    itineraries_df = get_itinerary_paths(json_content)
    itineraries_reduced, itinerary_routes_reduced = create_intinerary_gdf_and_reduce(itineraries_df)
    return (gdf_points, itineraries_reduced, itinerary_routes_reduced, tries)

def set_up_itineraries_for_site(itinerary_routes_reduced, itineraries_reduced):
    ''' add fields to itinerary_routes_reduced to provide properties for the site'''
    itinerary_routes_reduced['route_id'] = itinerary_routes_reduced['route_id'].astype(int)
    gtfs_routes = pd.read_csv("routes.txt")
    itinerary_routes_long_name = itinerary_routes_reduced.merge(gtfs_routes[['route_id','route_long_name']], how='inner', on='route_id')
    # Get Unique continents
    color_labels = itinerary_routes_long_name['route_id'].unique()
    # List of colors in the color palettes
    hex_values = sns.color_palette("Set2", len(color_labels)).as_hex()
    # Map continents to the colors
    color_map = dict(zip(color_labels, hex_values))
    color_map['WALK'] = '#bf5f58'

    color_map_str = {str(item[0]):item[1] for item in color_map.items()}

    itinerary_routes_long_name['route_color'] = itinerary_routes_long_name['route_id'].apply(lambda x: color_map[x])
    itinerary_routes_long_name['dropdown_route'] = itinerary_routes_long_name.apply(lambda x: str(x['route_id'])+" - "+str(x['route_long_name']), axis=1)
    itineraries_reduced_with_long_name = itineraries_reduced.merge(gtfs_routes[['route_id','route_long_name']].astype(str), how='left', on='route_id')

    itineraries_reduced_with_long_name['route_long_name'] = itineraries_reduced_with_long_name['route_long_name'].fillna(value='WALK')

    itineraries_reduced_with_long_name['dropdown_route'] = itineraries_reduced_with_long_name.apply(lambda x: str(x['route_id'])+" - "+str(x['route_long_name']), axis=1)

    itineraries_reduced_with_long_name['route_color'] = itineraries_reduced_with_long_name['route_id'].apply(lambda x: color_map_str[x])

    return (itinerary_routes_long_name, itineraries_reduced_with_long_name)


if __name__ == "__main__":
    tm_boundary = gpd.read_file("tm_route_buffer_bounds.geojson")
    trimet_crs = "EPSG:2913"
    gdf_points, itineraries_reduced, itinerary_routes_reduced, tries = generate_random_points_make_itinerary(tm_boundary, trimet_crs)
    
    origin_destination_centriod = LineString(list(gdf_points['points'].to_numpy())).centroid

    origin_destination_centriod_gdf = gpd.GeoDataFrame(pd.DataFrame(['origin_dest_centroid'], columns=['id']),crs="EPSG:4326", geometry=[origin_destination_centriod])

    itinerary_routes_long_name, itineraries_reduced_with_long_name = set_up_itineraries_for_site(itinerary_routes_reduced, itineraries_reduced)

    gdf_points.to_file("origin_destination_points.geojson", driver="GeoJSON")
    client = boto3.client(
                        's3',
                        aws_access_key_id=aws_access_key,
                        aws_secret_access_key=aws_secret_key
                    )
    client.upload_file("origin_destination_points.geojson", "meysohn-sandbox", "trimet_trip_planner/origin_destination_points.geojson",ExtraArgs={'ACL':'public-read'})

    itineraries_reduced_with_long_name.to_file("itineraries_reduced_with_long_name.geojson", driver="GeoJSON")
    client = boto3.client(
                        's3',
                        aws_access_key_id=aws_access_key,
                        aws_secret_access_key=aws_secret_key
                    )
    client.upload_file("itineraries_reduced_with_long_name.geojson", "meysohn-sandbox", "trimet_trip_planner/itineraries_reduced_with_long_name.geojson",ExtraArgs={'ACL':'public-read'})

    itinerary_routes_long_name.to_file("itinerary_routes_long_name.geojson", driver="GeoJSON")
    client = boto3.client(
                        's3',
                        aws_access_key_id=aws_access_key,
                        aws_secret_access_key=aws_secret_key
                    )
    client.upload_file("itinerary_routes_long_name.geojson", "meysohn-sandbox", "trimet_trip_planner/itinerary_routes_long_name.geojson",ExtraArgs={'ACL':'public-read'})

    origin_destination_centriod_gdf.to_file("origin_destination_centriod.geojson", driver="GeoJSON")
    client = boto3.client(
                        's3',
                        aws_access_key_id=aws_access_key,
                        aws_secret_access_key=aws_secret_key
                    )
    client.upload_file("origin_destination_centriod.geojson", "meysohn-sandbox", "trimet_trip_planner/origin_destination_centriod.geojson",ExtraArgs={'ACL':'public-read'})