import datetime
import json
import os
import time

import paho.mqtt.client as mqtt
from grove_rgb_lcd import setRGB, setText
from grovepi import digitalRead, pinMode, ultrasonicRead

# Constants
POUBELLENUMBER = "03"
TOPIC_OUT = f"/Junia/ProjetKN/Poubelle/{POUBELLENUMBER}/fullness"
TOPIC_IN = f"/Junia/ProjetKN/Poubelle/{POUBELLENUMBER}/msg"
ULTRASONIC_RANGER = 2
MOVEMENT_PIN = 5
BUTTON_PIN = 3
LCD_PIN = 2
LCD_WIDTH = 16  # LCD width in characters
UPDATE_INTERVAL = 0.5  # Update interval in seconds
MOVEMENT_COOLDOWN = 10  # Cooldown after movement detection (seconds)
MEASUREMENT_DELAY = 5  # Delay before taking measurement after movement (seconds)


def read_distance():
    """Read distance from ultrasonic sensor."""
    try:
        return ultrasonicRead(ULTRASONIC_RANGER)
    except (IOError, TypeError) as e:
        print(f"Error reading distance: {e}")
        return None


def read_movement():
    """Read movement from the sensor."""
    try:
        return digitalRead(MOVEMENT_PIN)
    except (IOError, TypeError) as e:
        print(f"Error reading movement: {e}")
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
    # Use simpler characters that are more likely to be supported by the LCD
    return ">" * filled_length + "-" * (LCD_WIDTH - filled_length)


def set_display_color(percentage):
    """Set display color based on percentage (green to red gradient)."""
    r = int(255 * percentage / 100)
    g = int(255 * (100 - percentage) / 100)
    b = 0
    setRGB(r, g, b)


def update_display(percentage):
    """Update LCD display with percentage and progress bar."""
    progress_bar = create_progress_bar(percentage)
    print(f"Progress bar: {progress_bar}")
    percentage_text = f"rempli a {int(percentage)}%"
    # Ensure text is properly formatted for the LCD
    setText_safe(percentage_text + "\n" + progress_bar)


def setText_safe(text):
    """Safely set LCD text with error handling."""
    try:
        setText(text)
    except Exception as e:
        print(f"Error setting LCD text: {e}")


def check_button():
    """Check if button is pressed."""
    try:
        return digitalRead(BUTTON_PIN) == 1
    except (IOError, TypeError) as e:
        print(f"Error reading button: {e}")
        return False


def save_data_to_json(percentage, timestamp):
    """Save the trash bin data to a JSON file."""
    data = {
        "poubelle_id": POUBELLENUMBER,
        "percentage": percentage,
        "timestamp": timestamp,
    }

    try:
        with open("last_trashbin_data.json", "w") as json_file:
            json.dump(data, json_file, indent=4)
        print(f"Data saved to last_trashbin_data.json")
        return data  # Return the data dictionary for immediate use
    except Exception as e:
        print(f"Error saving data to JSON: {e}")
        return None


def init_pins():
    """Initialize GPIO pins."""
    pinMode(BUTTON_PIN, "INPUT")
    pinMode(ULTRASONIC_RANGER, "INPUT")
    pinMode(LCD_PIN, "OUTPUT")
    pinMode(MOVEMENT_PIN, "INPUT")


#
#
def send_message(client, message):
    """Send a message to the MQTT broker."""
    try:
        client.publish(TOPIC_OUT, json.dumps(message))
        print("Message sent:", message)
    except Exception as e:
        print(f"Error sending message: {e}")


def load_json_file(filename):
    """Load data from a JSON file."""
    try:
        if os.path.exists(filename):
            with open(filename, "r") as json_file:
                return json.load(json_file)
        else:
            print(f"File {filename} not found")
            return None
    except Exception as e:
        print(f"Error loading JSON file: {e}")
        return None


#
# Global flag for reset requests from MQTT
reset_requested = False


#
# def on_pub(client, userdata, result):
#     print("Message publié")
#
#
def on_message(client, userdata, msg):
    """Handle incoming MQTT messages."""
    try:
        payload = msg.payload.decode()
        print("Reçu:", payload, "sur", msg.topic)

        if msg.topic != TOPIC_IN:
            return

        # Parse the message
        data = json.loads(payload)

        # Check if this is a reset command
        if "command" in data and data["command"] == "reset":
            print("Reset command received! Resetting distance...")
            # We'll set a flag to reset in the main loop since we can't
            # directly access variables in the main function
            global reset_requested
            reset_requested = True
            return

        # Handle other message types here
        # Save received data to history file
        save_received_data(data)

        percentage = data.get("percentage", 0)
        if percentage >= 75:
            action_remplit = "Il faut vider la poubelle"
            print(action_remplit)
    except Exception as e:
        print(f"Error processing message: {e}")


def main():
    """Main program loop."""
    try:
        # Initialize with a blank screen and neutral color
        setText("")
        setRGB(0, 128, 0)  # Start with green color
        print("LCD initialized successfully")
    except Exception as e:
        print(f"Error initializing LCD: {e}")

    # Initialize GPIO pins
    init_pins()

    # Initialize MQTT client
    try:
        client = mqtt.Client()
        client.connect(b"10.40.150.20", 1883, 60)  # Remove 'b' prefix
        client.on_message = on_message
        client.subscribe(TOPIC_IN, qos=2)
        print("Connected to MQTT broker and subscribed to", TOPIC_IN)
        client.loop_start()  # Non-blocking loop
    except Exception as e:
        print(f"Error connecting to MQTT broker: {e}")
        client = None

    # Uncomment if you want message handling
    # client.on_publish = on_pub
    # client.on_message = on_message
    # client.subscribe(TOPIC_IN, qos=2)

    # client.on_publish = on_pub
    # client.on_message = on_message
    # client.connect("mosquitto.junia.com", 1883, 60)
    # client.subscribe(TOPIC_IN, qos=2)
    # client.loop_forever()

    distance_init = read_distance()
    percentage = 0
    last_movement_time = 0  # Track when the last movement was detected
    waiting_for_measurement = (
        False  # Flag to track if we're waiting to take a measurement
    )
    movement_detected_time = 0  # When movement was detected

    while True:
        try:
            global reset_requested
            # Check if button is pressed to reset
            if check_button() or reset_requested:
                distance_init = read_distance()
                percentage = 0
                print("Distance initialized:", distance_init)
                reset_requested = False

            # Read current distance and calculate percentage if movement tracking is enabled
            # Read current distance and calculate percentage if movement tracking is enabled
            movement = read_movement()

            current_time = time.time()
            time_since_last_movement = current_time - last_movement_time

            # Check for new movement detection
            if (
                not waiting_for_measurement
                and movement == 0
                and time_since_last_movement >= MOVEMENT_COOLDOWN
            ):
                # Record when movement was detected
                movement_detected_time = current_time
                waiting_for_measurement = True
                print(
                    f"Movement detected at {datetime.datetime.now().isoformat()}! Will measure in {MEASUREMENT_DELAY} seconds..."
                )

            # Check if it's time to take measurement after waiting
            if (
                waiting_for_measurement
                and (current_time - movement_detected_time) >= MEASUREMENT_DELAY
            ):
                # Now take the measurement
                current_distance = read_distance()
                current_timestamp = datetime.datetime.now().isoformat()
                print(
                    f"[{current_timestamp}] Current distance (after delay): {current_distance}"
                )
                percentage = calculate_percentage(current_distance, distance_init)

                # Update display
                set_display_color(percentage)
                update_display(percentage)

                # Save data to JSON
                json_data = save_data_to_json(percentage, current_timestamp)

                # Send the data via MQTT if client is connected
                if client and json_data:
                    send_message(client, json_data)

                # Reset flags and update last movement time
                waiting_for_measurement = False
                last_movement_time = current_time
                print(
                    f"[{current_timestamp}] Measurement complete - next detection available in {MOVEMENT_COOLDOWN} seconds"
                )

            # Short sleep to prevent CPU overload
            time.sleep(0.1)

        except Exception as e:
            print(f"Error in main loop: {e}")


if __name__ == "__main__":
    main()
