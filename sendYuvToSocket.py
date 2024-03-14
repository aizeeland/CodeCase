import os
import time
import socket
import subprocess
import argparse

# Parse command line arguments
parser = argparse.ArgumentParser(description='Start a socket server and send .yuv420 files.')
parser.add_argument('camera', type=int, help='The camera number to use for the socket server.')
args = parser.parse_args()

# Directory to watch for new YUV images
if args.camera == 0:
    image_dir = 'camera0yuv420'
    port = 8888
if args.camera == 1:
    image_dir = 'camera1yuv420'
    port = 7777

# Create a socket server
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind(('0.0.0.0', port)) # Bind to localhost
server_socket.listen(1)

print('Server started. Waiting for connections...')

# Accept a connection
client_socket, addr = server_socket.accept()
if addr[0] != 'your_client_ip':
    print('Connection from unexpected client: ', addr)
    client_socket.close()
else:
    print('Client connected: ', addr)
    time.sleep(5)

# Continuously check the directory for new .yuv420 files
while True:
    # Check if the rpicam-still program is running
    if subprocess.run(['pgrep', '-x', 'rpicam-still'], stdout=subprocess.DEVNULL).returncode != 0:
        print('rpicam-still is no longer running. Stopping...')
        break

    # Get a sorted list of .data files
    filenames = sorted(filename for filename in os.listdir(image_dir) if filename.endswith('.yuv420'))

    for filename in filenames:
        # Read the file as binary data
        with open(os.path.join(image_dir, filename), 'rb') as f:
            byte_array = f.read()

        # Send the byte array over the socket
        client_socket.send(byte_array)

        # Remove the file after sending it
        os.remove(os.path.join(image_dir, filename))

    # Wait for a second before checking the directory again
    time.sleep(1)

# Close the sockets
client_socket.close()
server_socket.close()
