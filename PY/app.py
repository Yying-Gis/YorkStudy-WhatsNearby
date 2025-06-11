from flask import Flask, request, jsonify
from flask_cors import CORS
import osmnx as ox
import json
import networkx as nx
from geopy.distance import geodesic

app = Flask(__name__)
CORS(app)
@app.route('/')

# data from data folder

with open('data/libraries.geojson') as f:
    libraries = json.load(f)
with open('data/hospitals.geojson') as f:
    hospitals = json.load(f)
with open('data/pharmacies.geojson') as f:
    pharmacies = json.load(f)

# data from GitHub (save as GraphML)
try:
    york_graph = ox.load_graphml('data/york_walk.graphml')
except:
    # or download fm OSM
    york_graph = ox.graph_from_place('York, UK', network_type='walk')
    ox.save_graphml(york_graph, 'data/york_walk.graphml')

@app.route('/analyze', methods=['POST'])
def analyze_location():
    data = request.get_json()
    lat = data['lat']
    lng = data['lng']
    
    # 1. find the nearest node point
    orig_node = ox.distance.nearest_nodes(york_graph, lng, lat)
    
    # 2. find the nearest facilities 
    def calculate_nearest(feature_type, features):
        nearest = None
        min_distance = float('inf')
        path = None
        
        for feature in features['features']:
            coords = feature['geometry']['coordinates']
            dest_lng, dest_lat = coords[0], coords[1]
            dest_node = ox.distance.nearest_nodes(york_graph, dest_lng, dest_lat)
            
            try:
                # calculate the shortest
                path_nodes = nx.shortest_path(york_graph, orig_node, dest_node, weight='length')
                path_length = sum(ox.utils_graph.get_route_edge_attributes(york_graph, path_nodes, 'length'))
                
                if path_length < min_distance:
                    min_distance = path_length
                    nearest = feature
                    path = [[york_graph.nodes[node]['y'], york_graph.nodes[node]['x']] for node in path_nodes]
            except nx.NetworkXNoPath:
                continue
                
        walk_time = int((min_distance / 80) * 60)  # assum walking speed 80m/mins
        
        return {
            'feature': nearest['properties'] if nearest else None,
            'distance': round(min_distance),
            'walk_time': walk_time,
            'path': path
        }
    
    # 3.calculate facilites
    results = {
        'location': [lat, lng],
        'nearest_library': calculate_nearest('library', libraries),
        'nearest_hospital': calculate_nearest('hospital', hospitals),
        'nearest_pharmacy': calculate_nearest('pharmacy', pharmacies)
    }
    
    return jsonify(results)

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)