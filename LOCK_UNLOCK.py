import time
import base64
import os
from Adafruit_IO import Client, Feed, RequestError  # Adafruit IO for cloud communication
import RPi.GPIO as GPIO  # GPIO control for Raspberry Pi

# ---------------------------------------------
# Adafruit IO credentials and setup
# ---------------------------------------------
ADAFRUIT_IO_KEY = 'xxxxxxxxxxxxxxxxxxxxxx'  # Your Adafruit IO Key
ADAFRUIT_IO_USERNAME = 'your_username'                      # Your Adafruit IO Username
aio = Client(ADAFRUIT_IO_USERNAME, ADAFRUIT_IO_KEY)   # Initialize Adafruit IO client

# ---------------------------------------------
# GPIO setup
# ---------------------------------------------
GPIO.setmode(GPIO.BCM)        # Use Broadcom pin numbering
GPIO.setwarnings(False)       # Disable GPIO warnings

# Define GPIO pins
LED_Green = 26
LED_Red = 19
SERVO_PIN = 18                # Pin connected to servo motor

# Setup GPIO pin modes
GPIO.setup(LED_Green, GPIO.OUT)
GPIO.setup(LED_Red, GPIO.OUT)
GPIO.setup(SERVO_PIN, GPIO.OUT)

# ---------------------------------------------
# Servo setup
# ---------------------------------------------
servo = GPIO.PWM(SERVO_PIN, 50)  # Set PWM on servo pin with 50Hz frequency
servo.start(0)                   # Start PWM with 0% duty cycle (initial position)

# Get Adafruit IO feed for lock control
lock_feed = aio.feeds('lock')

# ---------------------------------------------
# Function to set servo angle
# ---------------------------------------------
def set_servo_angle(angle):
    """Move servo to the specified angle."""
    duty = (angle / 18.0) + 2.5         # Convert angle to duty cycle
    servo.ChangeDutyCycle(duty)        # Send signal to servo
    time.sleep(0.5)                    # Wait for servo to move
    servo.ChangeDutyCycle(0)           # Stop signal to avoid jitter

# ---------------------------------------------
# Main Program Loop
# ---------------------------------------------
try:
    set_servo_angle(0)  # Ensure the servo starts in locked position

    while True:
        try:
            print('Processing...')
            status = aio.receive('lock').value  # Get lock status from Adafruit IO
            print(f'Status: {status}')

            if status == '1':  # If lock status is '1', grant access
                print("Access Granted")
                GPIO.output(LED_Green, GPIO.HIGH)  # Green LED ON
                GPIO.output(LED_Red, GPIO.LOW)     # Red LED OFF
                set_servo_angle(90)                # Unlock the door
                time.sleep(10)                     # Keep it unlocked for 10 seconds
                aio.send(lock_feed.key, 0)         # Reset lock status to '0'
                set_servo_angle(0)                 # Lock the door again
                GPIO.output(LED_Green, GPIO.LOW)   # Turn OFF green LED
                GPIO.output(LED_Red, GPIO.HIGH)    # Turn ON red LED
            else:
                # If status is not '1', keep door locked
                GPIO.output(LED_Green, GPIO.LOW)
                GPIO.output(LED_Red, GPIO.HIGH)

        except Exception as e:
            print(f'Error: {e}')  # Handle communication or runtime errors

        time.sleep(4)  # Wait before next check

# ---------------------------------------------
# Handle manual program exit (Ctrl+C)
# ---------------------------------------------
except KeyboardInterrupt:
    print("\nKeyboard Interrupt detected. Cleaning up...")

# ---------------------------------------------
# Cleanup GPIO and servo before exiting
# ---------------------------------------------
finally:
    GPIO.output(LED_Green, GPIO.LOW)
    GPIO.output(LED_Red, GPIO.LOW)
    set_servo_angle(0)  # Lock door before exit
    servo.stop()        # Stop PWM
    GPIO.cleanup()      # Reset all GPIO pins
    print("GPIO cleaned up. Exiting.")
