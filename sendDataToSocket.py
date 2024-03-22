import os
import time
import socket
import subprocess
import argparse
import glob
import struct
import subprocess

connection_error = False

def is_png_complete(data):
    # IEND_CHUNK is how binary .png data ends
    IEND_CHUNK = b'\x00\x00\x00\x00\x49\x45\x4E\x44\xAE\x42\x60\x82'
    return data[-12:] == IEND_CHUNK

def clear_folder(folder):
    files = glob.glob(f'{image_dir}/*.png')
    for f in files:
        os.remove(f)

# Bitsequence = image size -> actual image + EOI marker

# End of image marker
EOI_MARKER = b'EOI'

# Camera settings
camera_settings = {
    "width":4056,
    "height":3040,
    "shutter":20000
}

# Parse command line arguments
parser = argparse.ArgumentParser(description='Start a socket server and send .yuv420 files.')
parser.add_argument('camera', type=int, help='The camera number to use for the socket server.')
args = parser.parse_args()


# Clear existing data and port and start making new images
if args.camera == 0:
    subprocess.run(["python3", "CodeCase/freeport.py", "8888"], capture_output=False, text=False)
    image_dir = 'camera0data'
    port = 8888
    clear_folder(image_dir)
    subprocess.Popen(["rpicam-still", "--datetime", "-t", "0", "--camera", "0", "-e", "png", "-o", "camera0data", "--timelapse", "1000", "--width", "4056", "--height", "3040", "--denoise", "off", "--shutter", str(camera_settings['shutter']), "--awb", "cloudy"])
    
if args.camera == 1:
    subprocess.run(["python3", "CodeCase/freeport.py", "7777"], capture_output=False, text=False)
    image_dir = 'camera1data'
    port = 7777
    clear_folder(image_dir)
    subprocess.Popen(["rpicam-still", "--datetime", "-t", "0", "--camera", "1", "-e", "png", "-o", "camera1data", "--timelapse", "1000", "--width", "4056", "--height", "3040", "--denoise", "off",  "--shutter", str(camera_settings['shutter']), "--awb", "cloudy"])

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

# Continuously check the directory for new files
while True:
    # Check if the rpicam-still program is running
    if subprocess.run(['pgrep', '-x', 'rpicam-still'], stdout=subprocess.DEVNULL).returncode != 0:
        print('rpicam-still is no longer running. Stopping...')
        break

    # Get a sorted list of files
    filenames = sorted((filename for filename in os.listdir(image_dir) if filename.endswith('.png')))
    
    # Do not loop over filenames if there aren't at least 2 filenames
    if len(filenames) < 2:
        continue
        
    for filename in filenames:
    
        # Read the file as binary data
        with open(os.path.join(image_dir, filename), 'rb') as f:
            byte_array = f.read()

        if not is_png_complete(byte_array):
            continue
    
        byte_array += EOI_MARKER
        try:
            # Send the size of the img
            client_socket.send(struct.pack('!I', len(byte_array)))

            # Send metadata
            for metadata in camera_settings.values():
                client_socket.send(struct.pack('!I', metadata)) 
        
            # Send the byte array over the socket
            client_socket.send(byte_array)
            
        except (BrokenPipeError, ConnectionResetError):
            connection_error = True
            break
        
        os.remove(os.path.join(image_dir, filename))
    
        # Wait for a second before checking the directory again
        #time.sleep(1)
    
    if connection_error:
        # Close the sockets and kill rpicam-still
        print('Closing sockets, killing rpicam-still and clearing ports...')
        client_socket.close()
        server_socket.close()
        subprocess.run(['pkill', '-x', 'rpicam-still'])
        subprocess.Popen(["python3", "CodeCase/freeport.py", "8888"])
        subprocess.Popen(["python3", "CodeCase/freeport.py", "7777"])        
        break
        

