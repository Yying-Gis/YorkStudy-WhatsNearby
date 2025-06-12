from flask import Flask, request, jsonify
from flask_cors import CORS
import osmnx as ox
import geopandas as gpd
import networkx as nx
import os
import sys
from functools import lru_cache
import time

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
        return ox.load_graphml(GRAPH_PATH)
    except Exception as e:
        print(f"failed forget graphml file: {e}")
        try:
            # retry
            for _ in range(3):
                try:
                    york_graph = ox.graph_from_place('York, UK', network_type='walk')
                    ox.save_graphml(york_graph, GRAPH_PATH)
                    return york_graph
                except Exception as e:
                    print(f"try {_+1}/3 fail: {e}")
                    time.sleep(5)
                    continue
            raise Exception("Unable to get the graphml file, please try it later ")
        except Exception as e:
            print(f"Failed to create new graphic: {e}")
            raise

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
def calculate_nearest_optimized(graph, orig_lat, orig_lng, gdf):
    if gdf.empty:
        return {'feature': None, 'distance': None, 'walk_time': None}
    
    orig_node = ox.distance.nearest_nodes(graph, orig_lng, orig_lat)
    min_dist = float('inf')
    nearest_properties = None
    nearest_path = None
    nearest_node = None
    
    for _, row in gdf.iterrows():
        point = row['geometry']
        if point.geom_type == 'Point':
            lng, lat = point.x, point.y
        else:
            # get the first data if more than one point/polygon
            lng, lat = point.coords[0][0:2]
        
        dest_node = ox.distance.nearest_nodes(graph, lng, lat)
        try:
            path_length = nx.shortest_path_length(graph, orig_node, dest_node, weight='length')
            if path_length < min_dist:
                min_dist = path_length
                nearest_properties = row.drop('geometry').to_dict()
        except nx.NetworkXNoPath:
            continue
    
    walk_time = int((min_dist / 80) * 60) if min_dist != float('inf') else None
    if nearest_node is not None:
        path_nodes = nx.shortest_path(graph, orig_node, nearest_node, weight='length')
        path_coords = [[graph.nodes[n]['y'], graph.nodes[n]['x']] for n in path_nodes]
    else:
        path_coords = None
    
    return {
        'feature': nearest_properties,
        'distance': round(min_dist) if min_dist != float('inf') else None,
        'walk_time': walk_time
    }

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        data = request.get_json()
        lat, lng = data['lat'], data['lng']
        graph = load_graph()
        
        # loading the result
        result = {
            'location': [lat, lng],
            'nearest_hospital': calculate_nearest_optimized(
                graph, lat, lng, load_geodata('Medical', 'hospital.geojson')),
            'nearest_pharmacy': calculate_nearest_optimized(
                graph, lat, lng, load_geodata('Medical', 'Pharmacies.geojson')),
            'nearest_gp_surgery': calculate_nearest_optimized(
                graph, lat, lng, load_geodata('Medical', 'GP_Surgeries.geojson')),
        }
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("Python version:", sys.version)
    print("Current file path:", __file__)
    print("Data dir path:", os.path.join(os.path.dirname(__file__), "Data"))
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)