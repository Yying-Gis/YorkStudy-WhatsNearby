from flask import Flask
import os

app = Flask(__name__)

@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"

if __name__ == '__main__':
    app.run(debug=True)

DATA_DIR = os.path.join(os.path.dirname(__file__), "Data")
print(f"Current directory: {os.getcwd()}")
print(f"DATA_DIR contents: {os.listdir(DATA_DIR)}")