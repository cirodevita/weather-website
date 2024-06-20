from flask import Flask, render_template, jsonify, request, make_response, render_template_string, Response
import json
from influxdb_client import InfluxDBClient
import requests

fields = ['latitude', 'longitude', 'TempIn', 'HumIn', 'place']


def getStations():
    url = "http://193.205.230.6:8086"
    token = "__jNBfyWPRNHEau33ebp2PzZSqoaHN5WkCqqZcELncYRpuF13LS-kV-cYmoq7zI3so3rtiFd2Kou6-md06PBdw=="
    org = "Parthenope"
    bucket = "ws"

    # Crea il client InfluxDB
    client = InfluxDBClient(url=url, token=token, org=org)

    query_api = client.query_api()

    query = """from(bucket: "ws") |> range(start: -3h) |> last()"""
    tables = query_api.query(query, org=org)

    devices = []

    stations = {}
    for table in tables:
        for record in table.records:
            if record.values.get("topic") not in stations:
                stations[record.values.get("topic")] = {}

            if record.get_field() in fields:
                stations[record.values.get("topic")][record.get_field()] = record.get_value()
    print(stations)
    return stations


app = Flask(__name__)


@app.after_request
def add_header(response):
    # Consenti l'incorporazione del sito web
    response.headers['Content-Security-Policy'] = "frame-ancestors 'self' *"
    return response


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/coordinates')
def get_coordinates():
    stations = getStations()

    return jsonify(stations)


if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5000)
