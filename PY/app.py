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

# 配置 OSMnx 設定
ox.settings.timeout = 300
ox.settings.log_console = True
ox.settings.use_cache = True
ox.settings.cache_folder = os.path.join(os.path.dirname(__file__), "cache")

@app.route('/')
def home():
    return "Hello Render"

# 定義資料目錄路徑
DATA_DIR = os.path.join(os.path.dirname(__file__), "Data")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(ox.settings.cache_folder, exist_ok=True)

# 使用 LRU 快取來緩存圖形資料
@lru_cache(maxsize=1)
def load_graph():
    GRAPH_PATH = os.path.join(DATA_DIR, 'york_walk_with_bearing.graphml')
    try:
        return ox.load_graphml(GRAPH_PATH)
    except Exception as e:
        print(f"載入圖形失敗: {e}")
        try:
            # 重試機制
            for _ in range(3):
                try:
                    york_graph = ox.graph_from_place('York, UK', network_type='walk')
                    ox.save_graphml(york_graph, GRAPH_PATH)
                    return york_graph
                except Exception as e:
                    print(f"嘗試 {_+1}/3 失敗: {e}")
                    time.sleep(5)
                    continue
            raise Exception("無法獲取地圖資料，請稍後再試")
        except Exception as e:
            print(f"創建新圖形失敗: {e}")
            raise

# 按需載入 GeoJSON 資料的函數
def load_geodata(category, filename):
    filepath = os.path.join(DATA_DIR, category, filename)
    try:
        # 使用 Geopandas 讀取並只保留必要欄位
        gdf = gpd.read_file(filepath)
        # 簡化幾何資料以減少記憶體使用
        if gdf.crs is None:
            gdf = gdf.set_crs(epsg=4326)
        return gdf[['geometry']].copy()  # 只保留幾何資料
    except Exception as e:
        print(f"載入 {filename} 失敗: {e}")
        return gpd.GeoDataFrame()  # 返回空的 GeoDataFrame

# 記憶體優化的最近點計算函數
def calculate_nearest_optimized(graph, orig_lat, orig_lng, gdf):
    if gdf.empty:
        return {'feature': None, 'distance': None, 'walk_time': None}
    
    orig_node = ox.distance.nearest_nodes(graph, orig_lng, orig_lat)
    min_dist = float('inf')
    nearest_properties = None
    
    # 批次處理點位
    for _, row in gdf.iterrows():
        point = row['geometry']
        if point.geom_type == 'Point':
            lng, lat = point.x, point.y
        else:
            # 如果是多點或多邊形，取第一個座標
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
        
        # 按需載入需要的資料集
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