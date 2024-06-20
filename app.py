from flask import Flask, render_template, jsonify, request, make_response, render_template_string, Response
import json
from influxdb_client import InfluxDBClient
import requests

fields = ['latitude', 'longitude', 'TempIn', 'HumIn', 'place']

coordinates = [
        (40.84431667,14.23892778),
        (40.79166667 ,14.18694444),
        (40.936502,14.729150),
        (40.938759,14.725191),
        (40.6056513,14.3637172),
        (40.76666667,14.03333336),
        (40,716, 13.8666),
        (40.549238 ,14.2323)

        ]

def getOfflineStations(coordinates):
    staticStations = {}
    for idx, coordinate in enumerate(coordinates):
        print(idx, type(coordinate))
        staticStations[str(idx)] = {}
        staticStations[str(idx)]['longitude'] = coordinate[0]
        staticStations[str(idx)]['latitude'] = coordinate[1]
        staticStations[str(idx)]['TempIn'] = "N/A"
        staticStations[str(idx)]['HumIn'] = "N/A"
        staticStations[str(idx)]['place'] = "Not Installed!"
        staticStations[str(idx)]['installed'] = "Not Installed!"
        staticStations[str(idx)]['model'] = "DAVIS Vantage Pro 2"
        staticStations[str(idx)]['type'] = "ws_off"
        staticStations[str(idx)]['ente'] = "N/A"
        

    return staticStations

def getStations():
    offlineStations = getOfflineStations(coordinates)
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

            stations[record.values.get("topic")]['type'] = "ws_on"
            stations[record.values.get("topic")]['model'] = "DAVIS Vantage Pro 2"
            stations[record.values.get("topic")]['installed'] = "11/05/2024"
            stations[record.values.get("topic")]['ente'] = "Marina"

    print(stations | offlineStations)
    return stations | offlineStations


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
