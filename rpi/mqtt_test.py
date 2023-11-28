import paho.mqtt.client as mqtt
import time
import os

broker_address = "127.0.0.1"
port = 1883
topic = "test_topic"

client = mqtt.Client()
client.connect(broker_address, port=port)
current_directory = os.path.dirname(os.path.abspath(__file__))
video_path = os.path.join(current_directory, "test_video.mp4")

mock_message_payload = f"1234,{video_path},true"
print(video_path)
client.publish(topic, mock_message_payload)

time.sleep(2)

client.disconnect()
