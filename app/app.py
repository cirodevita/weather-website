import os
from dotenv import load_dotenv
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, request, jsonify
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_migrate import Migrate
from models import db, User, Instrument
from flask_bcrypt import Bcrypt
from werkzeug.utils import secure_filename
from sqlalchemy.exc import IntegrityError
from influxdb_client import InfluxDBClient

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
    }
}


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


@app.route('/instruments', methods=['GET', 'POST'])
def get_instruments():
    url = os.getenv("INFLUXDB_URL")
    token = os.getenv("INFLUXDB_TOKEN")
    org = os.getenv("INFLUXDB_ORG")
    bucket = os.getenv("INFLUXDB_BUCKET")

    client = InfluxDBClient(url=url, token=token, org=org)
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
        instruments_data.append(instrument_data)

    return jsonify(instruments_data)


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


@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin():
    if request.method == 'POST':
        data = {
            'id': request.form.get('id'),
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
