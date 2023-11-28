from flask import Flask, request, jsonify
from flask_pymongo import PyMongo
from bson import ObjectId
import random
import string
import yaml
import bcrypt
import boto3
from flask_mail import Mail, Message

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

# Model
class Site:
    def create(self, name, location, email):
        auth_token = self.generate_auth_token()
        site_data = {'name': name, 'location': location, 'email': email, 'auth_token': auth_token, 'logs': []}
        site_id = mongo.db.sites.insert_one(site_data).inserted_id
        return site_id

    def update_logs(self, site_id, logs):
        mongo.db.sites.update_one({'_id': ObjectId(site_id)}, {'$push': {'logs': logs}})

    def generate_auth_token(self):
        return ''.join(random.choices(string.ascii_letters + string.digits, k=16))


class User:
    def create(self, site_id, name, email, password):
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        user_data = {'site': site_id, 'name': name, 'email': email, 'password': hashed_password}
        user_id = mongo.db.users.insert_one(user_data).inserted_id
        return user_id

    def authenticate(self, email, password):
        user_data = mongo.db.users.find_one({'email': email})
        if user_data and bcrypt.checkpw(password.encode('utf-8'), user_data['password']):
            return user_data['_id']
        return None


# Controller
site_controller = Site()
user_controller = User()


# Routes
@app.route('/new-site', methods=['POST'])
def new_site():
    data = request.json
    name = data.get('name')
    location = data.get('location')
    email = data.get('email')

    # Verify email through one-time passcode
    auth_token = site_controller.generate_auth_token()
    site_data = {'name': name, 'location': location, 'email': email, 'auth_token': auth_token, 'logs': []}

    # Send email with OTP
    subject = "Verification Code for Site Sign-Up"
    body = f"Your verification code is: {auth_token}"

    send_email(email, subject, body)

    site_id = mongo.db.sites.insert_one(site_data).inserted_id
    return jsonify({'site_id': str(site_id)}), 201


@app.route('/new-user', methods=['POST'])
def new_user():
    data = request.json
    site_id = data.get('site_id')
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')

    # Verify email through one-time passcode
    auth_token = site_controller.generate_auth_token()
    user_data = {'site': site_id, 'name': name, 'email': email, 'password': bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())}

    # Send email with OTP
    subject = "Verification Code for User Sign-Up"
    body = f"Your verification code is: {auth_token}"

    send_email(email, subject, body)

    user_id = mongo.db.users.insert_one(user_data).inserted_id
    return jsonify({'user_id': str(user_id)}), 201


@app.route('/update-logs', methods=['POST'])
def update_logs():
    data = request.json
    site_id = data.get('site_id')
    logs = data.get('logs')

    site_controller.update_logs(site_id, logs)
    return jsonify({'message': 'Logs updated successfully'}), 200


@app.route('/send-email', methods=['POST'])
def send_email_route():
    data = request.json
    user_id = data.get('user_id')

    # Fetch user details from the database
    user_data = mongo.db.users.find_one({'_id': ObjectId(user_id)})
    if user_data:
        email_address = user_data['email']

        # Send email using AWS SES
        subject = "Subject of the Email"
        body = "Body of the Email"

        send_email(email_address, subject, body)

        return jsonify({'message': 'Email sent successfully'}), 200
    else:
        return jsonify({'error': 'User not found'}), 404


@app.route('/site-signin', methods=['POST'])
def site_signin():
    data = request.json
    email = data.get('email')
    auth_token = data.get('auth_token')

    site_data = mongo.db.sites.find_one({'email': email, 'auth_token': auth_token})
    if site_data:
        return jsonify({'message': 'Site signed in successfully'}), 200
    else:
        return jsonify({'error': 'Invalid email or auth_token'}), 401


@app.route('/user-signin', methods=['POST'])
def user_signin():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    user_id = user_controller.authenticate(email, password)
    if user_id:
        return jsonify({'user_id': str(user_id), 'message': 'User signed in successfully'}), 200
    else:
        return jsonify({'error': 'Invalid email or password'}), 401


def send_email(to_email, subject, body):
    # Send email using AWS SES
    ses_client = boto3.client('ses', aws_access_key_id=aws_access_key_id,
                              aws_secret_access_key=aws_secret_access_key, region_name=aws_region)

    response = ses_client.send_email(
        Source=config['mail_username'],
        Destination={'ToAddresses': [to_email]},
        Message={'Subject': {'Data': subject}, 'Body': {'Text': {'Data': body}}},
    )

    return response


if __name__ == '__main__':
    app.run(debug=True)


def lambda_handler(event, context):
    app.run()
