from flask import Flask, render_template, jsonify, request, make_response, render_template_string, Response
import json
from influxdb_client import InfluxDBClient
import requests

fields = ['latitude', 'longitude', 'TempIn', 'HumIn', 'place']

coordinates = [
        [40.84431667,14.23892778, "Castel Sant'Elmo (NA)", "ws_off", "Weather Station"],
        [40.79166667 ,14.18694444, "Gaiola", "ws_off", "Weather Station"],
        [40.936502,14.729150, "Montevergine", "ws_off", "Weather Station"],
        [40.938759,14.725191, "Montevergine alto", "ws_off", "Weather Station"],
        [40.6056513,14.3637172, "Sant'Agata (Sorrento)", "ws_off", "Weather Station"],
        [40.76666667,14.03333336, "Procida", "ws_off", "Weather Station"],
        [40,716, 13.8666, "Ischia", "ws_off", "Weather Station"],
        [40.549238 ,14.2323, "Capri", "ws_off", "Weather Station"],

        [40.8435 ,14.2394, "Castel Sant’Elmo", "radar_off", "Weather Radar"],
        [41.0486 ,15.2329, "Trevico (AV)", "radar_off", "Weather Radar"],

        [40.745833 ,13.940556, "Ischia", "tidegauge_off", "Tide gauge (Mareografi)"],
        [40.7161  ,14.4747 , "Marina di Stabia", "tidegauge_off", "Tide gauge (Mareografi)"],

        [40.6188 ,14.3247, "Scoglio Vervece ", "wavebuoy_off", "Wavebuoy (Ondametri)"],
        [40.745833  ,13.940556 , "Ischia", "wavebuoy_off", "Wavebuoy (Ondametri)"],

        [40.6188 ,14.3247, "Scoglio Vervece ", "mooring_off", "Mooring"],
        
        [40.7714 ,14.0952, "Miseno", "owbuoy_off", "Ocean-Weather buoy (Boa Multiparametrica)"],

        [41.2463 ,13.5897, "Formia", "hf_off", "HF Radar System"],
        [41.2463 ,13.4230, "Ventotene", "hf_off", "HF Radar System"],
        [40.7798 ,14.088, "Miseno", "hf_off", "HF Radar System"],
        [40.8122 ,14.3344, "Portici", "hf_off", "HF Radar System"],
        [40.6982 ,14.4809, "Castellammare", "hf_off", "HF Radar System"],

        [40.6915 ,14.2072, "Glider", "glider_off", "Glider"]
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
        staticStations[str(idx)]['place'] = coordinate[2]
        staticStations[str(idx)]['installed'] = "Not Installed!"
        staticStations[str(idx)]['model'] = "N/A"
        staticStations[str(idx)]['type'] = coordinate[3]
        staticStations[str(idx)]['ente'] = "N/A",
        staticStations[str(idx)]['typology'] = coordinate[4]
        

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
            stations[record.values.get("topic")]['typology'] = "Weather Station"

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
    app.run(debug=True, host='0.0.0.0', port=5000)
