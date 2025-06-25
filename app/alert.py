import time
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from influxdb_client import InfluxDBClient
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

load_dotenv()

# Load environment variables
url = os.getenv("INFLUXDB_URL")
token = os.getenv("INFLUXDB_TOKEN")
org = os.getenv("INFLUXDB_ORG")
bucket = os.getenv("INFLUXDB_BUCKET")
db_url = os.getenv('DATABASE_URL')

# SMTP Configuration
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = os.getenv("SMTP_PORT")
#SMTP_USERNAME = os.getenv("SMTP_USERNAME")
#SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
EMAIL_FROM = os.getenv("EMAIL_FROM")
EMAIL_TO = os.getenv("EMAIL_TO")
if EMAIL_TO:
    EMAIL_TO = EMAIL_TO.split(",")

# Postgres engine
engine = create_engine(db_url)

# InfluxDB client
client = InfluxDBClient(url=url, token=token, org=org)
query_api = client.query_api()


def check_station_status():
    with engine.connect() as connection:
        results = connection.execute(text("SELECT id, name, status FROM instruments"))
        instruments = [{"id": row[0], "name": row[1], "status": row[2]} for row in results]

        current_time = datetime.utcnow()

        for instrument in instruments:
            id = instrument["id"]
            name = instrument["name"]
            prev_status = instrument["status"]
            
            query = f"""from(bucket: "{bucket}") 
                        |> range(start: -30m) 
                        |> filter(fn: (r) => r._field == "TempOut" and r.topic == "{id}") 
                        |> last()"""
            tables = query_api.query(query)

            last_message_time = None
            for table in tables:
                for record in table.records:
                    last_message_time = record.get_time()

            if last_message_time:
                last_message_time = last_message_time.replace(tzinfo=None)
                time_difference = current_time - last_message_time
                current_status = "offline" if time_difference > timedelta(minutes=10) else "online"
            else:
                current_status = "offline"

            if current_status != prev_status:
                send_alert(id, current_status, name)
                update_query = text("UPDATE instruments SET status = :status WHERE id = :id")
                connection.execute(update_query, {"status": current_status, "id": id})

        connection.commit()


def send_alert(station_id, status, station_name):
    subject = f"ALERT: Station {station_name} ({station_id}) is now {status.upper()}"
    body = f"The station '{station_name}' (ID {station_id}) has changed status to {status.upper()}."

    send_email(subject, body)

    print(f"ALERT: Station {station_name} ({station_id}) is now {status}")


def send_email(subject, body):
    msg = MIMEMultipart()
    msg['From'] = EMAIL_FROM
    msg['To'] = ", ".join(EMAIL_TO) if isinstance(EMAIL_TO, list) else EMAIL_TO
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            #server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())

        print(f"Email sent to {EMAIL_TO} with subject: {subject}")
    except Exception as e:
        print(f"Failed to send email: {e}")


while True:
    check_station_status()
    time.sleep(60)
