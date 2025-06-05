import numpy as np
import cv2
import socket
import face_recognition
from data_feed import send_image, authorize
import os
import time
import smtplib
from email.message import EmailMessage

class SecurityCheck(object):
    def __init__(self, host, port):
        self.start = time.time()

        # Initialize face recognition variables
        self.process_this_frame = 0  # Counter to process every nth frame for performance
        self.face_locations = []     # List to store face locations in the frame
        self.face_encodings = []     # List to store face encodings in the frame
        self.face_names = []         # List to store recognized face names

        # Setup socket server for receiving video frames
        self.server_socket = socket.socket()
        self.server_socket.bind((host, port))
        self.server_socket.listen(1)
        print("Waiting for connection...")
        self.connection, self.client_address = self.server_socket.accept()
        print("Connection from:", self.client_address)

        # Load known face data from disk
        self.load_known_faces()

        # Start the video streaming and recognition loop
        self.streaming()

    def load_known_faces(self):
        folder = "known_faces"
        self.known_face_names = []      # Names of known people
        self.known_face_encodings = []  # Encodings of known faces

        # Iterate through all images in the known_faces folder
        for filename in os.listdir(folder):
            path = os.path.join(folder, filename)
            name, ext = os.path.splitext(filename)
            if ext.lower() in ['.jpg', '.png', '.jpeg']:
                image = face_recognition.load_image_file(path)
                encodings = face_recognition.face_encodings(image)
                if encodings:
                    self.known_face_names.append(name)
                    self.known_face_encodings.append(encodings[0])
                    print("Loaded:", name)
                else:
                    print("No face found in", filename)

    def process_frame(self):
        speed = 3  # Process every 3rd frame for speed/performance
        small_frame = cv2.resize(self.frame, (0, 0), fx=0.25, fy=0.25)  # Resize frame for faster processing
        # Try fx=0.5 for better accuracy if needed
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)  # Convert BGR to RGB

        if self.process_this_frame % speed == 0:
            # Detect face locations and encodings in the current frame
            self.face_locations = face_recognition.face_locations(rgb_small_frame)
            self.face_encodings = face_recognition.face_encodings(rgb_small_frame, self.face_locations)
            self.face_names = []

            tolerance = 0.45  # Tighter threshold for better accuracy

            for face_encoding in self.face_encodings:
                # Compare detected face with known faces
                face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)

                if len(face_distances) > 0:
                    best_match_index = np.argmin(face_distances)
                    best_distance = face_distances[best_match_index]
                    print(f"Best match: {self.known_face_names[best_match_index]} with distance {best_distance:.2f}")

                    if best_distance < tolerance:
                        name = self.known_face_names[best_match_index]
                    else:
                        name = "Unknown"
                else:
                    name = "Unknown"

                self.face_names.append(name)

        self.process_this_frame += 1
        if self.process_this_frame >= speed:
            self.process_this_frame = 0

    def send_email_alert(self, name, frame):
        try:
            msg = EmailMessage()
            sender_email = 'your_email@gmail.com'  # Change this email
            # Use an app password or OAuth2 for better security
            # Do not use your main email password directly
            receiver_email = 'reciever_email@gmail.com'  # Change this email
            password = 'xxxxxxxxxxxxxxxxxxx'  # Change this password

            msg['Subject'] = f'Security Alert: {name}'
            msg['From'] = sender_email
            msg['To'] = receiver_email

            # Set email content based on recognition result
            if name == "Unknown":
                msg.set_content("An unknown person was detected by the security system.")
            else:
                msg.set_content(f"{name} was recognized by the security system.")

            # Attach the detected face image to the email
            ret, jpeg = cv2.imencode('.jpg', frame)
            if ret:
                img_data = jpeg.tobytes()
                msg.add_attachment(img_data, maintype='image', subtype='jpeg', filename=f"{name}.jpg")

            # Send the email using Gmail's SMTP server
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                smtp.login(sender_email, password)
                smtp.send_message(msg)
                print(f"Email alert sent for {name}")
        except Exception as e:
            print("Failed to send email:", e)

    def send_adafruit(self, name):
        check = time.time() - self.start
        print("Time since last auth:", check)
        # Only send data if enough time has passed since last alert
        if check > 5:
            if name == 'Unknown':
                authorize(0)  # Send unauthorized signal
                send_image(self.frame, name)  # Send image to Adafruit
                self.send_email_alert(name, self.frame)  # Send email alert
                cv2.imwrite(f'unknown_faces/unknown_{int(time.time())}.png', self.frame)  # Save unknown face
            else:
                authorize(1)  # Send authorized signal
                send_image(self.frame, name)
                self.send_email_alert(name, self.frame)
            self.start = time.time()  # Reset timer

    def display_frame(self):
        # Draw rectangles and labels around detected faces
        for (top, right, bottom, left), name in zip(self.face_locations, self.face_names):
            self.send_adafruit(name)
            # Scale back up face locations since the frame was resized
            top *= 4
            right *= 4
            bottom *= 4
            left *= 4

            cv2.rectangle(self.frame, (left, top), (right, bottom), (0, 0, 255), 2)
            cv2.rectangle(self.frame, (left, bottom - 35), (right, bottom), (0, 0, 255), cv2.FILLED)
            font = cv2.FONT_HERSHEY_DUPLEX
            cv2.putText(self.frame, name, (left + 6, bottom - 6), font, 1.0, (255, 255, 255), 1)

        cv2.imshow('Video', self.frame)  # Display the frame

    def receive_frame(self):
        # Receive the length of the incoming frame
        length_bytes = self.connection.recv(4)
        if not length_bytes:
            return None

        length = int.from_bytes(length_bytes, byteorder='big')
        data = b''
        # Receive the frame data based on the length
        while len(data) < length:
            more = self.connection.recv(length - len(data))
            if not more:
                return None
            data += more

        # Decode the received image data
        image = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
        return image

    def streaming(self):
        try:
            print("Streaming started. Press 'CTRL+C' to quit.")
            while True:
                self.frame = self.receive_frame()  # Receive a frame from the client
                if self.frame is None:
                    print("Disconnected.")
                    break

                self.frame = cv2.flip(self.frame, 0)  # Flip the frame vertically if needed
                self.process_frame()                  # Process the frame for face recognition
                self.display_frame()                  # Display the frame with annotations

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
        finally:
            self.connection.close()
            self.server_socket.close()
            cv2.destroyAllWindows()

if __name__ == '__main__':
    host, port = '', 8000  # Listen on all interfaces, port 8000
    SecurityCheck(host, port)



