import os
import time
import socket
import subprocess
import argparse
import glob
import struct

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
if addr[0] != '192.168.16.210':
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
    filenames = sorted(filename for filename in os.listdir(image_dir) if filename.endswith('.png'))

    for filename in filenames:
        # Read the file as binary data
        with open(os.path.join(image_dir, filename), 'rb') as f:
            byte_array = f.read()

        # First send the size of the img
        client_socket.send(struct.pack('!I', len(byte_array))

        # Send the byte array over the socket
        client_socket.send(byte_array)

        # Remove the file after sending it
        os.remove(os.path.join(image_dir, filename))

    # Wait for a second before checking the directory again
    time.sleep(1)


# Close the sockets and kill rpicam-still
print('Closing sockets, killing rpicam-still and clearing ports...')
client_socket.close()
server_socket.close()
subprocess.run(['pkill', '-x', 'rpicam-still'])
subprocess.Popen(["python3", "CodeCase/freeport.py", "8888"])
subprocess.Popen(["python3", "CodeCase/freeport.py", "7777"])

# Clear the contents of the camera0yuv420 and camera1yuv420 directories
for folder in ['camera0yuv420', 'camera1yuv420']:
    files = glob.glob(f'{folder}/*')
    for f in files:
        os.remove(f)

