import subprocess

registered_devices = ['9c:3e:53:81:e0:60', '9c:3e:53:87:37:a2']
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


connected_devices = get_connected_devices()
print("Connected devices:")
for device in connected_devices:
    print(device)

def check_registered_devices(connected_devices):
    global alarm_triggered

    unregistered_devices = [device for device in connected_devices if device not in registered_devices]

    if unregistered_devices:
        alarm_triggered = True
        print("Unregistered devices detected:")
        for device in unregistered_devices:
            print(device)
        print("ALARM! Unregistered device(s) detected on the network!")

    else:
        if alarm_triggered:
            alarm_triggered = False
            print("No unregistered devices detected.")

