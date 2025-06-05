import socket
import time
import io
import cv2
import numpy as np
from picamera2 import Picamera2
from PIL import Image

# ---------------------------------------------
# Setup socket for client to connect to server
# ---------------------------------------------
client_socket = socket.socket()  # Create a TCP/IP socket
client_socket.connect(('192.192.xx.xx', 8000))  # Connect to the server's IP and port
connection = client_socket.makefile('wb')  # Create a file-like object for the socket (write-binary)

# ---------------------------------------------
# Initialize PiCamera
# ---------------------------------------------
camera = Picamera2()  # Initialize the PiCamera2
camera_config = camera.create_video_configuration(main={"size": (640, 480)})  # Set resolution to 640x480
camera.configure(camera_config)  # Apply the configuration
camera.start()  # Start camera preview
time.sleep(2)  # Allow camera to warm up

# ---------------------------------------------
# Streaming loop - capture, encode, and send frames
# ---------------------------------------------
try:
    print("Streaming started...")

    while True:
        frame = camera.capture_array()  # Capture frame as numpy array
        frame = cv2.flip(frame, 0)  # Flip the image vertically if required
        img = Image.fromarray(frame).convert("RGB")  # Convert to PIL Image in RGB format

        # Encode frame to JPEG format into memory buffer
        stream = io.BytesIO()  # Create in-memory buffer
        img.save(stream, format='JPEG')  # Save image in JPEG format into buffer
        jpeg_bytes = stream.getvalue()  # Get raw JPEG bytes

        # Send the size of the image followed by the image itself
        length = len(jpeg_bytes)  # Calculate byte length of the image
        client_socket.sendall(length.to_bytes(4, byteorder='big'))  # Send image size (4 bytes)
        client_socket.sendall(jpeg_bytes)  # Send image data

        time.sleep(0.1)  # Small delay to control frame rate and CPU usage

# ---------------------------------------------
# Handle program interruption and errors
# ---------------------------------------------
except KeyboardInterrupt:
    print("Stream interrupted by user.")  # Graceful exit if user presses Ctrl+C
except Exception as e:
    print("Error:", e)  # Print any other error that occurs

# ---------------------------------------------
# Cleanup on exit
# ---------------------------------------------
finally:
    connection.close()  # Close file-like socket connection
    client_socket.close()  # Close socket
    print("Connection closed.")
