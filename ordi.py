import json
import threading
import time

import paho.mqtt.client as mqtt

TOPIC_OUT = f"/Junia/ProjetKN/Poubelle/+/msg"
TOPIC_IN = f"/Junia/ProjetKN/Poubelle/+/fullness"


def on_message(mqtt_client, userdata, msg):
    """Handle incoming MQTT messages."""
    payload = msg.payload.decode()

    # Check if the topic matches the pattern /Junia/ProjetKN/Poubelle/{bin_id}/fullness
    if not msg.topic.startswith("/Junia/ProjetKN/Poubelle/") or not msg.topic.endswith(
        "/fullness"
    ):
        return

    try:
        data = json.loads(payload)
        poubelle_id = data.get("poubelle_id", 0)
        percentage = data.get("percentage", 0)
        timestamp = data.get("timestamp", 0)

        if percentage >= 50:
            print(
                f"Il faut vider la poubelle {poubelle_id} ({percentage}%) depuis {timestamp}"
            )
    except json.JSONDecodeError:
        print(f"Failed to decode JSON from payload: {payload}")


def send_message_to_bin(bin_number):
    """Send a reset message to the specified bin."""
    topic = f"/Junia/ProjetKN/Poubelle/{bin_number}/msg"
    message = json.dumps({"command": "reset"})
    try:
        result = client.publish(topic, message, qos=2)
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            print(f"Message sent to bin {bin_number}: {message}")
        else:
            print(f"Failed to send message to bin {bin_number}")
    except Exception as e:
        print(f"Error sending message: {e}")


def console_input_handler():
    """Handle console input for sending commands to bins."""
    while True:
        user_input = input("Enter command (e.g., 'R 01' to reset bin 01): ")
        parts = user_input.strip().split()
        if len(parts) == 2 and parts[0].upper() == "R":
            bin_number = parts[1]
            send_message_to_bin(bin_number)
        else:
            print("Invalid command format. Use 'R {bin_number}' (e.g., 'R 01')")


client = mqtt.Client(client_id="poubelle_monitor", protocol=mqtt.MQTTv311)
client.on_message = on_message

# Add error handling for connection
try:
    # Start console input handler in a separate thread
    input_thread = threading.Thread(target=console_input_handler)
    input_thread.daemon = (
        True  # This will make the thread exit when the main program exits
    )
    input_thread.start()

    # Connect to MQTT broker
    client.connect("10.40.150.20", 1883, 60)
    print("Connected to MQTT broker. Enter commands in the format 'R {bin_number}'.")
    client.subscribe(TOPIC_IN, qos=2)
    client.loop_forever()
except Exception as e:
    print(f"Error connecting to MQTT broker: {e}")
