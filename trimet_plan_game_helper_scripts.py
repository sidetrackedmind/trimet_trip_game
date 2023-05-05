import os
os.environ['USE_PYGEOS'] = '0'
import requests
import pandas as pd
import geopandas as gpd
import datetime
from shapely import wkt, wkb
import polyline
from shapely.geometry import LineString, Point
import boto3
import numpy as np
import random
import json
import folium
import seaborn as sns


def random_points_within(poly, num_points):
    min_x, min_y, max_x, max_y = poly.bounds

    points = []

    while len(points) < num_points:
        random_point = Point([random.uniform(min_x, max_x), random.uniform(min_y, max_y)])
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

    df = pd.DataFrame()
    df['points'] = points_list
    df['points'] = df['points'].apply(Point)
    gdf_points = gpd.GeoDataFrame(df,crs=trimet_crs ,geometry='points')
    gdf_points_reproject = gdf_points.to_crs("EPSG:4326")

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