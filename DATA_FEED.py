import time
import base64
import os
import cv2
from Adafruit_IO import Client, Feed, RequestError  # Import Adafruit IO library

# ---------------------------------------------
# Adafruit IO credentials and client initialization
# ---------------------------------------------
ADAFRUIT_IO_KEY = 'xxxxxxxxxxxxxxxxxxxxx'  # Adafruit IO Key (should be stored in .env for security)
ADAFRUIT_IO_USERNAME = 'your_username'                      # Adafruit IO Username
aio = Client(ADAFRUIT_IO_USERNAME, ADAFRUIT_IO_KEY)   # Initialize Adafruit IO client

# ---------------------------------------------
# Function to send image to Adafruit IO
# ---------------------------------------------
def send_image(frame, name):
    """
    Takes a frame and name, resizes the frame,
    saves it as an image, and uploads it to the
    Adafruit IO 'known' or 'unknown' feed depending
    on the person's name.
    """
    frame = cv2.resize(frame, (300, 300))  # Resize frame to 300x300 for consistency
    cv2.imwrite(name + '.jpg', frame)      # Save image with person's name

    print('Camera: SNAP! Sending photo....')

    # Choose the appropriate feed based on recognition
    cam_feed = aio.feeds('known') if name != 'Unknown' else aio.feeds('unknown')

    # Open the saved image and encode it in base64
    with open(name + '.jpg', "rb") as imageFile:
        image = base64.b64encode(imageFile.read())  # Encode the image in base64
        image_string = image.decode("utf-8")         # Convert bytes to string

        try:
            aio.send(cam_feed.key, image_string)     # Send to Adafruit IO
            print('Picture sent to Adafruit IO')
        except:
            print('Sending to Adafruit IO Failed...')

    time.sleep(2)  # Delay between image transmissions

# ---------------------------------------------
# Function to send lock/unlock authorization
# ---------------------------------------------
def authorize(status):
    """
    Sends a lock/unlock status to the Adafruit IO 'lock' feed.
    '1' for unlock (access granted), '0' for lock (access denied).
    """
    print('Camera: SNAP! Sending info...')
    lock_feed = aio.feeds('lock')  # Get the lock feed from Adafruit IO

    try:
        aio.send(lock_feed.key, status)  # Send lock status
        print('Authorization sent to Adafruit IO')
    except:
        print('Sending to Adafruit IO Failed...')

    time.sleep(2)  # Delay after sending authorization
