from flask import Flask, request, jsonify
from flask_cors import CORS
import osmnx as ox
import geopandas as gpd
import networkx as nx
import os
import sys
from functools import lru_cache
import time
from shapely.geometry import Point
import requests

app = Flask(__name__)
CORS(app)

# setting OSMnx 
ox.settings.timeout = 300
ox.settings.log_console = True
ox.settings.use_cache = True
ox.settings.cache_folder = os.path.join(os.path.dirname(__file__), "cache")

"""@app.route('/')"""

# define data irectory
DATA_DIR = os.path.join(os.path.dirname(__file__), "Data")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(ox.settings.cache_folder, exist_ok=True)

# using LRU to get graphml file
@lru_cache(maxsize=1)

def load_graph():
    GRAPH_PATH = os.path.join(DATA_DIR, 'york_walk_with_bearing.graphml')
    try:
        walk_Graph = ox.load_graphml(GRAPH_PATH)
        # 簡化圖形 - 只保留必要屬性
        walk_Graph = ox.utils_graph.get_undirected(walk_Graph)
        for _, _, data in walk_Graph.edges(data=True):
            for attr in list(data.keys()):
                if attr not in ['length', 'geometry']:
                    del data[attr]
        return walk_Graph
    except Exception as e:
        print(f"Failed to load graph: {e}")
        return None

# load geojson
def load_geodata(category, filename):
    filepath = os.path.join(DATA_DIR, category, filename)
    try:
        gdf = gpd.read_file(filepath)
        # Simplify geometry to reduce memory usage
        if gdf.crs is None:
            gdf = gdf.set_crs(epsg=4326)
        return gdf[['geometry']].copy()  # keep Simplify geometry
    except Exception as e:
        print(f"loading {filename} failure: {e}")
        return gpd.GeoDataFrame()  # return a empty GeoDataFrame

# Memory-efficient nearest point calculation function
def calculate_nearest_optimized(graph, orig_lat, orig_lng, gdf, n_closest=3):
    if gdf.empty or graph is None:
        return {'feature': None, 'distance': None, 'walk_time': None, 'path': None}
    try: 
        orig_node = ox.distance.nearest_nodes(graph, orig_lng, orig_lat)
        candidates = []
        for _, row in gdf.iterrows():
            point = row['geometry']
            if point.geom_type == 'Point':
                lng, lat = point.x, point.y
            else:
                lng, lat = point.coords[0][0:2]
            dist = ox.distance.great_circle_vec(orig_lat, orig_lng, lat, lng)
            candidates.append((dist, lat, lng, row))
        
        candidates.sort()
        min_dist = float('inf')
        result = {'feature': None, 'distance': None, 'walk_time': None, 'path': None}
        
        for dist, lat, lng, row in candidates[:3]:
            dest_node = ox.distance.nearest_nodes(graph, lng, lat)
            try:
                path_length = nx.shortest_path_length(graph, orig_node, dest_node, weight='length')
                if path_length < min_dist:
                    min_dist = path_length
                    result = {
                        'feature': row.drop('geometry').to_dict(),
                        'distance': round(min_dist),
                        'walk_time': int((min_dist / 80) * 60),
                        'path': [[graph.nodes[n]['y'], graph.nodes[n]['x']] 
                               for n in nx.shortest_path(graph, orig_node, dest_node, weight='length')]
                    }
            except nx.NetworkXNoPath:
                continue
        
        return result
    except Exception as e:
        print(f"Error in nearest calculation: {e}")
        return {'feature': None, 'distance': None, 'walk_time': None, 'path': None}

 # get postcode   
def get_postcode(lat, lng):
    try:
        response = requests.get(f"https://api.postcodes.io/postcodes?lon={lng}&lat={lat}")
        if response.status_code == 200:
            data = response.json()
            if data['result'] and len(data['result']) > 0:
                return data['result'][0]['postcode']
        return None
    except Exception as e:
        print(f"Failed to retrieve postal code: {e}")
        return None


@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        data = request.get_json()
        lat, lng = data['lat'], data['lng']
         # get postcode 
        postcode = get_postcode(lat, lng)
        
        if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
            return jsonify({'error': 'Invalid coordinates'}), 400
        
        graph = load_graph()
        if graph is None:
            return jsonify({'error': 'Map data not available'}), 503
        
        #load geojson if need
        def get_nearest(category, filename):
            gdf = load_geodata(category, filename)
            result = calculate_nearest_optimized(graph, lat, lng, gdf)
            del gdf  
            return result
        
        # loading the result
        result = {
            'location': [lat, lng],
            'postcode': postcode,
            'nearest_hospital': get_nearest('Medical', 'hospital.geojson'),
            'nearest_pharmacy': get_nearest('Medical', 'Pharmacies.geojson'),
            'nearest_gp_surgery': get_nearest('Medical', 'GP_Surgeries.geojson'),
        }
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    

    
if __name__ == '__main__':
    #print("Python version:", sys.version)
    #print("Current file path:", __file__)
    #print("Data dir path:", os.path.join(os.path.dirname(__file__), "Data"))
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)