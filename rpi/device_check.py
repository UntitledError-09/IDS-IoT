import schedule
from rpi import User
import subprocess
import time

registered_devices = User.query.with_entities(User.mac_address).all()

# Extract the mac_addresses into a list
mac_addresses = [device[0] for device in registered_devices]
alarm_triggered = False

def get_connected_devices():
    try:
        output = subprocess.check_output(["arp", "-a"])
        output_lines = output.decode().split("\n")

        devices = []

        for line in output_lines:
            line_parts = line.split()
            if len(line_parts) >= 4:
                mac_address = line_parts[3]
                devices.append(mac_address)

        return devices

    except subprocess.CalledProcessError as e:
        raise OSError(f"Command execution failed: {e}")
    except FileNotFoundError as e:
        raise OSError(f"Required command not found: {e}")



def check_registered_devices():
    global alarm_triggered
    connected_devices = get_connected_devices()
    unregistered_devices = [device for device in connected_devices if device not in registered_devices]

    if unregistered_devices:
        alarm_triggered = True

    else:
        if alarm_triggered:
            alarm_triggered = False


def periodic_device_check():
    connected_devices = get_connected_devices()
    check_registered_devices(connected_devices)

schedule.every(30).seconds.do(periodic_device_check)

# Run the scheduled job indefinitely
while True:
    schedule.run_pending()
    time.sleep(1)
