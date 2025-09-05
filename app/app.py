
'''
TODO: 
- Use CSRF Protection for POST/PUT/DELETE
- Reimplement instrument delete/edit APIs
'''

from io import StringIO
from dotenv import load_dotenv
from datetime import timedelta, datetime
from flask import Flask, render_template, redirect, url_for, request, jsonify, Response, abort
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
import pandas as pd

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

airlink_variables = "pm_2p5_nowcast, pm_1, pm_10_nowcast, aqi_nowcast_val"

inluxdb_url = os.getenv("INFLUXDB_URL")
token = os.getenv("INFLUXDB_TOKEN")
org = os.getenv("INFLUXDB_ORG")
bucket = os.getenv("INFLUXDB_BUCKET")


def admin_required(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)
        if current_user.username != 'admin':
            abort(403)
        return f(*args, **kwargs)
    return wrapper

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
    if airlinkID != "":
        variables += airlink_variables
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

@app.route('/users', methods=['GET'])
@login_required
def users_page():
    """Se admin: mostra gestione utenti. Se non admin: mostra pagina cambio password."""
    if current_user.username == 'admin':
        users = User.query.order_by(User.username.asc()).all()
        return render_template('users_admin.html', users=users)
    else:
        return render_template('users_profile.html')

@app.route('/api/users', methods=['POST'])
@login_required
@admin_required
def api_create_user():
    data = request.get_json(silent=True) or request.form
    username = (data.get('username') or '').strip()
    password = (data.get('password') or '').strip()

    if not username or not password:
        return jsonify({"error": "Username e password sono obbligatori."}), 400
    if username.lower() == 'admin':
        pass

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username già esistente."}), 409

    user = User(username=username)
    user.set_password(password)

    try:
        db.session.add(user)
        db.session.commit()
        return jsonify({"message": "User creato", "id": user.id, "username": user.username}), 201
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Username già esistente."}), 409
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Errore inatteso."}), 500

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@login_required
@admin_required
def api_delete_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "Utente non trovato."}), 404
    if user.username == 'admin':
        return jsonify({"error": "Non puoi cancellare l'utente admin."}), 400
    if user.id == current_user.id:
        return jsonify({"error": "Non puoi cancellare il tuo stesso account."}), 400

    try:
        db.session.delete(user)
        db.session.commit()
        return jsonify({"message": "Utente eliminato."}), 200
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Errore inatteso."}), 500

@app.route('/api/users/change_password', methods=['POST'])
@login_required
def api_change_password():
    """
    Cambia la password dell'utente corrente.
    Richiede: current_password, new_password, confirm_password
    """
    data = request.get_json(silent=True) or request.form
    current_password = (data.get('current_password') or '').strip()
    new_password = (data.get('new_password') or '').strip()
    confirm_password = (data.get('confirm_password') or '').strip()

    if not current_password or not new_password or not confirm_password:
        return jsonify({"error": "Tutti i campi sono obbligatori."}), 400
    if new_password != confirm_password:
        return jsonify({"error": "Le nuove password non coincidono."}), 400
    if len(new_password) < 6:
        return jsonify({"error": "La nuova password deve avere almeno 6 caratteri."}), 400

    if not current_user.check_password(current_password):
        return jsonify({"error": "Password attuale non corretta."}), 400

    try:
        current_user.set_password(new_password)
        db.session.commit()
        return jsonify({"message": "Password aggiornata con successo."}), 200
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Errore inatteso nell'aggiornamento."}), 500


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
            'airlinkID': instrument.airlinkID,
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


@app.route('/dashboard', methods=['GET'])
@login_required
def dashboard():
    instruments = Instrument.query.all()
    return render_template('dashboard.html', instruments=instruments, instrument_types=instrument_types)


@app.route('/api/instruments', methods=['POST'])
@login_required
def api_create_instrument():
    # Supporta sia JSON che form-data
    is_json = request.is_json
    src = request.get_json(silent=True) if is_json else request.form

    # Estrai campi con default coerenti al tuo schema
    data = {
        'id': (src.get('id') if src else None),
        'name': (src.get('name') if src else None) or '',
        'airlinkID': (src.get('airlinkID') if src else None),
        'organization': (src.get('organization') if src else None) or '',
        'installation_date': (src.get('installation_date') if src else None) or datetime.utcnow().strftime('%Y-%m-%d'),
        'latitude': (src.get('latitude') if src else None) or 0.0,
        'longitude': (src.get('longitude') if src else None) or 0.0,
        'instrument_type': (src.get('instrument_type') if src else None) or '',
        'image': (request.files.get('image') if not is_json else None)
    }

    # Validazione minima
    missing = [k for k in ('id', 'instrument_type') if not data.get(k)]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400

    # Parsing sicuro dei tipi
    try:
        # installation_date è 'YYYY-MM-DD' nella tua create_or_update_instrument
        datetime.strptime(data['installation_date'], '%Y-%m-%d')
        data['latitude'] = float(data['latitude'])
        data['longitude'] = float(data['longitude'])
    except ValueError:
        return jsonify({"error": "Invalid date or coordinates format."}), 400

    try:
        inst = create_or_update_instrument(data, is_edit=False)
        if not inst:
            # create_or_update_instrument ritorna None se fallisce su lookup in edit,
            # qui non dovrebbe capitare, ma gestiamo comunque
            db.session.rollback()
            return jsonify({"error": "Could not create instrument."}), 400

        db.session.commit()

        # Risposta JSON coerente con quello che già usi altrove
        return jsonify({
            "id": inst.id,
            "name": inst.name,
            "airlinkID": inst.airlinkID,
            "latitude": inst.latitude,
            "longitude": inst.longitude,
            "instrument_type": inst.instrument_type,
            "organization": inst.organization,
            "image": f'static/uploads/{inst.image}' if inst.image else None,
            "variables": inst.variables
        }), 201

    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Instrument with this id (or unique field) already exists."}), 409
    except Exception as e:
        db.session.rollback()
        # Non leakare dettagli in prod, ma utile in dev:
        return jsonify({"error": "Unexpected error creating instrument."}), 500


@app.route('/api/instruments/<string:instrument_id>', methods=['PATCH', 'PUT', 'DELETE'])
@login_required
def api_instrument_detail(instrument_id):
    inst = Instrument.query.get(instrument_id)
    if not inst:
        return jsonify({"error": "Instrument not found"}), 404

    if request.method in ('PATCH', 'PUT'):
        is_json = request.is_json
        src = request.get_json(silent=True) if is_json else request.form

        # Costruisci solo i campi presenti (qui non usiamo create_or_update_instrument per non forzare tutti i campi)
        if 'name' in src: inst.name = src['name']
        if 'airlinkID' in src: inst.airlinkID = src['airlinkID'] or None
        if 'organization' in src: inst.organization = src['organization'] or ''
        if 'installation_date' in src:
            try:
                inst.installation_date = datetime.strptime(src['installation_date'], '%Y-%m-%d')
            except ValueError:
                return jsonify({"error": "Invalid installation_date"}), 400
        if 'latitude' in src:
            try: inst.latitude = float(src['latitude'])
            except ValueError: return jsonify({"error": "Invalid latitude"}), 400
        if 'longitude' in src:
            try: inst.longitude = float(src['longitude'])
            except ValueError: return jsonify({"error": "Invalid longitude"}), 400
        if 'instrument_type' in src: inst.instrument_type = src['instrument_type'] or ''
        # Immagine via multipart
        if not is_json and 'image' in request.files and request.files['image']:
            file = request.files['image']
            filename = handle_file_upload(file)
            if filename:
                inst.image = filename

        try:
            db.session.commit()
            return jsonify({"message": "Updated", "id": inst.id}), 200
        except IntegrityError:
            db.session.rollback()
            return jsonify({"error": "Unique constraint violation"}), 409

    if request.method == 'DELETE':
        db.session.delete(inst)
        db.session.commit()
        return jsonify({"message": "Deleted"}), 200

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

    return redirect(url_for('dashboard'))


@app.route('/delete/<instrument_id>', methods=['POST', 'GET'])
@login_required
def delete_instrument(instrument_id):
    instrument = Instrument.query.get(instrument_id)
    if instrument:
        db.session.delete(instrument)
        db.session.commit()
    return redirect(url_for('dashboard'))


@app.route("/upload_influx", methods=["POST"])
@login_required
def upload_influx():
    file = request.files.get("file")
    topic_value = request.form.get("topic") or request.args.get("topic")
    if not file:
        return jsonify({"error": "No file uploaded"}), 400
    if not topic_value:
        return jsonify({"error": "Missing 'topic' parameter."}), 400
    
    df = pd.read_csv(file)
    if "Datetime" not in df.columns:
        return jsonify({"error": "Missing 'Datetime' column in the uploaded file."}), 400
    
    influx_client = InfluxDBClient(url=inluxdb_url, token=token, org=org)
    write_api = influx_client.write_api()
    query_api = influx_client.query_api()

    inserted_count = 0
    for _, row in df.iterrows():
        datetime_value = row["Datetime"]
        t0 = datetime.fromisoformat(datetime_value.replace("Z", "+00:00"))
        start_range = (t0 - timedelta(seconds=1)).isoformat().replace("+00:00", "Z")
        end_range = (t0 + timedelta(seconds=1)).isoformat().replace("+00:00", "Z")

        query = f'''
        from(bucket: "{bucket}") 
        |> range(start: {start_range}, stop: {end_range})
        |> filter(fn: (r) => r._measurement == "mqtt_data") 
        |> filter(fn: (r) => r["topic"] == "{topic_value}")
        '''
        tables = query_api.query(query, org=org)

        exists = any(
            record.get_field() == "Datetime" and record.get_value() == datetime_value
            for table in tables
            for record in table.records
        )

        if exists:
            continue
        
        fields = {
            key: value
            for key, value in row.items()
            if isinstance(value, (int, float, str))
        }
        point = {
                "measurement": "mqtt_data",
                "tags": {"topic": topic_value},
                "fields": fields,
                "time": datetime_value
        }
        write_api.write(bucket=bucket, org=org, record=point)
        inserted_count += 1
    
    return jsonify({"inserted_count": inserted_count}), 200


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=8088)
