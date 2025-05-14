# import datetime
# import json
import time

# import paho.mqtt.client as mqtt
from grove_rgb_lcd import setRGB, setText
from grovepi import digitalRead, pinMode, ultrasonicRead

# Constants
POUBELLENUMBER = "01"
TOPIC_OUT = f"/Junia/ProjetKN/Poubelle/{POUBELLENUMBER}/fullness"
TOPIC_IN = f"/Junia/ProjetKN/Poubelle/{POUBELLENUMBER}/msg"
MOVEMENT_ENABLED = True
ULTRASONIC_RANGER = 0
BUTTON_PIN = 2
DHT_SENSOR_PORT = 7  # Connect the DHt sensor to port 7
LCD_WIDTH = 16  # LCD width in characters
UPDATE_INTERVAL = 0.5  # Update interval in seconds


def read_distance():
    """Read distance from ultrasonic sensor."""
    try:
        return ultrasonicRead(ULTRASONIC_RANGER)
    except (IOError, TypeError) as e:
        print(f"Error reading distance: {e}")
        return None


def calculate_percentage(current_distance, initial_distance):
    """Calculate fill percentage based on distance change."""
    if current_distance is None or initial_distance is None:
        return 0

    percentage = (initial_distance - current_distance) / initial_distance * 100

    # Clamp percentage between 0 and 100
    if percentage < 0:
        return 0
    elif percentage > 100:
        return 100
    else:
        return percentage


def create_progress_bar(percentage):
    """Create a text-based progress bar."""
    filled_length = int(LCD_WIDTH * percentage / 100)
    return "█" * filled_length + "░" * (LCD_WIDTH - filled_length)


def set_display_color(percentage):
    """Set display color based on percentage (green to red gradient)."""
    r = int(255 * percentage / 100)
    g = int(255 * (100 - percentage) / 100)
    b = 0
    setRGB(r, g, b)


def update_display(percentage):
    """Update LCD display with percentage and progress bar."""
    progress_bar = create_progress_bar(percentage)
    percentage_text = f"{int(percentage)}%"
    setText(percentage_text + "\n" + progress_bar)


def check_button():
    """Check if button is pressed."""
    try:
        return digitalRead(BUTTON_PIN) == 1
    except (IOError, TypeError) as e:
        print(f"Error reading button: {e}")
        return False


#
#
# def send_message(client, message):
#     """Send a message to the MQTT broker."""
#     try:
#         client.publish(TOPIC_OUT, json.dumps(message))
#         print("Message sent:", message)
#     except Exception as e:
#         print(f"Error sending message: {e}")
#
#
# def on_pub(client, userdata, result):
#     print("Message publié")
#
#
# def on_message(client, userdata, msg):
#     payload = msg.payload.decode()
#     print("Reçu", payload, "sur", msg.topic)
#
#     if msg.topic != TOPIC_IN:
#         return
#
#     data = json.loads(payload)
#
#     if percentage >= 75:
#         action_remplit = "Il faut vider la poubelle"
#
#     cmds = {"action_remplit": action_remplit}
#     client.publish(TOPIC_OUT, json.dumps(cmds))
#     print("Commandes envoyées:", cmds)
#


def main():
    """Main program loop."""
    # client = mqtt.Client()
    # client.on_publish = on_pub
    # client.on_message = on_message
    #
    # client.connect("mosquitto.junia.com", 1883, 60)
    # client.subscribe(TOPIC_IN, qos=2)
    # client.loop_forever()

    try:
        # Initialize with a blank screen and neutral color
        setText("")
        setRGB(0, 128, 0)  # Start with green color
        print("LCD initialized successfully")
    except Exception as e:
        print(f"Error initializing LCD: {e}")

    pinMode(BUTTON_PIN, "INPUT")
    pinMode(ULTRASONIC_RANGER, "INPUT")

    distance_init = read_distance()
    percentage = 0

    while True:
        try:
            # Check if button is pressed to reset
            if check_button():
                distance_init = read_distance()
                percentage = 0

            # Read current distance and calculate percentage if movement tracking is enabled
            if MOVEMENT_ENABLED:
                current_distance = read_distance()
                percentage = calculate_percentage(current_distance, distance_init)

            # Update display
            set_display_color(percentage)
            update_display(percentage)

            # Pause before next update
            time.sleep(UPDATE_INTERVAL)

        except Exception as e:
            print(f"Error in main loop: {e}")


if __name__ == "__main__":
    main()
