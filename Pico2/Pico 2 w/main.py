"""
Aurora Camera System - Pico W Servo Controller
Listens for commands from Pi Zero 2 W to control pan/tilt servos
"""

import network
import time
import socket
import json
from machine import Pin, SPI
import _thread
import utime
import math

# Import the Kitronik Pico Robotics library
class KitronikPicoRobotics:
    #Class variables - these should be the same for all instances of the class.
    # If you wanted to write some code that stepped through
    # the servos or motors then this is the Base and size to do that
    SRV_REG_BASE = 0x08
    MOT_REG_BASE = 0x28
    REG_OFFSET = 4
    PRESCALE_VAL = b'\x79'
    PI_ESTIMATE = 3.1416

    #setup the PCA chip for 50Hz and zero out registers.
    def initPCA(self):
        # Make sure we are in a known position
        # Soft reset of the I2C chip
        self.i2c.writeto(0,"\x06")

        # setup the prescale to have 20mS pulse repetition - this is dictated by the servos.
        # set PWM Frequency Pre Scale.  The prescale value is determined with the formunla:
        # presscale value = round(osc clock / (4096 * update rate))
        # Where update rate is the output modulation frequency required.
        # For example, the output frequency of 50Hz (20ms) for the servo, with the internal oscillator 
        # clock frequency of 25 Mhz is as follows:
        # prescale value = round( 25MHZ / (4096 * 50Hz) ) - 1 
        # prescale value = round (25000000 / (4096 * 50)) - 1 
        # presscale value = 121 = 79h = 0x79
        self.i2c.writeto_mem(108,0xfe,self.PRESCALE_VAL)

        #block write outputs to off
        self.i2c.writeto_mem(108,0xfa,"\x00")
        self.i2c.writeto_mem(108,0xfb,"\x00")
        self.i2c.writeto_mem(108,0xfc,"\x00")
        self.i2c.writeto_mem(108,0xfd,"\x00")
        
        # come out of sleep
        self.i2c.writeto_mem(108,0x00,"\x01")
        
        # It takes 500uS max for the oscillator to be up and running once the SLEEP bit (bit 4) has
        # been set to logic 0.  Timings on outputs are not guranteed if the PWM control registers are
        # accessed within the 500uS window.
        utime.sleep_us(500)
    
    # Adjusts the servos.
    # This block should be used if the connected servo does not respond correctly to the 'servoWrite' command.
    # Try changing the value by small amounts and testing the servo until it correctly sets to the angle.
    def adjustServos(self, change):
        if change < -25:
            change = -25
        if change > 25:
            change = 25
        self.PRESCALE_VAL = (121 + change).to_bytes(1,"big")
        self.initPCA()

    def servoWrite(self,servo, degrees):
        #check the degrees is a reasonable number. we expect 0-180, so cap at those values.
        if(degrees>180):
            degrees = 180
        elif (degrees<0):
            degrees = 0
        #check the servo number
        if((servo<1) or (servo>8)):
            raise Exception("INVALID SERVO NUMBER") #harsh, but at least you'll know
        calcServo = self.SRV_REG_BASE + ((servo - 1) * self.REG_OFFSET)
        PWMVal = int((degrees*2.2755)+102) # see comment above for maths
        lowByte = PWMVal & 0xFF
        highByte = (PWMVal>>8)&0x01 #cap high byte at 1 - shoud never be more than 2.5mS.
        self.i2c.writeto_mem(self.CHIP_ADDRESS, calcServo,bytes([lowByte]))
        self.i2c.writeto_mem(self.CHIP_ADDRESS, calcServo+1,bytes([highByte]))

    def motorOn(self,motor, direction, speed):
        #cap speed to 0-100%
        if (speed<0):
            speed = 0
        elif (speed>100):
            speed=100

        if((motor<1) or (motor>4)):
            raise Exception("INVALID MOTOR NUMBER") # harsh, but at least you'll know
            
        motorReg = self.MOT_REG_BASE + (2 * (motor - 1) * self.REG_OFFSET)
        PWMVal = int(speed * 40.95)
        lowByte = PWMVal & 0xFF
        highByte = (PWMVal>>8) & 0xFF #motors can use all 0-4096
        
        if direction == "f":
            self.i2c.writeto_mem(self.CHIP_ADDRESS, motorReg,bytes([lowByte]))
            self.i2c.writeto_mem(self.CHIP_ADDRESS, motorReg+1,bytes([highByte]))
            self.i2c.writeto_mem(self.CHIP_ADDRESS, motorReg+4,bytes([0]))
            self.i2c.writeto_mem(self.CHIP_ADDRESS, motorReg+5,bytes([0]))
        elif direction == "r":
            self.i2c.writeto_mem(self.CHIP_ADDRESS, motorReg+4,bytes([lowByte]))
            self.i2c.writeto_mem(self.CHIP_ADDRESS, motorReg+5,bytes([highByte]))
            self.i2c.writeto_mem(self.CHIP_ADDRESS, motorReg,bytes([0]))
            self.i2c.writeto_mem(self.CHIP_ADDRESS, motorReg+1,bytes([0]))
        else:
            self.i2c.writeto_mem(self.CHIP_ADDRESS, motorReg+4,bytes([0]))
            self.i2c.writeto_mem(self.CHIP_ADDRESS, motorReg+5,bytes([0]))
            self.i2c.writeto_mem(self.CHIP_ADDRESS, motorReg,bytes([0]))
            self.i2c.writeto_mem(self.CHIP_ADDRESS, motorReg+1,bytes([0]))
            raise Exception("INVALID DIRECTION")
    
    def motorOff(self,motor):
        self.motorOn(motor,"f",0)

    def __init__(self, I2CAddress=108,sda=8,scl=9):
        import machine
        self.CHIP_ADDRESS = 108
        sda=machine.Pin(sda)
        scl=machine.Pin(scl)
        self.i2c=machine.I2C(0,sda=sda, scl=scl, freq=100000)
        self.initPCA()

# WiFi Configuration
WIFI_SSID = "SC2025"
WIFI_PASSWORD = "april202025"

# Servo Configuration - Using Kitronik Robotics Board
SERVO_PAN_CHANNEL = 1     # Pan servo on robotics board channel 1
SERVO_TILT_CHANNEL = 2    # Tilt servo on robotics board channel 2

# Communication Configuration
LISTEN_PORT = 8888         # Port to listen for Pi Zero commands
PI_ZERO_IP = "192.168.1.166"  # Pi Zero 2 W static IP address

# Servo limits (in degrees)
PAN_MIN, PAN_MAX = -90, 90      # Full 180Â° range for pan servo
TILT_MIN, TILT_MAX = -30, 30    # Limited 60Â° range for tilt servo (30Â° up/down)

# Current servo positions
current_pan = 0
current_tilt = 0

# Simple 5x7 font for displaying numbers and letters
FONT_5x7 = {
    '0': [0x3E, 0x51, 0x49, 0x45, 0x3E],
    '1': [0x00, 0x42, 0x7F, 0x40, 0x00],
    '2': [0x42, 0x61, 0x51, 0x49, 0x46],
    '3': [0x21, 0x41, 0x45, 0x4B, 0x31],
    '4': [0x18, 0x14, 0x12, 0x7F, 0x10],
    '5': [0x27, 0x45, 0x45, 0x45, 0x39],
    '6': [0x3C, 0x4A, 0x49, 0x49, 0x30],
    '7': [0x01, 0x71, 0x09, 0x05, 0x03],
    '8': [0x36, 0x49, 0x49, 0x49, 0x36],
    '9': [0x06, 0x49, 0x49, 0x29, 0x1E],
    '.': [0x00, 0x60, 0x60, 0x00, 0x00],
    ':': [0x00, 0x36, 0x36, 0x00, 0x00],
    ' ': [0x00, 0x00, 0x00, 0x00, 0x00],
    'A': [0x7E, 0x11, 0x11, 0x11, 0x7E],
    'B': [0x7F, 0x49, 0x49, 0x49, 0x36],
    'C': [0x3E, 0x41, 0x41, 0x41, 0x22],
    'D': [0x7F, 0x41, 0x41, 0x22, 0x1C],
    'E': [0x7F, 0x49, 0x49, 0x49, 0x41],
    'F': [0x7F, 0x09, 0x09, 0x09, 0x01],
    'G': [0x3E, 0x41, 0x49, 0x49, 0x7A],
    'H': [0x7F, 0x08, 0x08, 0x08, 0x7F],
    'I': [0x00, 0x41, 0x7F, 0x41, 0x00],
    'L': [0x7F, 0x40, 0x40, 0x40, 0x40],
    'N': [0x7F, 0x04, 0x08, 0x10, 0x7F],
    'O': [0x3E, 0x41, 0x41, 0x41, 0x3E],
    'P': [0x7F, 0x09, 0x09, 0x09, 0x06],
    'R': [0x7F, 0x09, 0x19, 0x29, 0x46],
    'S': [0x46, 0x49, 0x49, 0x49, 0x31],
    'T': [0x01, 0x01, 0x7F, 0x01, 0x01],
    'U': [0x3F, 0x40, 0x40, 0x40, 0x3F],
    'V': [0x1F, 0x20, 0x40, 0x20, 0x1F],
    '+': [0x08, 0x08, 0x3E, 0x08, 0x08],
    '-': [0x08, 0x08, 0x08, 0x08, 0x08],
}

class TextDisplay:
    def __init__(self, spi, width, height, reset, cs, dc, backlight):
        self.spi = spi
        # Swap width/height for 90-degree rotation
        self.width = height   # 320 (landscape width)
        self.height = width   # 240 (landscape height)
        self.reset = reset
        self.cs = cs  
        self.dc = dc
        self.backlight = backlight
        
        # Colors (RGB565 format)
        self.BLACK = 0x0000
        self.WHITE = 0xFFFF
        self.RED = 0xF800
        self.GREEN = 0x07E0
        self.BLUE = 0x001F
        self.YELLOW = 0xFFE0
        self.CYAN = 0x07FF
        self.MAGENTA = 0xF81F
        
        # Initialize pins
        self.reset.value(1)
        self.cs.value(1)
        self.dc.value(1)
        self.backlight.value(1)  # Turn on backlight
        
    def write_cmd(self, cmd):
        self.cs.value(1)
        self.dc.value(0)  # Command mode
        self.cs.value(0)
        self.spi.write(bytearray([cmd]))
        self.cs.value(1)
        
    def write_data(self, data):
        self.cs.value(1)
        self.dc.value(1)  # Data mode  
        self.cs.value(0)
        if isinstance(data, int):
            self.spi.write(bytearray([data]))
        else:
            self.spi.write(data)
        self.cs.value(1)
        
    def init_display(self):
        # Reset sequence
        self.reset.value(1)
        time.sleep_ms(100)
        self.reset.value(0)
        time.sleep_ms(100)
        self.reset.value(1)
        time.sleep_ms(100)
        
        # Initialize ST7789
        self.write_cmd(0x01)  # Software reset
        time.sleep_ms(150)
        
        self.write_cmd(0x11)  # Sleep out
        time.sleep_ms(120)
        
        self.write_cmd(0x3A)  # Color mode
        self.write_data(0x05)  # 16-bit color
        
        self.write_cmd(0x36)  # Memory access control
        self.write_data(0x60)  # Rotate 90 degrees (landscape mode)
        
        self.write_cmd(0x2A)  # Column address set
        self.write_data(0x00)
        self.write_data(0x00) 
        self.write_data(0x01)
        self.write_data(0x3F)  # 319 (rotated width)
        
        self.write_cmd(0x2B)  # Row address set
        self.write_data(0x00)
        self.write_data(0x00)
        self.write_data(0x00)
        self.write_data(0xEF)  # 239 (rotated height)
        
        self.write_cmd(0x21)  # Inversion on
        self.write_cmd(0x29)  # Display on
        time.sleep_ms(100)
        
    def fill_screen(self, color):
        # Set full screen window
        self.write_cmd(0x2A)  # Column address
        self.write_data(0x00)
        self.write_data(0x00)
        self.write_data(0x01)
        self.write_data(0x3F)  # 319 (rotated)
        
        self.write_cmd(0x2B)  # Row address
        self.write_data(0x00)
        self.write_data(0x00)
        self.write_data(0x00)
        self.write_data(0xEF)  # 239 (rotated)
        
        self.write_cmd(0x2C)  # Memory write
        
        # Send color data
        color_bytes = bytearray([color >> 8, color & 0xFF])
        self.cs.value(1)
        self.dc.value(1)
        self.cs.value(0)
        
        for _ in range(self.width * self.height):
            self.spi.write(color_bytes)
        self.cs.value(1)
        
    def draw_section(self, x, y, width, height, color):
        # Set window
        self.write_cmd(0x2A)  # Column address
        self.write_data(x >> 8)
        self.write_data(x & 0xFF)
        self.write_data((x + width - 1) >> 8)
        self.write_data((x + width - 1) & 0xFF)
        
        self.write_cmd(0x2B)  # Row address  
        self.write_data(y >> 8)
        self.write_data(y & 0xFF)
        self.write_data((y + height - 1) >> 8)
        self.write_data((y + height - 1) & 0xFF)
        
        self.write_cmd(0x2C)  # Memory write
        
        # Fill area with color
        color_bytes = bytearray([color >> 8, color & 0xFF])
        self.cs.value(1)
        self.dc.value(1)  
        self.cs.value(0)
        
        for _ in range(width * height):
            self.spi.write(color_bytes)
        self.cs.value(1)
    
    def draw_pixel(self, x, y, color):
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return
            
        self.write_cmd(0x2A)  # Column address
        self.write_data(x >> 8)
        self.write_data(x & 0xFF)
        self.write_data(x >> 8)
        self.write_data(x & 0xFF)
        
        self.write_cmd(0x2B)  # Row address
        self.write_data(y >> 8)
        self.write_data(y & 0xFF)
        self.write_data(y >> 8)
        self.write_data(y & 0xFF)
        
        self.write_cmd(0x2C)  # Memory write
        self.write_data(color >> 8)
        self.write_data(color & 0xFF)
    
    def draw_char(self, char, x, y, color, scale=2):
        """Draw a character using the 5x7 font"""
        char = char.upper()
        if char not in FONT_5x7:
            char = ' '
            
        pattern = FONT_5x7[char]
        
        for col in range(5):
            col_data = pattern[col]
            for row in range(7):
                if col_data & (1 << row):
                    # Draw scaled pixel
                    for sx in range(scale):
                        for sy in range(scale):
                            self.draw_pixel(x + col*scale + sx, y + row*scale + sy, color)
    
    def draw_text(self, text, x, y, color, scale=2):
        """Draw text string"""
        current_x = x
        for char in text:
            self.draw_char(char, current_x, y, color, scale)
            current_x += 6 * scale  # Character width + spacing

class ServoController:
    def __init__(self, pan_channel, tilt_channel):
        # Initialize Kitronik Robotics Board
        self.robotics_board = KitronikPicoRobotics()
        self.pan_channel = pan_channel
        self.tilt_channel = tilt_channel
        
        # Center both servos
        self.set_position(0, 0)
        print("ðŸ¤– Kitronik Robotics Board initialized")
        
    def angle_to_servo_degrees(self, angle):
        """Convert angle (-90 to 90) to servo degrees (0 to 180)"""
        # Map -90 to 90 degrees to 0 to 180 degrees for servo
        return int(angle + 90)
    
    def set_position(self, pan_angle, tilt_angle):
        """Set servo positions with safety limits"""
        global current_pan, current_tilt
        
        # Apply limits
        pan_angle = max(PAN_MIN, min(PAN_MAX, pan_angle))
        tilt_angle = max(TILT_MIN, min(TILT_MAX, tilt_angle))
        
        # Convert to servo degrees (0-180)
        pan_servo_deg = self.angle_to_servo_degrees(pan_angle)
        tilt_servo_deg = self.angle_to_servo_degrees(tilt_angle)
        
        # Set servo positions using Kitronik board
        try:
            self.robotics_board.servoWrite(self.pan_channel, pan_servo_deg)
            self.robotics_board.servoWrite(self.tilt_channel, tilt_servo_deg)
            
            current_pan = pan_angle
            current_tilt = tilt_angle
            
            print(f"ðŸŽ¯ Servos positioned: Pan={pan_angle}Â° (servo:{pan_servo_deg}Â°), Tilt={tilt_angle}Â° (servo:{tilt_servo_deg}Â°)")
            return True
        except Exception as e:
            print(f"âŒ Servo error: {e}")
            return False
    
    def smooth_move(self, target_pan, target_tilt, steps=8, delay_ms=15):
        """Smooth movement to target position"""
        start_pan, start_tilt = current_pan, current_tilt
        
        for i in range(steps + 1):
            progress = i / steps
            # Use easing function for smoother acceleration/deceleration
            eased_progress = 0.5 * (1 - math.cos(progress * 3.14159))
            
            pan = start_pan + (target_pan - start_pan) * eased_progress
            tilt = start_tilt + (target_tilt - start_tilt) * eased_progress
            
            self.set_position(pan, tilt)
            time.sleep_ms(delay_ms)
    
    def sweep_pattern(self):
        """Demo sweep pattern"""
        positions = [
            (0, 0),      # Center
            (-45, 0),    # Left
            (45, 0),     # Right
            (0, 0),      # Center
            (0, -20),    # Down
            (0, 20),     # Up
            (0, 0)       # Center
        ]
        
        for pan, tilt in positions:
            self.smooth_move(pan, tilt, steps=30, delay_ms=20)
            time.sleep_ms(300)

class CommandListener:
    def __init__(self, servo_controller, port=8888):
        self.servo_controller = servo_controller
        self.port = port
        self.socket = None
        self.running = False
        
    def start_listening(self):
        """Start listening for commands"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind(('', self.port))
            self.socket.listen(5)
            self.running = True
            
            print(f"ðŸŽ§ Aurora servo listener started on port {self.port}")
            return True
        except Exception as e:
            print(f"âŒ Failed to start listener: {e}")
            return False
    
    def handle_command(self, command_data):
        """Process incoming commands from Pi Zero"""
        try:
            cmd = json.loads(command_data)
            command_type = cmd.get('command', '')
            
            if command_type == 'move':
                pan = cmd.get('pan', current_pan)
                tilt = cmd.get('tilt', current_tilt)
                smooth = cmd.get('smooth', False)
                
                if smooth:
                    self.servo_controller.smooth_move(pan, tilt)
                else:
                    self.servo_controller.set_position(pan, tilt)
                
                return {'status': 'success', 'pan': current_pan, 'tilt': current_tilt}
            
            elif command_type == 'get_position':
                return {'status': 'success', 'pan': current_pan, 'tilt': current_tilt}
            
            elif command_type == 'sweep':
                self.servo_controller.sweep_pattern()
                return {'status': 'success', 'message': 'sweep completed'}
            
            elif command_type == 'center':
                self.servo_controller.smooth_move(0, 0)
                return {'status': 'success', 'message': 'centered'}
            
            elif command_type == 'wake_response':
                # Aurora wake word detected - acknowledge
                print("ðŸŒ… Aurora wake word detected!")
                # Quick acknowledgment movement
                self.servo_controller.set_position(current_pan + 5, current_tilt)
                time.sleep_ms(100)
                self.servo_controller.set_position(current_pan - 5, current_tilt)
                return {'status': 'success', 'message': 'aurora acknowledged'}
            
            else:
                return {'status': 'error', 'message': f'unknown command: {command_type}'}
                
        except Exception as e:
            print(f"âŒ Command handling error: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def listen_loop(self):
        """Raw JSON-over-TCP listener with guaranteed JSON replies"""
        while self.running:
            try:
                conn, addr = self.socket.accept()
                conn.settimeout(2.0)
                data = conn.recv(1024).decode('utf-8')
                if not data:
                    conn.close()
                    continue

                try:
                    response = self.handle_command(data)
                except Exception as e:
                    response = {"status": "error", "error": str(e)}

                conn.send(json.dumps(response).encode())
                conn.close()

            except OSError as e:
                # Treat accept() timeouts as normal idle
                if hasattr(e, 'args') and e.args and e.args[0] == 110:
                    continue
                if self.running:
                    print(f"✗ Listener error: {e}")
                time.sleep(1)

            except Exception as e:
                if self.running:
                    print(f"✗ Listener error: {e}")
                time.sleep(1)


def connect_wifi():
    """Connect to WiFi"""
    print("Initializing WiFi...")
    onboard_led = Pin("LED", Pin.OUT)
    
    # Add small delay to let power stabilize
    time.sleep(2)
    
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    # Wait for WiFi to fully activate
    time.sleep(1)
    
    if wlan.isconnected():
        print("Already connected")
        return wlan
        
    print(f"Connecting to: {WIFI_SSID}")
    
    # Try to connect with more attempts
    for attempt in range(3):
        print(f"Connection attempt {attempt + 1}/3")
        
        try:
            wlan.connect(WIFI_SSID, WIFI_PASSWORD)
            
            # Wait for connection with more time
            connect_attempts = 0
            while not wlan.isconnected() and connect_attempts < 30:
                print(f"  Connecting... {connect_attempts}")
                onboard_led.value(1)
                time.sleep_ms(250)
                onboard_led.value(0)
                time.sleep_ms(250)
                connect_attempts += 1
                
            if wlan.isconnected():
                print(f"âœ… Connected on attempt {attempt + 1}!")
            # Add network diagnostics
                print("=== Network Diagnostics ===")
                print(f"Network config: {wlan.ifconfig()}")
                print(f"Active: {wlan.active()}")  
                print(f"Connected: {wlan.isconnected()}")
                print(f"Status: {wlan.status()}")
                onboard_led.value(1)
                return wlan
            else:
                print(f"âŒ Attempt {attempt + 1} failed")
                wlan.disconnect()
                time.sleep(2)
                
        except Exception as e:
            print(f"âŒ Connection error on attempt {attempt + 1}: {e}")
            time.sleep(2)
    
    print("âŒ All connection attempts failed")
    onboard_led.value(0)
    return None

def update_display_with_aurora_status(display, wlan, listener_active=False):
    """Update display to show Aurora system status"""
    if not wlan or not wlan.isconnected():
        return
        
    ip_address = wlan.ifconfig()[0]
    
    # Clear and setup display
    display.init_display()
    display.fill_screen(display.BLACK)
    
    # Status sections (adjusted for landscape 320x240)
    display.draw_section(10, 10, 300, 40, display.GREEN)    # Aurora Status
    display.draw_section(10, 60, 300, 35, display.BLUE)     # Network
    display.draw_section(10, 105, 300, 35, display.MAGENTA) # Servo Status
    display.draw_section(10, 150, 300, 35, display.CYAN)    # Listener Status
    display.draw_section(10, 195, 300, 35, display.YELLOW)  # Current Position
    
    # Text content - bigger text sizes
    display.draw_text("AURORA SERVO", 20, 20, display.WHITE, 2)
    display.draw_text("CONTROLLER", 20, 35, display.WHITE, 1)
    
    display.draw_text("IP: " + ip_address, 20, 70, display.WHITE, 2)
    
    display.draw_text("SERVOS READY", 20, 115, display.WHITE, 2)
    
    if listener_active:
        display.draw_text("LISTENING :8888", 20, 160, display.WHITE, 2)
    else:
        display.draw_text("OFFLINE", 20, 160, display.RED, 2)
    
    display.draw_text(f"P:{current_pan:+3.0f} T:{current_tilt:+3.0f}", 20, 205, display.BLACK, 2)

def main():
    """Aurora Camera System - Servo Controller"""
    print("ðŸŒ… Starting Aurora Camera Servo Controller...")
    print(f"ðŸ”‹ Power source: Kitronik Robotics Board")
    
    # Initialize hardware
    onboard_led = Pin("LED", Pin.OUT)
    
    # Power stabilization delay
    print("â³ Waiting for power to stabilize...")
    time.sleep(3)
    
    # Initialize display
    print("ðŸ“± Initializing display...")
    spi = SPI(0, baudrate=40000000, sck=Pin(6), mosi=Pin(7))
    display = TextDisplay(
        spi=spi, width=240, height=320,
        reset=Pin(3, Pin.OUT), cs=Pin(5, Pin.OUT),
        dc=Pin(4, Pin.OUT), backlight=Pin(2, Pin.OUT)
    )
    
    # Show startup screen
    display.init_display()
    display.fill_screen(display.BLUE)
    display.draw_text("AURORA", 100, 100, display.WHITE, 4)
    display.draw_text("STARTING...", 80, 140, display.YELLOW, 2)
    
    # Connect to WiFi with better error handling
    print("ðŸŒ Starting WiFi connection...")
    wlan = connect_wifi()
    # After wlan.connect(), before checking if connected:
    wlan.ifconfig(('192.168.1.250', '255.255.255.0', '192.168.1.1', '192.168.1.1'))
    if not (wlan and wlan.isconnected()):
        print("âŒ WiFi connection failed - showing error screen")
        display.fill_screen(display.RED)
        display.draw_text("WIFI FAILED", 60, 80, display.WHITE, 3)
        display.draw_text("CHECK POWER", 50, 120, display.YELLOW, 2)
        display.draw_text("& NETWORK", 60, 140, display.YELLOW, 2)
        
        # Error blink pattern
        while True:
            for _ in range(5):
                onboard_led.value(1)
                time.sleep_ms(200)
                onboard_led.value(0)  
                time.sleep_ms(200)
            time.sleep(3)
    
    print(f"âœ… Connected! IP: {wlan.ifconfig()[0]}")   
    
    # Initialize servo controller (after WiFi to ensure stable power)
    print("ðŸ”§ Initializing servos...")
    try:
        servo_controller = ServoController(SERVO_PAN_CHANNEL, SERVO_TILT_CHANNEL)
    except Exception as e:
        print(f"âŒ Servo initialization failed: {e}")
        display.fill_screen(display.RED)
        display.draw_text("SERVO ERROR", 60, 100, display.WHITE, 3)
        return
    
    # Startup demo
    print("ðŸŽ¯ Running startup demo...")
    servo_controller.sweep_pattern()
    
    # Start command listener
    print("ðŸŽ§ Starting command listener...")
    listener = CommandListener(servo_controller)
    
    if listener.start_listening():
        # Start listener in background thread
        _thread.start_new_thread(listener.listen_loop, ())
        
        # Update display
        update_display_with_aurora_status(display, wlan, True)
        
        print("ðŸŒ… Aurora Servo Controller ready!")
        print(f"ðŸ“¡ Listening on {wlan.ifconfig()[0]}:8888")
        print("ðŸ’¬ Waiting for commands from Pi Zero 2 W...")
        
        # Main loop - monitor connection and update display
        while True:
            if wlan.isconnected():
               # Only update display every 20 iterations (about 100 seconds)
               display_counter += 1
            if display_counter >= 20:
                display.draw_section(10, 195, 300, 35, display.YELLOW)
                display.draw_text(f"P:{current_pan:+3.0f} T:{current_tilt:+3.0f}", 20, 205, display.BLACK, 2)
                display_counter = 0 
                
                # Status blink
                onboard_led.value(1)
                time.sleep(0.1)
                onboard_led.value(0)
                time.sleep(4.9)
            else:
                print("âŒ WiFi connection lost!")
                display.fill_screen(display.RED)
                display.draw_text("CONNECTION LOST", 40, 100, display.WHITE, 2)
                break
    
    else:
        display.fill_screen(display.RED)
        display.draw_text("LISTENER FAILED", 30, 100, display.WHITE, 2)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nðŸ›‘ Aurora servo controller stopped")
        Pin("LED", Pin.OUT).value(0)
    except Exception as e:
        print(f"ðŸ’¥ Error: {e}")
        Pin("LED", Pin.OUT).value(0)
