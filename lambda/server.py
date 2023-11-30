import base64

from flask import Flask, request, jsonify, render_template
from bson import json_util
from flask_pymongo import PyMongo
import boto3
import yaml

app = Flask(__name__)

# Load configuration from config.yml
with open('config.yml', 'r') as config_file:
    config = yaml.safe_load(config_file)

# MongoDB Configuration
app.config['MONGO_URI'] = config['mongo_uri']
mongo = PyMongo(app)

# AWS SES Configuration
aws_access_key_id = config['aws_access_key_id']
aws_secret_access_key = config['aws_secret_access_key']
aws_region = config['aws_region']


# Routes

@app.route('/', methods=['GET'])
def index_route():
    return render_template('index.html')


@app.route('/latest_activity', methods=['POST', 'GET'])
def latest_activity():
    if request.method == 'POST':
        data = request.json
        video = data.get('video')
        timestamp = data.get('timestamp')
        device_name = data.get('device_name')
        activity_id = data.get('activity_id')

        # Store data in MongoDB
        activity_data = {'video': video, 'timestamp': timestamp, 'device_name': device_name, 'activity_id': activity_id}
        mongo.db.latest_activity.insert_one(activity_data)

        return jsonify({'message': 'Data stored successfully'}), 201
    elif request.method == 'GET':
        data = request.json
        email = data.get('email')

        # Fetch the latest data from MongoDB
        latest_activity_log = mongo.db.latest_activity.find_one({'email': email}, sort=[('_id', -1)])
        if latest_activity_log:
            return jsonify(
                {'activity_id': latest_activity_log['activity_id'], 'video': latest_activity_log['video'],
                 'timestamp': latest_activity_log['timestamp']}), 200
        else:
            return jsonify({'message': 'No activity found for the specified email'}), 404


@app.route('/all_activity', methods=['GET'])
def all_activity():
    data = request.args
    email = data.get('email')

    # Fetch all records from MongoDB in descending order
    all_activity_logs = json_util.dumps(mongo.db.latest_activity.find({'email': email}, sort=[('_id', -1)]))

    if all_activity_logs:
        return jsonify({'all_activity': all_activity_logs}), 200
    else:
        return jsonify({'message': 'No activity records found'}), 404


@app.route('/send_email', methods=['POST'])
def send_email():
    data = request.json
    to_email = data.get('to_email')
    subject = data.get('subject')
    body = data.get('body')

    # Send email using AWS SES
    ses_client = boto3.client('ses', aws_access_key_id=aws_access_key_id,
                              aws_secret_access_key=aws_secret_access_key, region_name=aws_region)

    response = ses_client.send_email(
        Source=config['mail_username'],
        Destination={'ToAddresses': [to_email]},
        Message={'Subject': {'Data': subject}, 'Body': {'Text': {'Data': body}}},
    )

    if response['ResponseMetadata']['HTTPStatusCode'] == 200:
        return jsonify({'message': 'Email sent successfully'}), 200
    else:
        return jsonify({'error': 'Failed to send email'}), 500


if __name__ == '__main__':
    app.run(debug=True, port=8080)
