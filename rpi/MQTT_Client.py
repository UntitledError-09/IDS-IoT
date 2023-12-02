import logging
import time
import yaml
import json
import base64
import paho.mqtt.client as mqtt


def current_milli_time():
    return round(time.time_ns())


global config, secrets
with open('config.yml', 'r') as config_file:
    global config
    config = yaml.safe_load(config_file)
# with open(config['secrets_file'], 'r') as secrets_file:
#     global secrets
#     secrets = yaml.safe_load(secrets_file)

BROKER_HOSTNAME = 'localhost'
BROKER_PORT = 1883
# CREDS = secrets['credentials']['mqtt_users'][0]
AUTO_RECONNECT_DELAY = 20
AUTO_RECONNECT_RETRIES = 100
KEEPALIVE = 60
REFRESH_RATE = 0.1

reconnect_flag = True
kill_flag = False

logging.basicConfig(filename='rpi_log.csv', format='%(asctime)s.%(msecs)03d,%(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S', filemode='w+')
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


# function for
def init_mqttc():
    """Returns MQTT client"""

    print("Starting MQTT Client...")

    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print(f"Connected to '{BROKER_HOSTNAME}:{BROKER_PORT}' as '{client._client_id.decode('utf-8')}'.")
        else:
            print(
                f"Failed to connect to '{BROKER_HOSTNAME}:{BROKER_PORT}' as '{client._client_id.decode('utf-8')}'. Retrying...")

    def on_subscribe(client, userdata, mid, granted_qos):
        print(
            f"Subscribed to '{BROKER_HOSTNAME}:{BROKER_PORT}' as '{client._client_id.decode('utf-8')}' with {granted_qos} QoS.")

    def on_publish(client, userdata, mid):
        print(f"Published to '{BROKER_HOSTNAME}:{BROKER_PORT}' as '{client._client_id.decode('utf-8')}'.")

    def reconnect(client):

        if AUTO_RECONNECT_DELAY > 0:
            print(f"Auto-reconnecting in {AUTO_RECONNECT_DELAY} seconds...")
            client.reconnect_flag = True

    def on_disconnect(client, userdata, reasonCode):
        if reasonCode == 0:
            print(f"Disconnected from '{BROKER_HOSTNAME}:{BROKER_PORT}' as '{client._client_id.decode('utf-8')}'.")
            reconnect(client)
        else:
            print(
                f"Disconnected due reasonCode {reasonCode} from '{BROKER_HOSTNAME}:{BROKER_PORT}' as '{client._client_id.decode('utf-8')}'. Retrying...")

        client.kill_flag = True

    client_inst = mqtt.Client(client_id='tester')
    client_inst.kill_flag = False
    client_inst.reconnect_flag = True
    client_inst.enable_logger(logger=logging.Logger('tester'))
    # client_inst.username_pw_set(username=CREDS['username'], password=CREDS['password'])
    # client_inst.tls_set(tls_version=mqtt.ssl.PROTOCOL_TLS)
    client_inst.on_connect = on_connect
    client_inst.on_disconnect = on_disconnect
    client_inst.on_subscribe = on_subscribe
    client_inst.on_publish = on_publish
    client_inst.change_flag = False

    try:
        client_inst.connect(host=BROKER_HOSTNAME, port=BROKER_PORT, keepalive=KEEPALIVE)
    except Exception as e:
        print("Unable to connect to host." + str(e))
        return False
    print("Starting connection...")
    client_inst.loop_start()

    while not client_inst.is_connected() and not client_inst.kill_flag:
        # wait to connect or kill
        time.sleep(REFRESH_RATE)

    return client_inst


m = init_mqttc()

with open("test_video.mp4", "rb") as f:
    temp = m.publish("activity_detected", json.dumps({"video": base64.b64encode(f.read()).decode("utf-8"), "timestamp": 123, "device_name": "abc"}), 0)
    temp.wait_for_publish()
