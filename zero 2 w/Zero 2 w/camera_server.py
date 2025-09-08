#!/usr/bin/env python3
"""
Pi Zero 2 W Camera Web Server with Pan/Tilt Controls
Streams video from Pi Camera Module 3 and provides web interface for servo control
"""

from flask import Flask, render_template, Response, jsonify, request
from picamera2 import Picamera2
import socket
import json
import io
import threading
import time

app = Flask(__name__)

# Configuration - UPDATE THIS WITH YOUR PICO'S IP
PICO_IP = "192.168.1.250"  # Replace with your Pico's actual IP
PICO_PORT = 8888
STREAM_WIDTH = 640
STREAM_HEIGHT = 480
STREAM_FPS = 30

# Current servo positions (tracking for smooth moves)
current_pan = 0
current_tilt = 0

# Movement step size for directional commands
STEP_SIZE = 10

class CameraStreamer:
    def __init__(self):
        self.picam2 = None
        self.output = None
        self.streaming = False
        self.setup_camera()
    
    def setup_camera(self):
        """Initialize the camera with optimal settings for streaming"""
        try:
            self.picam2 = Picamera2()
            
            # Configure camera for streaming
            config = self.picam2.create_video_configuration(
                main={"size": (STREAM_WIDTH, STREAM_HEIGHT), "format": "RGB888"},
                lores={"size": (320, 240), "format": "YUV420"}
            )
            self.picam2.configure(config)
            
            # Set frame rate
            self.picam2.set_controls({"FrameRate": STREAM_FPS})
            
            print(f"Camera initialized: {STREAM_WIDTH}x{STREAM_HEIGHT} @ {STREAM_FPS}fps")
            
        except Exception as e:
            print(f"Camera initialization error: {e}")
            self.picam2 = None
    
    def start_streaming(self):
        """Start the camera streaming"""
        if self.picam2 and not self.streaming:
            try:
                self.picam2.start()
                self.streaming = True
                print("Camera streaming started")
            except Exception as e:
                print(f"Failed to start camera: {e}")
    
    def stop_streaming(self):
        """Stop the camera streaming"""
        if self.picam2 and self.streaming:
            try:
                self.picam2.stop()
                self.streaming = False
                print("Camera streaming stopped")
            except Exception as e:
                print(f"Failed to stop camera: {e}")
    
    def get_frame(self):
        """Get the latest frame as JPEG bytes"""
        if not self.picam2 or not self.streaming:
            return None
        
        try:
            # Capture frame to memory buffer
            stream = io.BytesIO()
            self.picam2.capture_file(stream, format='jpeg')
            stream.seek(0)
            return stream.getvalue()
        except Exception as e:
            print(f"Frame capture error: {e}")
            return None

# Global camera instance
camera = CameraStreamer()

def get_current_position():
    """Get current servo position from Pico"""
    global current_pan, current_tilt
    try:
        print(f"Connecting to Pico at {PICO_IP}:{PICO_PORT}...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        sock.connect((PICO_IP, PICO_PORT))
        
        cmd = json.dumps({"command": "get_position"})
        sock.send(cmd.encode())
        
        response = sock.recv(1024).decode()
        sock.close()
        
        result = json.loads(response)
        if result.get('status') == 'success':
            current_pan = result.get('pan', 0)
            current_tilt = result.get('tilt', 0)
            print(f"✅ Got current position: Pan={current_pan}°, Tilt={current_tilt}°")
            return True
    except Exception as e:
        print(f"⚠️  Could not get current position from Pico: {e}")
        print("    Using default positions (Pan=0°, Tilt=0°)")
    return False

def send_servo_command(command, pan=None, tilt=None, smooth=False):
    """Send command to Pico servo controller via TCP socket"""
    try:
        # Create socket connection
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        sock.connect((PICO_IP, PICO_PORT))
        
        # Prepare command based on your Pico's expected format
        if command == 'move':
            cmd_data = {
                "command": "move",
                "pan": pan if pan is not None else current_pan,
                "tilt": tilt if tilt is not None else current_tilt,
                "smooth": smooth
            }
        elif command == 'center':
            cmd_data = {"command": "center"}
        elif command == 'get_position':
            cmd_data = {"command": "get_position"}
        else:
            cmd_data = {"command": command}
        
        # Send command
        message = json.dumps(cmd_data)
        sock.send(message.encode())
        
        # Receive response
        response = sock.recv(1024).decode()
        sock.close()
        
        result = json.loads(response)
        return result.get('status') == 'success'
        
    except Exception as e:
        print(f"Servo command error: {e}")
        return False

def generate_frames():
    """Generator function for video streaming"""
    while True:
        frame = camera.get_frame()
        if frame:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        time.sleep(1.0 / STREAM_FPS)

@app.route('/')
def index():
    """Main web interface"""
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    """Video streaming route"""
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/control', methods=['POST'])
def control():
    """Handle servo control commands"""
    global current_pan, current_tilt
    
    data = request.get_json()
    command = data.get('command')
    value = data.get('value')
    
    # Handle different command types
    if command in ['up', 'down', 'left', 'right']:
        # Directional movements
        new_pan, new_tilt = current_pan, current_tilt
        
        if command == 'up':
            new_tilt = max(-30, current_tilt - STEP_SIZE)  # Tilt limits from your Pico code
        elif command == 'down':
            new_tilt = min(30, current_tilt + STEP_SIZE)
        elif command == 'left':
            new_pan = max(-90, current_pan - STEP_SIZE)    # Pan limits from your Pico code
        elif command == 'right':
            new_pan = min(90, current_pan + STEP_SIZE)
        
        if send_servo_command('move', pan=new_pan, tilt=new_tilt, smooth=True):
            current_pan, current_tilt = new_pan, new_tilt
            return jsonify({"status": "success", "pan": current_pan, "tilt": current_tilt})
    
    elif command == 'pan' and value is not None:
        # Absolute pan positioning
        new_pan = max(-90, min(90, value - 90))  # Convert slider (0-180) to angle (-90 to 90)
        if send_servo_command('move', pan=new_pan, tilt=current_tilt, smooth=True):
            current_pan = new_pan
            return jsonify({"status": "success", "pan": current_pan, "tilt": current_tilt})
    
    elif command == 'tilt' and value is not None:
        # Absolute tilt positioning  
        new_tilt = max(-30, min(30, value - 90))  # Convert slider (0-180) to angle (-30 to 30)
        if send_servo_command('move', pan=current_pan, tilt=new_tilt, smooth=True):
            current_tilt = new_tilt
            return jsonify({"status": "success", "pan": current_pan, "tilt": current_tilt})
    
    return jsonify({"status": "error", "message": "Invalid command"}), 500

@app.route('/center', methods=['POST'])
def center():
    """Center both servos"""
    global current_pan, current_tilt
    
    if send_servo_command('center'):
        current_pan, current_tilt = 0, 0
        return jsonify({"status": "success", "pan": 0, "tilt": 0})
    else:
        return jsonify({"status": "error"}), 500

@app.route('/status')
def status():
    """Get camera and servo status"""
    return jsonify({
        "streaming": camera.streaming,
        "pico_ip": PICO_IP,
        "resolution": f"{STREAM_WIDTH}x{STREAM_HEIGHT}",
        "fps": STREAM_FPS,
        "current_pan": current_pan,
        "current_tilt": current_tilt
    })

if __name__ == '__main__':
    # Start camera streaming first
    camera.start_streaming()
    
    # Get initial servo position (with better error handling)
    print("Getting initial servo position...")
    get_current_position()
    
    try:
        # Start Flask web server
        print("Starting camera web server...")
        print(f"Servo controller at: {PICO_IP}:{PICO_PORT}")
        print(f"Current servo position: Pan={current_pan}°, Tilt={current_tilt}°")
        print(f"Web interface will be available at: http://{socket.gethostname()}.local:5000")
        print("Press Ctrl+C to stop")
        
        app.run(host='0.0.0.0', port=5000, threaded=True, debug=False)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        camera.stop_streaming()
