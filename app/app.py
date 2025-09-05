"""
Application: Meteo/Oceanographic Instruments Dashboard API
Author: Gennaro Mellone, Ciro Giuseppe De Vita

Overview
--------
Flask app that manages users and instruments and exposes:
- Session-based authentication (Flask-Login + bcrypt).
- Admin/user pages: dashboard, users (admin panel) or self-service password change.
- Instrument CRUD (mix of HTML forms and JSON APIs).
- InfluxDB queries to fetch/aggregate time series and export CSV.
- File upload to backfill InfluxDB from CSV.

Security (current & TODO)
-------------------------
- Uses SECRET_KEY, bcrypt, and login-required routes where needed.
- TODO (recommended): enable CSRF protection on POST/PUT/DELETE, harden cookies,
  rate-limit login, and convert destructive GETs to POST (some already done).

Configuration (env)
-------------------
- SECRET_KEY, DATABASE_URL, UPLOAD_FOLDER, ALLOWED_EXTENSIONS
- INFLUXDB_URL, INFLUXDB_TOKEN, INFLUXDB_ORG, INFLUXDB_BUCKET

Key Endpoints
-------------
- GET  /dashboard                      : instruments table (HTML)
- GET  /users                          : admin list or user profile (HTML)
- POST /api/users                      : create user (admin)
- DELETE /api/users/<id>               : delete user (admin)
- POST /api/users/change_password      : change current user's password
- GET/POST /instruments                : list or import instruments from Influx topics
- GET  /timeseries/<instrument_id>     : export CSV for selected time window/interval
- POST /api/instruments                : create instrument
- PATCH/PUT/DELETE /api/instruments/<id>: update/delete instrument
- POST /edit/<id>                      : update instrument via form
- POST /delete/<id>                    : delete instrument (HTML flow)
- POST /upload_influx                  : backfill InfluxDB with CSV rows

Notes
-----
- The variables list for each instrument influences which fields are favored in CSV headers.
- The time series export uses Flux aggregateWindow with fn=last to preserve non-numeric fields.
- Keep models/schema intact per your requirement; comments focus on structure and usage.
"""

from io import StringIO
from dotenv import load_dotenv
from datetime import timedelta, datetime
from dateutil import parser as dateparser
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

from config.constants import INSTRUMENT_TYPES, variables_for

# Load environment configuration
load_dotenv()

app = Flask(__name__)

# Core configuration (secrets, DB, uploads, formats)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER')
app.config['ALLOWED_EXTENSIONS'] = set(os.getenv('ALLOWED_EXTENSIONS').split(','))

# Initialize extensions (DB, password hashing, migrations, session manager)
db.init_app(app)
bcrypt = Bcrypt(app)
migrate = Migrate(app, db)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Static catalog that maps instrument type keys to labels and variable hints
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

# Additional variables automatically appended for airlink devices
airlink_variables = "pm_2p5_nowcast, pm_1, pm_10_nowcast, aqi_nowcast_val"

# InfluxDB connection parameters
inluxdb_url = os.getenv("INFLUXDB_URL")
token = os.getenv("INFLUXDB_TOKEN")
org = os.getenv("INFLUXDB_ORG")
bucket = os.getenv("INFLUXDB_BUCKET")


# Simple admin guard: only "admin" username is treated as administrator
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

# Basic file-type allowlist for uploads (by extension)
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


# Session user loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Save uploaded image into configured upload folder (if any)
def handle_file_upload(file):
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return filename
    return None


# Shared helper to create or update Instrument from form/JSON data
def create_or_update_instrument(data, is_edit=False):
    instrument_id = data.get('id')
    name = data.get('name')
    airlinkID = data.get('airlinkID')
    organization = data.get('organization')
    installation_date = datetime.strptime(data.get('installation_date'), '%Y-%m-%d')
    latitude = float(data.get('latitude'))
    longitude = float(data.get('longitude'))
    instrument_type = data.get('instrument_type')

    # Build variables list from type catalog and append airlink fields if present
    variables = variables_for(instrument_type, bool(airlinkID))

    image = handle_file_upload(data.get('image'))

    if is_edit:
        instrument = Instrument.query.get(instrument_id)
        if not instrument:
            return None
        # Update fields in place (image only if uploaded)
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
        # Create new instrument and add to session
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


# Public home page (e.g., login form view)
@app.route('/')
def index():
    return render_template('index.html')


# Username/password login with bcrypt verification and session creation
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # NOTE: consider CSRF protection and rate limiting for brute-force defense
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
    return render_template('index.html')


# Users page: admin sees full management; non-admin sees self-service password change
@app.route('/users', methods=['GET'])
@login_required
def users_page():
    """If admin, render admin user list; otherwise show profile/password form."""
    if current_user.username == 'admin':
        users = User.query.order_by(User.username.asc()).all()
        return render_template('users_admin.html', users=users)
    else:
        return render_template('users_profile.html')


# Admin-only: create a new user (accepts JSON or form-data)
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
        pass  # no special handling here beyond uniqueness

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


# Admin-only: delete a user, with safeguards for admin/self-delete
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


# Logged-in user: change own password (validates current + basic policy)
@app.route('/api/users/change_password', methods=['POST'])
@login_required
def api_change_password():
    """
    Change password for current user.
    Accepts: current_password, new_password, confirm_password (form or JSON).
    """
    data = request.get_json(silent=True) or request.form
    current_password = (data.get('current_password') or '').strip()
    new_password = (data.get('new_password') or '').strip()
    confirm_password = (data.get('confirm_password') or '').strip()

    # Minimal validation; extend with stronger policy if needed
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


# Utility API to fetch AirLink ID by instrument id
@app.route('/get_airlink/<string:instrument_id>', methods=['GET'])
def get_airlink(instrument_id):
    airlinkID = Instrument.get_airlinkID_by_id(instrument_id)
    if airlinkID:
        return jsonify({"airlinkID": airlinkID}), 200
    else:
        return jsonify({"error": "Strumento non trovato"}), 404


# Instruments API:
# - POST: import new instruments discovered in Influx (distinct topics)
# - GET : list instruments enriched with latest Influx values for relevant variables
@app.route('/instruments', methods=['GET', 'POST'])
def get_instruments():
    client = InfluxDBClient(url=inluxdb_url, token=token, org=org)
    query_api = client.query_api()

    if request.method == 'POST':
        # Discover unique topics seen in the last 3 hours and create instruments for missing ones
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

    # For listing, collect last values per topic and attach to instruments
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

        # Example conversion: Fahrenheit to Celsius for TempOut
        instrument_data['variables'] = influx_data
        if 'TempOut' in instrument_data['variables']:
            instrument_data['variables']['TempOut'] = utils.convert_f_to_c(instrument_data['variables']['TempOut'])

        instruments_data.append(instrument_data)

    return jsonify(instruments_data)


# CSV export of time series for a given instrument id, with windowed aggregation
@app.route('/timeseries/<string:instrument_id>', methods=['GET'])
@login_required
def timeseries(instrument_id):
    client = InfluxDBClient(url=inluxdb_url, token=token, org=org)
    query_api = client.query_api()

    # Read time range and sampling interval (supports ISO or epoch seconds)
    start_arg = request.args.get('start')
    end_arg = request.args.get('end')
    interval = request.args.get('interval', '10')
    try:
        interval = int(interval)
    except ValueError:
        interval = 10
    if interval not in (10, 20, 30):
        interval = 10
    every = f"{interval}m"

    # Helper to parse flexible time inputs
    def parse_time(val, default_ts):
        if not val:
            return datetime.utcfromtimestamp(default_ts)
        if isinstance(val, str) and val.isdigit():
            return datetime.utcfromtimestamp(int(val))
        return dateparser.parse(val)

    now_ts = int(time.time())
    start_dt = parse_time(start_arg, now_ts - 10800)  # default last 3 hours
    end_dt = parse_time(end_arg, now_ts)

    # Build time bounds as UTC Zulu
    start_iso = start_dt.replace(tzinfo=None).isoformat() + "Z"
    end_iso = end_dt.replace(tzinfo=None).isoformat() + "Z"

    # Use instrument.variables as favored columns for header order
    instrument = Instrument.query.get(instrument_id)
    if not instrument:
        return jsonify({"error": "Instrument not found"}), 404

    expected = []
    if instrument.variables:
        expected = [v.strip() for v in instrument.variables.replace(";", ",").split(",") if v.strip()]
    expected_set = set(expected)

    # Flux query: windowed last value per field, pivot to one row per timestamp
    query = f'''
from(bucket: "{bucket}")
  |> range(start: {start_iso}, stop: {end_iso})
  |> filter(fn: (r) => r["topic"] == "{instrument_id}")
  |> filter(fn: (r) => r._measurement == "mqtt_data")
  |> aggregateWindow(every: {every}, fn: last, createEmpty: true)
  |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
  |> sort(columns: ["_time"])
'''
    tables = query_api.query(query, org=org)

    # Collect rows and discover all columns dynamically
    rows = []
    found_cols = set()
    for table in tables:
        for rec in table.records:
            vals = dict(rec.values)
            clean = {}
            for k, v in vals.items():
                if k == "_time":
                    clean["_time"] = v
                elif not k.startswith("_") and k not in ("result", "table", "topic", "_measurement", "_start", "_stop"):
                    clean[k] = v
            rows.append(clean)
            found_cols.update([c for c in clean.keys() if c != "_time"])

    # Header: "time" plus expected (stable order) and any extra discovered fields
    header_fields = list(expected)
    extras = sorted(list(found_cols - expected_set))
    all_fields = header_fields + extras
    if not all_fields:
        all_fields = sorted(list(found_cols))

    # Stream CSV to client
    out = StringIO()
    w = csv.writer(out)
    w.writerow(["time"] + all_fields)

    def row_time_key(r):
        t = r.get("_time")
        try:
            return dateparser.parse(t) if isinstance(t, str) else t
        except Exception:
            return t

    for r in sorted(rows, key=row_time_key):
        t = r.get("_time")
        t_str = t.isoformat() if isinstance(t, datetime) else (t or "")
        row = [t_str] + [r.get(col, "") for col in all_fields]
        w.writerow(row)

    out.seek(0)
    fname = f"{instrument_id}_timeseries_{interval}m.csv"
    return Response(out, mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment;filename={fname}"})


# Dashboard view (HTML) – server-side provides instruments list; client JS enhances UI
@app.route('/dashboard', methods=['GET'])
@login_required
def dashboard():
    instruments = Instrument.query.all()
    return render_template('dashboard.html', instruments=instruments, instrument_types=INSTRUMENT_TYPES)


# JSON API to create instruments (accepts JSON or multipart form to include image)
@app.route('/api/instruments', methods=['POST'])
@login_required
def api_create_instrument():
    is_json = request.is_json
    src = request.get_json(silent=True) if is_json else request.form

    # Normalize incoming data to expected types/defaults
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

    # Minimal validation
    missing = [k for k in ('id', 'instrument_type') if not data.get(k)]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400

    try:
        datetime.strptime(data['installation_date'], '%Y-%m-%d')
        data['latitude'] = float(data['latitude'])
        data['longitude'] = float(data['longitude'])
    except ValueError:
        return jsonify({"error": "Invalid date or coordinates format."}), 400

    try:
        inst = create_or_update_instrument(data, is_edit=False)
        if not inst:
            db.session.rollback()
            return jsonify({"error": "Could not create instrument."}), 400

        db.session.commit()

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
        return jsonify({"error": "Unexpected error creating instrument."}), 500


# JSON API to update/delete instruments without altering DB schema
@app.route('/api/instruments/<string:instrument_id>', methods=['PATCH', 'PUT', 'DELETE'])
@login_required
def api_instrument_detail(instrument_id):
    inst = Instrument.query.get(instrument_id)
    if not inst:
        return jsonify({"error": "Instrument not found"}), 404

    if request.method in ('PATCH', 'PUT'):
        is_json = request.is_json
        src = request.get_json(silent=True) if is_json else request.form

        # Partial update: apply only provided fields; accept image via multipart
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


# HTML form-based edit route (kept for current UI modal flow)
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


# Delete route used by the HTML button (recommend making it POST-only with CSRF)
@app.route('/delete/<instrument_id>', methods=['POST', 'GET'])
@login_required
def delete_instrument(instrument_id):
    instrument = Instrument.query.get(instrument_id)
    if instrument:
        db.session.delete(instrument)
        db.session.commit()
    return redirect(url_for('dashboard'))


# CSV upload to InfluxDB to backfill measurement points for a specific topic
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

    # For each row, check for an existing point around the timestamp, then insert if new
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
        
        # Accept numeric and string fields only; write point with timestamp
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


# Logout route to clear session and return to homepage
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


# App entry point: ensure DB tables exist and start development server
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=8088)
