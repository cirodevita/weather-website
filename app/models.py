from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from flask_bcrypt import Bcrypt

db = SQLAlchemy()
bcrypt = Bcrypt()

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

    def set_password(self, password):
        """Hashes the password and stores it."""
        self.password = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        """Checks the hashed password."""
        return bcrypt.check_password_hash(self.password, password)


class Instrument(db.Model):
    __tablename__ = 'instruments'

    id = db.Column(db.String(50), primary_key=True, unique=True, nullable=False)
    image = db.Column(db.String(255), nullable=True)
    organization = db.Column(db.String(100), nullable=True)
    installation_date = db.Column(db.Date, nullable=True)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    variables = db.Column(db.String(255), nullable=False)
    instrument_type = db.Column(db.String(100), nullable=False)
    airlinkID = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String, default='offline')

    def __init__(self, id, airlinkID, image, organization, installation_date, latitude, longitude, variables, instrument_type):
        self.id = id
        self.airlinkID = airlinkID
        self.image = image
        self.organization = organization
        self.installation_date = installation_date
        self.latitude = latitude
        self.longitude = longitude
        self.variables = variables
        self.instrument_type = instrument_type

    @classmethod
    def get_airlinkID_by_id(cls, id):
        instrument = cls.query.filter_by(id=id).first()
        if instrument:
            return instrument.airlinkID
        return None

    @classmethod
    def get_variables_by_id(cls, id):
        instrument = cls.query.filter_by(id=id).first()
        if instrument:
            return instrument.variables
        return None