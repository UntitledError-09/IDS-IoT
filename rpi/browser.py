# from flask import Flask, render_template, request
# import paho.mqtt.client as mqtt
# import requests
#
# app = Flask(__name__)
#
# # MQTT configuration
# broker_address = "127.0.0.1"  # Replace with your MQTT broker address
# topic = "test_topic"  # Replace with your MQTT topic
#
# # Function to handle MQTT messages
# def on_message(client, userdata, message):
#     # Process MQTT messages here
#     # Extract video, alert ID, intrusion result, etc., from the received message
#     msg_payload = str(message.payload.decode("utf-8"))
#
#     # For example, assuming the payload format is comma-separated: "alert_id,video_url,intrusion_result"
#     message_parts = msg_payload.split(',')
#
#     alert_id = message_parts[0]  # Extract alert ID
#     video_url = message_parts[1]  # Extract video URL
#     intrusion_result = message_parts[2]  # Extract intrusion result
#
#     # Display video and information on the web page (sample code)
#     # For actual implementation, use a suitable way to display video and information in the HTML
#     render_template('index.html', alert_id=alert_id, video_url=video_url, intrusion_result=intrusion_result)
#
# # Function to send HTTP response to RPi based on user choice
# def send_response_to_rpi(choice):
#     # Define the RPi endpoint to which you want to send the HTTP request
#     rpi_endpoint = "http://your_rpi_ip_address:port/receive_response"  # Replace with your RPi's IP address and port
#
#     # Define the data payload to be sent to the RPi
#     data = {'choice': choice}
#
#     try:
#         # Send an HTTP POST request to the RPi endpoint
#         response = requests.post(rpi_endpoint, json=data)
#
#         # Check the response status code
#         if response.status_code == 200:
#             print("Response sent to RPi successfully")
#         else:
#             print("Failed to send response to RPi. Status code:", response.status_code)
#     except requests.exceptions.RequestException as e:
#         print("Error sending request to RPi:", e)

# # MQTT client setup
# client = mqtt.Client()
# client.on_message = on_message
# client.connect(broker_address)
# client.subscribe(topic)
# client.loop_start()
#
# # Route for displaying the web page
# @app.route('/')
# def index():
#     # Render HTML template with video display and user interaction options
#     return render_template('index.html')
#
# # Route to handle user interaction
# @app.route('/process_choice', methods=['POST'])
# def process_choice():
#     choice = request.form['choice']  # Get user choice from the form
#     send_response_to_rpi(choice)  # Send user choice to RPi
#     return "Choice sent to RPi: " + choice  # Return a response to the browser
#
# if __name__ == '__main__':
#     app.run(debug=False)

from flask import Flask, render_template, request, send_from_directory
import paho.mqtt.client as mqtt
import requests

app = Flask(__name__)

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

@app.route('/render_template_route')
def render_template_route():
    global received_data
    return render_template('index.html', alert_id=received_data["alert_id"],
                           video_url=received_data["video_url"],
                           intrusion_result=received_data["intrusion_result"])

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

if __name__ == '__main__':
    broker_address = "127.0.0.1"
    topic = "test_topic"

    client = mqtt.Client()
    client.on_message = on_message
    client.connect(broker_address)
    client.subscribe(topic)
    client.loop_start()
    app.run(debug=True)