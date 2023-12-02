import base64
from flask import Flask, render_template, request, Response, send_file, jsonify
import paho.mqtt.client as mqtt
from flask_sqlalchemy import SQLAlchemy
from device_check import get_connected_devices, check_registered_devices
import os
import yaml
import json
import logging
from datetime import datetime
import requests
from face_recog import face_recog

# Initializations

global config, secrets
with open('config.yml', 'r') as config_file:
    global config
    config = yaml.safe_load(config_file)

logging.basicConfig(filename='rpi.log', format='%(asctime)s.%(msecs)03d,%(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S', filemode='w+')
logger = logging.getLogger()
# logger.setLevel(logging.INFO)

print("Server Starting...")
logger.info("Server Starting...")

# MQTT mqtt_client
mqtt_client = mqtt.Client("rpi")

# Flask
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///registry.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
app.config['SECRET_KEY'] = 'secret_key'
app.config['UPLOAD_FOLDER'] = 'activity_vlogs'
with app.app_context():
    db = SQLAlchemy(app)


# SQLite table initializations
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
    timestamp = db.Column(db.String(32), nullable=False)
    # Detection_results: 0 = pending, -1 = False (Negative), +1 = True (Positive)
    detection_result = db.Column(db.Integer, nullable=False)
    suppressor_name = db.Column(db.String(32), nullable=True)


# Create tables
with app.app_context():
    db.create_all()

# Globals
received_data = {
    "alert_id": None,
    "video_url": None,
    "intrusion_result": None
}
latest_path = ''
latest_filename = ''


# Helper functions

def on_connect(_mqtt_client, userdata, flags, rc):
    if rc == 0:
        print(f"Connected to broker as '{_mqtt_client._client_id.decode('utf-8')}'.")
    else:
        print(
            f"Failed to connect to broker as '{_mqtt_client._client_id.decode('utf-8')}'. Retrying...")


def on_message(_mqtt_client, userdata, message):
    print(message.topic, ":", len(message.payload))
    if message.topic == 'rpi_to_user':
        msg_payload = str(json.loads(message.payload.decode("utf-8")))
        message_parts = msg_payload.split(',')
        print("Video URL:", message_parts[1])
        global received_data
        print("-------", received_data)
        received_data["alert_id"] = message_parts[0]
        received_data["video_url"] = message_parts[1]
        received_data["intrusion_result"] = message_parts[2]
    elif message.topic == 'activity_detected':
        data = json.loads(message.payload.decode("utf-8"))

        video = data.get('video')
        timestamp = data.get('timestamp')
        device_name = data.get('device_name')

        # Save the video to the 'activity_vlogs' directory
        activity_id = save_video(video, timestamp, device_name)

        # Perform intrusion detection and handle result
        intrusion_detection(payload={
            "video": video,
            "timestamp": timestamp,
            "device_name": device_name,
            "activity_id": activity_id
        })


def send_email_and_update_cloud(subject, body, upload_payload):
    temp1 = requests.post(url=config['cloud_endpoint'] + "latest_activity", json=upload_payload)
    temp2 = requests.post(url=config['cloud_endpoint'] + "send_email", json={"to_email": "harishrohank2@gmail.com", "subject": subject, "body": body})
    print(temp1, temp2)
    return None


def save_video(video, timestamp, device_name):
    global latest_filename
    global latest_path
    # Generate activity_id
    activity_id = f'{datetime.now().strftime("%Y%m%d_%H%M%S")}-{device_name}'
    logger.info(f'{device_name},{activity_id},video_size:{len(video)}')

    # Create the directory if it doesn't exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Decode base64 and save video as a binary file
    video_data = base64.b64decode(video)
    filename = f"{timestamp}-{device_name}.mp4"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    latest_filename = filename
    latest_path = filepath
    
    print(latest_filename, latest_path)

    with open(filepath, 'wb') as file:
        file.write(video_data)

    new_activity_log = ActivityLog(id=activity_id, timestamp=timestamp, detection_result=0)
    with app.app_context():
        db.session.add(new_activity_log)
        db.session.commit()

    return activity_id


def intrusion_detection(payload: dict):
    # TODO: WiFi-based detection
    wifi_check = 0.0

    connected_devices = get_connected_devices()
    check_registered_devices()
    if connected_devices:
        wifi_check = 1.0

    # TODO: ML-based face/posture detection
    face_check = face_recog()  # UPDATE THIS!
    #print("face check is:",face_check)
    

    # TODO: Get weighted result and alert user
    detection_result = (0.75 * wifi_check) + (0.25 * face_check)  # UPDATE THIS!

    logger.info(f'{payload["activity_id"]},detection_result:{detection_result}')
    print(f'{payload["activity_id"]},detection_result:{detection_result}')

    # Save detection result to db
    with app.app_context():
        activity_log = ActivityLog.query.filter_by(id=payload["activity_id"]).first()
        activity_log.detection_result = detection_result
        db.session.commit()
        activity_id = payload["activity_id"]
        # Publish detection result to user
        received_data['alert_id'] = payload["activity_id"]
        received_data['video_url'] = latest_path
        received_data['intrusion_result'] = detection_result
        send_email_and_update_cloud("Site Activity Alert",
                                        f"Possible intrusion detected at your site. {activity_id} at {activity_log.timestamp} with {activity_log.detection_result} certainty.",
                                        payload)


mqtt_client.on_message = on_message
mqtt_client.on_connect = on_connect
#mqtt_client.connect("127.0.0.1")
#mqtt_client.subscribe([("rpi_to_user", 0), ("activity_detected", 0)])
#mqtt_client.loop_start()


# Routes
@app.route('/video')
def serve_video():
    global latest_filename
    global latest_path
    #print(latest_path)
    if latest_path:
        return send_file(latest_path)
    else:
        return "none"


@app.route('/away/<flag>')
def away_route(flag):
    away_flag = flag
    if away_flag == 'true':
        print("*****************************")
        print("Away from Home mode activated")
        print("*****************************")
        return jsonify({"message": "Away from Home mode activated"})
    else:
        print("*******************************")
        print("Away from Home mode deactivated")
        print("*******************************")
        return jsonify({"message": "Away from Home mode deactivated"})
    


# /Users/chetana/PycharmProjects/csc591-iot_project/rpi
@app.route('/render_template_route')
def render_template_route():
    global received_data
    print(received_data)
    return render_template('index.html', alert_id=received_data["alert_id"],
                           video_url=latest_path,
                           intrusion_result=received_data["intrusion_result"])


@app.post('/activity-detected')
# Handle POST from ESP32-CAM
# Request body: {video: base64.b64encode, timestamp: str, device_name: str}
def handle_activity_detected():
    data = json.loads(request.json)

    video = data.get('video')
    timestamp = data.get('timestamp')
    device_name = data.get('device_name')

    # Save the video to the 'activity_vlogs' directory
    activity_id = save_video(video, timestamp, device_name)

    # Asynchronously perform intrusion detection and handle result
    intrusion_detection(payload={
        "video": video,
        "timestamp": timestamp,
        "device_name": device_name,
        "activity_id": activity_id
    })

    return Response(f"{activity_id}", 201)


@app.route('/all_activity', methods=['GET'])
def all_activity():
    return jsonify(db.session.query(ActivityLog).all())


@app.route('/suppress-alert', methods=['POST'])
def process_choice():
    choice = request.form['choice']
    person_name = request.form.get('person_name', '')
    activity_id = request.form.get('alert_id')  # Get person's name from the form
    with app.app_context():
        activity_log = ActivityLog.query.filter_by(id=activity_id).first()
        if choice == 'true' or choice == 'True' or choice == True or choice == 1:
            activity_log.suppressor_name = person_name
            db.session.commit()

    print(f"Alert Id: {activity_id}. Choice sent to RPi: {choice}. Suppressed by: {person_name}")
    return Response("suppressed", 200)


if __name__ == '__main__':
    print("Started")
    app.run(host='0.0.0.0', debug=True, port=8080)
