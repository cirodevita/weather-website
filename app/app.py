from io import StringIO
from dotenv import load_dotenv
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, request, jsonify, Response
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_migrate import Migrate
from models import db, User, Instrument
from flask_bcrypt import Bcrypt
from werkzeug.utils import secure_filename
from sqlalchemy.exc import IntegrityError
from influxdb_client import InfluxDBClient
import utils
import csv
import os
import time

load_dotenv()

app = Flask(__name__)

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER')
app.config['ALLOWED_EXTENSIONS'] = set(os.getenv('ALLOWED_EXTENSIONS').split(','))

db.init_app(app)
bcrypt = Bcrypt(app)

migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


instrument_types = {
    "ws_on": {
        "name": "Stazione Meteorologica",
        "variables": "TempOut, HumOut, WindSpeed, WindDir, RainRate, Barometer"
    },
    "ws_off": {
        "name": "Stazione Meteorologica - off",
        "variables": ""
    },
    "radar_off": {
        "name": "Radar Meteorologico",
        "variables": "Precipitation"
    },
    "tidegauge_off": {
        "name": "Mareografo",
        "variables": "SeaLevel"
    },
    "wavebuoy_off": {
        "name": "Ondametro",
        "variables": ""
    },
    "mooring_off": {
        "name": "Mooring",
        "variables": ""
    },
    "owbuoy_off": {
        "name": "Boa Meteo-Oceanografica",
        "variables": ""
    },
    "hf_off": {
        "name": "HF Radar",
        "variables": ""
    },
    "glider_off": {
        "name": "Glider",
        "variables": "Temp, Salt, Depth, Turbidity, Oxygen, Nitrates"
    }
}


inluxdb_url = os.getenv("INFLUXDB_URL")
token = os.getenv("INFLUXDB_TOKEN")
org = os.getenv("INFLUXDB_ORG")
bucket = os.getenv("INFLUXDB_BUCKET")


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def handle_file_upload(file):
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return filename
    return None


def create_or_update_instrument(data, is_edit=False):
    instrument_id = data.get('id')
    name = data.get('name')
    airlinkID = data.get('airlinkID')
    organization = data.get('organization')
    installation_date = datetime.strptime(data.get('installation_date'), '%Y-%m-%d')
    latitude = float(data.get('latitude'))
    longitude = float(data.get('longitude'))
    instrument_type = data.get('instrument_type')

    variables = instrument_types.get(instrument_type, {}).get("variables", "")

    image = handle_file_upload(data.get('image'))

    if is_edit:
        instrument = Instrument.query.get(instrument_id)
        if not instrument:
            return None
        instrument.airlinkID = airlinkID
        instrument.name = name
        instrument.organization = organization
        instrument.installation_date = installation_date
        instrument.latitude = latitude
        instrument.longitude = longitude
        instrument.variables = variables
        instrument.instrument_type = instrument_type
        if image:
            instrument.image = image
    else:
        instrument = Instrument(
            id=instrument_id,
            name=name,
            airlinkID=airlinkID,
            image=image,
            organization=organization,
            installation_date=installation_date,
            latitude=latitude,
            longitude=longitude,
            variables=variables,
            instrument_type=instrument_type
        )
        db.session.add(instrument)

    return instrument


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
    return render_template('index.html')


@app.route('/get_airlink/<string:instrument_id>', methods=['GET'])
def get_airlink(instrument_id):
    airlinkID = Instrument.get_airlinkID_by_id(instrument_id)
    if airlinkID:
        return jsonify({"airlinkID": airlinkID}), 200
    else:
        return jsonify({"error": "Strumento non trovato"}), 404


@app.route('/instruments', methods=['GET', 'POST'])
def get_instruments():
    client = InfluxDBClient(url=inluxdb_url, token=token, org=org)
    query_api = client.query_api()

    if request.method == 'POST':
        query = f"""from(bucket: "{bucket}") |> range(start: -3h) |> last() |> distinct(column: "topic")"""
        tables = query_api.query(query, org=org)

        unique_topics = {record.values.get("topic") for table in tables for record in table.records if record.values.get("topic")}

        imported_count = 0
        for topic in unique_topics:
            if not Instrument.query.filter_by(id=topic).first():
                data = {
                    'id': topic,
                    'name': '',
                    'airlinkID': None,
                    'organization': "",
                    'installation_date': datetime.now().strftime('%Y-%m-%d'),
                    'latitude': 0.0,
                    'longitude': 0.0,
                    'instrument_type': "",
                    'image': None
                }

                if create_or_update_instrument(data):
                    imported_count += 1

        db.session.commit()
        return jsonify({'count': imported_count})

    query = f"""from(bucket: "{bucket}") |> range(start: -3h) |> last()"""
    tables = query_api.query(query, org=org)

    instruments = Instrument.query.all()
    instruments_data = []
    for instrument in instruments:
        relevant_variables = instrument.variables.split(", ") if instrument.variables else []

        instrument_data = {
            'id': instrument.id,
            'name': instrument.name,
            'latitude': instrument.latitude,
            'longitude': instrument.longitude,
            'type': instrument.instrument_type,
            'organization': instrument.organization,
            'image': f'static/uploads/{instrument.image}' if instrument.image else None
        }

        influx_data = {}
        for table in tables:
            for record in table.records:
                if record.values.get("topic") == instrument.id:
                    if record.get_field() in relevant_variables:
                        influx_data[record.get_field()] = record.get_value()

        instrument_data['variables'] = influx_data
        if 'TempOut' in instrument_data['variables']:
            instrument_data['variables']['TempOut'] = utils.convert_f_to_c(instrument_data['variables']['TempOut'])

        instruments_data.append(instrument_data)

    return jsonify(instruments_data)


@app.route('/timeseries/<string:instrument_id>', methods=['GET'])
@login_required
def timeseries(instrument_id):
    client = InfluxDBClient(url=inluxdb_url, token=token, org=org)
    query_api = client.query_api()

    start_time = request.args.get('start', None)
    end_time = request.args.get('end', None)

    if not start_time:
        start_time = int(time.time()) - 10800
    if not end_time:
        end_time = int(time.time())

    start_time_iso = datetime.utcfromtimestamp(int(start_time)).isoformat() + "Z"
    end_time_iso = datetime.utcfromtimestamp(int(end_time)).isoformat() + "Z"

    query = f"""
    from(bucket: "{bucket}")
    |> range(start: {start_time_iso}, stop: {end_time_iso})
    |> filter(fn: (r) => r["topic"] == "{instrument_id}")
    """
    tables = query_api.query(query, org=org)

    influx_data = {}
    for table in tables:
        for record in table.records:
            field = record.get_field()
            if field not in influx_data:
                influx_data[field] = []

            influx_data[field].append({
                "time": record.get_time().isoformat(),
                "value": record.get_value()
            })

    csv_output = StringIO()
    writer = csv.writer(csv_output)

    all_variables = list(influx_data.keys())
    headers = ["time"] + all_variables
    writer.writerow(headers)

    time_indexed_data = {}

    for variable, records in influx_data.items():
        for record in records:
            time_value = record["time"]
            if time_value not in time_indexed_data:
                time_indexed_data[time_value] = {var: "" for var in all_variables}
            time_indexed_data[time_value][variable] = record["value"]

    for time_value, values in sorted(time_indexed_data.items()):
        row = [time_value] + [values[var] for var in all_variables]
        writer.writerow(row)

    csv_output.seek(0)
    return Response(csv_output, mimetype="text/csv", headers={"Content-Disposition": f"attachment;filename={instrument_id}_timeseries.csv"})


@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin():
    if request.method == 'POST':
        data = {
            'id': request.form.get('id'),
            'name': request.form.get('name'),
            'airlinkID': request.form.get('airlinkID'),
            'organization': request.form.get('organization'),
            'installation_date': request.form.get('installation_date'),
            'latitude': request.form.get('latitude'),
            'longitude': request.form.get('longitude'),
            'instrument_type': request.form.get('instrument_type'),
            'image': request.files.get('image')
        }

        if create_or_update_instrument(data):
            db.session.commit()
        else:
            db.session.rollback()

        return redirect(url_for('admin'))

    instruments = Instrument.query.all()
    return render_template('admin.html', instruments=instruments, instrument_types=instrument_types)


@app.route('/edit/<instrument_id>', methods=['POST'])
@login_required
def edit_instrument(instrument_id):
    data = {
        'id': request.form.get('id'),
        'name': request.form.get('name'),
        'airlinkID': request.form.get('airlinkID'),
        'organization': request.form.get('organization'),
        'installation_date': request.form.get('installation_date'),
        'latitude': request.form.get('latitude'),
        'longitude': request.form.get('longitude'),
        'instrument_type': request.form.get('instrument_type'),
        'image': request.files.get('image')
    }

    if create_or_update_instrument(data, is_edit=True):
        db.session.commit()
    else:
        db.session.rollback()

    return redirect(url_for('admin'))


@app.route('/delete/<instrument_id>', methods=['POST', 'GET'])
@login_required
def delete_instrument(instrument_id):
    instrument = Instrument.query.get(instrument_id)
    if instrument:
        db.session.delete(instrument)
        db.session.commit()
    return redirect(url_for('admin'))


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=8088)
