from flask import Flask, request, jsonify
from flask_cors import CORS
import osmnx as ox
import json
import networkx as nx
from geopy.distance import geodesic
import sys
import os

app = Flask(__name__)

@app.route("/")


if __name__ == '__main__':
    app.run(debug=True)

DATA_DIR = os.path.join(os.path.dirname(__file__), "Data")
print(f"Current directory: {os.getcwd()}")
print(f"DATA_DIR contents: {os.listdir(DATA_DIR)}")
print(f"Python version:", sys.version)
print(f"os module test:", os.__file__)
print(f"Current file path:", __file__)
print(f"Data dir path:", os.path.join(os.path.dirname(__file__), "Data"))

def load_geojson(category, filename):
    with open(os.path.join(DATA_DIR, category, filename)) as f:
        return json.load(f)

# load all data 
libraries = load_geojson('Facility', 'libraries.geojson')
def hello_world():
    return libraries
