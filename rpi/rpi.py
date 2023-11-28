import base64
from flask import Flask, render_template, request, Response, send_from_directory
import paho.mqtt.client as mqtt
from flask_sqlalchemy import SQLAlchemy
from connected_devices import get_connected_devices, check_registered_devices
from werkzeug.security import generate_password_hash, check_password_hash
import os
import yaml
import json
import logging
from datetime import datetime
import asyncio
import requests

from MQTT_Client import init_mqttc

# initializations

global config, secrets
with open('config.yml', 'r') as config_file:
    global config
    config = yaml.safe_load(config_file)

logging.basicConfig(filename='logs/rpi.csv', format='%(asctime)s.%(msecs)03d,%(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S', filemode='w+')
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# mqtt client
# mqtt_client = init_mqttc()
client = mqtt.Client()

# flask
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///registry.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'secret_key'
app.config['UPLOAD_FOLDER'] = 'activity_vlogs'
db = SQLAlchemy(app)


# sqlite table initializations
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mac_address = db.Column(db.String(17), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)


class Device(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mac_address = db.Column(db.String(17), unique=True, nullable=False)
    uri = db.Column(db.String(255), nullable=False)


class ActivityLog(db.Model):
    id = db.Column(db.String(64), primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False)
    # detection_results: 0 = pending, -1 = False (Negative), +1 = True (Positive)
    detection_result = db.Column(db.Integer, nullable=False)
    suppressor_name = db.Column(db.String(32), nullable=True)


# Create tables
with app.app_context():
    db.create_all()


# helper functions

received_data = {
    "alert_id": None,
    "video_url": None,
    "intrusion_result": None
}

def on_message(client, userdata, message):
    msg_payload = str(message.payload.decode("utf-8"))
    message_parts = msg_payload.split(',')
    print("Video URL :", message_parts[1])
    global received_data
    received_data["alert_id"] = message_parts[0]
    received_data["video_url"] = message_parts[1]
    received_data["intrusion_result"] = message_parts[2]
    # Redirect to a Flask route to render the template with the data
    redirect_to_render()

def redirect_to_render():
    # Perform a redirect to a Flask route where the template will be rendered
    # You'll need to create a route in your Flask app to render the template with the received data
    pass  # Placeholder for redirecting logic


def send_response_to_rpi( choice, person_name):
    rpi_endpoint = "http://rpi_ip_address:port/receive_response"
    data = {'choice': choice, 'person_name': person_name}

    try:
        response = requests.post(rpi_endpoint, json=data)
        if response.status_code == 200:
            print("Response sent to RPi successfully")
        else:
            print("Failed to send response to RPi. Status code:", response.status_code)
    except requests.exceptions.RequestException as e:
        print("Error sending request to RPi:", e)


def send_email(subject, body):
    return requests.post(url=config['cloud_endpoint'] + "send-email", json={"subject": subject, "body": body})


def save_video(video, timestamp, device_name):
    # Generate activity_id
    activity_id = f'{datetime.now().strftime("%Y%m%d_%H%M%S")}-{device_name}'
    logger.debug(f'{device_name},{activity_id},video_size:{len(video)}')

    # Create the directory if it doesn't exist
    os.makedirs(app.config['VLOGS_SAVE_FOLDER'], exist_ok=True)

    # Decode base64 and save video as a binary file
    video_data = base64.b64decode(video)
    filename = f"{timestamp}-{device_name}.mp4"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    with open(filepath, 'wb') as file:
        file.write(video_data)

    new_activity_log = ActivityLog(id=activity_id, timestamp=timestamp, detection_result=0)
    db.session.add(new_activity_log)
    db.session.commit()

    return activity_id

async def intrusion_detection(payload: dict):
    # TODO: Wifi-based detection
    wifi_check = 0.0

    connected_devices = get_connected_devices()
    check_registered_devices(connected_devices)
    if(connected_devices.alarm_triggered) :
        wifi_check = 1.0

    # TODO: ML-based face/posture detection
    face_check = 1.0  # UPDATE THIS!

    # TODO: get weighted result and alert user
    detection_result = (0.75 * wifi_check) + (0.25 * face_check)  # UPDATE THIS!

    logger.debug(f'{payload["activity_id"]},detection_result:{detection_result}')

    # save detection result to db
    activity_log = ActivityLog.query.filter_by(id=payload["activity_id"]).first()
    activity_log.detection_result = detection_result
    db.session.commit()
    activity_id = payload["activity_id"]
    if detection_result > 0.75:
        # publish detection result to user
        client.publish(topic="test_topic", payload=payload, qos=2, retain=True)
        send_email("Site Activity Alert",
                   f"Possible intrusion detected at your site. {activity_id} at {activity_log.timestamp} with {activity_log.detection_result} certainty.")

# config['topics']['rpi_to_user']

broker_address = "127.0.0.1"
topic = "test_topic"

client.on_message = on_message
client.connect(broker_address)
client.subscribe(topic)
client.loop_start()

# routes
@app.route('/process_choice', methods=['POST'])
def process_choice():
    choice = request.form['choice']
    person_name = request.form.get('person_name', '')
    alert_id = request.form.get('alert_id') # Get person's name from the form
    send_response_to_rpi( choice, person_name)
    # Send user choice and person's name to RPi
    print(choice, "chosen by : ", person_name)
    return f"Alert Id: {alert_id}. Choice sent to RPi: {choice}. Suppressed by: {person_name}"

@app.route('/video/<path:filename>')
def serve_video(filename):
    return send_from_directory('/Users/chetana/PycharmProjects/WID_IoT/', filename)

@app.route('/render_template_route')
def render_template_route():
    global received_data
    return render_template('index.html', alert_id=received_data["alert_id"],
                           video_url=received_data["video_url"],
                           intrusion_result=received_data["intrusion_result"])

@app.post('/activity-detected')
# handle POST from ESP32-CAM
# request body: {video: base64.b64encode, timestamp: str, device_name: str}
def activity_detected():
    data = request.json

    video = data.get('video')
    timestamp = data.get('timestamp')
    device_name = data.get('device_name')

    # Save the video to the 'activity_vlogs' directory
    activity_id = save_video(video, timestamp, device_name)

    # asynchronously perform intrusion detection and handle result
    asyncio.create_task(intrusion_detection(payload={
        "video": video,
        "timestamp": timestamp,
        "device_name": device_name,
        "activity_id": activity_id
    }))

    return Response(f"{activity_id}", 201)

@app.post('/suppress-alert')
# handle POST from user
# request body: {activity_id, suppress, suppressor_id}
def suppress_alert():
    data = request.json

    activity_id = data.get('activity_id')
    suppress = data.get('suppress')
    suppressor_name = data.get('suppressor_name')

    activity_log = ActivityLog.query.filter_by(id=activity_id).first()
    if suppress == 'true' or suppress == 'True' or suppress == True or suppress == 1:
        activity_log.suppressor_name = suppressor_name
        db.session.commit()

    if activity_log.detection_result > 0.75:
        send_email("Site Activity Alert",
                   f"Possible intrusion detected at your site. {activity_id} at {activity_log.timestamp} with {activity_log.detection_result} certainty.")

    return Response(f"{activity_id}", 201)


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=8080)