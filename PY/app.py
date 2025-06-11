from flask import Flask, request, jsonify
from flask_cors import CORS
import osmnx as ox
import json
import networkx as nx
from geopy.distance import geodesic
import os
import sys



app = Flask(__name__)
CORS(app)

@app.route('/')

print("Python version:", sys.version)
print("os module test:",  print(os.__file__))
print("Current file path:", __file__)
print("Data dir path:", os.path.join(os.path.dirname(__file__), "data"))


# define directory's path
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

# 讀取GeoJSON工具
def load_geojson(category, filename):
    with open(os.path.join(DATA_DIR, category, filename)) as f:
        return json.load(f)

# load all data 
libraries = load_geojson('Facility', 'libraries.geojson')
supermarkets = load_geojson('Facility', 'supermarkets.geojson')
restaurants = load_geojson('Facility', 'restaurants.geojson')
stations = load_geojson('Transport', 'stations.geojson')
bus_stops = load_geojson('Transport', 'bus_stops.geojson')
hospitals = load_geojson('Medical', 'hospitals.geojson')
pharmacies = load_geojson('Medical', 'pharmacies.geojson')
gp_surgeries = load_geojson('Medical', 'gp_surgeries.geojson')
schools = load_geojson('School', 'schools.geojson')

# load GraphML
GRAPH_PATH = os.path.join(DATA_DIR, 'york_walk.graphml')
try:
    york_graph = ox.load_graphml(GRAPH_PATH)
except:
    york_graph = ox.graph_from_place('York, UK', network_type='walk')
    ox.save_graphml(york_graph, GRAPH_PATH)

def calculate_nearest(graph, orig_lat, orig_lng, features):
    orig_node = ox.distance.nearest_nodes(graph, orig_lng, orig_lat)
    min_dist = float('inf')
    nearest = None
    for feature in features['features']:
        lng, lat = feature['geometry']['coordinates'][0:2]
        dest_node = ox.distance.nearest_nodes(graph, lng, lat)
        try:
            path_nodes = nx.shortest_path(graph, orig_node, dest_node, weight='length')
            path_length = sum(ox.utils_graph.get_route_edge_attributes(graph, path_nodes, 'length'))
            if path_length < min_dist:
                min_dist = path_length
                nearest = feature
        except nx.NetworkXNoPath:
            continue
    walk_time = int((min_dist / 80) * 60)  # 80m/min
    return {
        'feature': nearest['properties'] if nearest else None,
        'distance': round(min_dist),
        'walk_time': walk_time
    }

@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.get_json()
    lat, lng = data['lat'], data['lng']
    result = {
        'location': [lat, lng],
        'nearest_library': calculate_nearest(york_graph, lat, lng, libraries),
        'nearest_supermarket': calculate_nearest(york_graph, lat, lng, supermarkets),
        'nearest_restaurant': calculate_nearest(york_graph, lat, lng, restaurants),
        'nearest_station': calculate_nearest(york_graph, lat, lng, stations),
        'nearest_bus_stop': calculate_nearest(york_graph, lat, lng, bus_stops),
        'nearest_hospital': calculate_nearest(york_graph, lat, lng, hospitals),
        'nearest_pharmacy': calculate_nearest(york_graph, lat, lng, pharmacies),
        'nearest_gp_surgery': calculate_nearest(york_graph, lat, lng, gp_surgeries),
        'nearest_school': calculate_nearest(york_graph, lat, lng, schools),
    }
    return jsonify(result)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)