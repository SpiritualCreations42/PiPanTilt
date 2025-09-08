#!/usr/bin/env python3
"""
2-inch LCD Rolling Hello Display Script
For Waveshare 2-inch LCD (ST7789V) with SunFounder Robot HAT v4
Custom pin configuration: DC=GPIO2, RST=GPIO3, BL=GPIO6
"""

import time
import spidev
import RPi.GPIO as GPIO
from PIL import Image, ImageDraw, ImageFont
import numpy as np

# Custom pin configuration for Robot HAT v4
RST_PIN = 3   # Reset pin
DC_PIN = 2    # Data/Command pin  
BL_PIN = 6    # Backlight pin
CS_PIN = 8    # Chip Select (SPI CS)

# LCD dimensions
LCD_WIDTH = 240
LCD_HEIGHT = 320

# Colors (RGB565 format)
BLACK = 0x0000
WHITE = 0xFFFF
RED = 0xF800
GREEN = 0x07E0
BLUE = 0x001F
YELLOW = 0xFFE0
MAGENTA = 0xF81F
CYAN = 0x07FF

class LCD_2inch:
    def __init__(self):
        self.width = LCD_WIDTH
        self.height = LCD_HEIGHT
        
        # Initialize GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(RST_PIN, GPIO.OUT)
        GPIO.setup(DC_PIN, GPIO.OUT)
        GPIO.setup(BL_PIN, GPIO.OUT)
        GPIO.setup(CS_PIN, GPIO.OUT)
        
        # Initialize SPI
        self.spi = spidev.SpiDev(0, 0)  # SPI bus 0, device 0
        self.spi.max_speed_hz = 40000000  # 40MHz
        self.spi.mode = 0
        
        # Turn on backlight
        GPIO.output(BL_PIN, GPIO.HIGH)
        
        # Initialize LCD
        self.init_lcd()
    
    def digital_write(self, pin, value):
        GPIO.output(pin, value)
    
    def spi_writebyte(self, data):
        if isinstance(data, list):
            self.spi.writebytes(data)
        else:
            self.spi.writebytes([data])
    
    def write_cmd(self, cmd):
        self.digital_write(DC_PIN, GPIO.LOW)
        self.digital_write(CS_PIN, GPIO.LOW)
        self.spi_writebyte(cmd)
        self.digital_write(CS_PIN, GPIO.HIGH)
    
    def write_data(self, data):
        self.digital_write(DC_PIN, GPIO.HIGH)
        self.digital_write(CS_PIN, GPIO.LOW)
        if isinstance(data, list):
            self.spi_writebyte(data)
        else:
            self.spi_writebyte(data)
        self.digital_write(CS_PIN, GPIO.HIGH)
    
    def init_lcd(self):
        """Initialize the ST7789V LCD controller"""
        # Reset
        self.digital_write(RST_PIN, GPIO.HIGH)
        time.sleep(0.01)
        self.digital_write(RST_PIN, GPIO.LOW)
        time.sleep(0.01)
        self.digital_write(RST_PIN, GPIO.HIGH)
        time.sleep(0.05)
        
        # ST7789V initialization sequence
        self.write_cmd(0x36)    # Memory Data Access Control
        self.write_data(0x00)   # Normal display
        
        self.write_cmd(0x3A)    # Interface Pixel Format
        self.write_data(0x05)   # 16-bit color
        
        self.write_cmd(0xB2)    # Porch Setting
        self.write_data([0x0C, 0x0C, 0x00, 0x33, 0x33])
        
        self.write_cmd(0xB7)    # Gate Control
        self.write_data(0x35)
        
        self.write_cmd(0xBB)    # VCOM Setting
        self.write_data(0x19)
        
        self.write_cmd(0xC0)    # LCM Control
        self.write_data(0x2C)
        
        self.write_cmd(0xC2)    # VDV and VRH Command Enable
        self.write_data(0x01)
        
        self.write_cmd(0xC3)    # VRH Set
        self.write_data(0x12)
        
        self.write_cmd(0xC4)    # VDV Set
        self.write_data(0x20)
        
        self.write_cmd(0xC6)    # Frame Rate Control in Normal Mode
        self.write_data(0x0F)
        
        self.write_cmd(0xD0)    # Power Control 1
        self.write_data([0xA4, 0xA1])
        
        self.write_cmd(0xE0)    # Positive Voltage Gamma Control
        self.write_data([0xD0, 0x04, 0x0D, 0x11, 0x13, 0x2B, 0x3F, 0x54, 
                        0x4C, 0x18, 0x0D, 0x0B, 0x1F, 0x23])
        
        self.write_cmd(0xE1)    # Negative Voltage Gamma Control
        self.write_data([0xD0, 0x04, 0x0C, 0x11, 0x13, 0x2C, 0x3F, 0x44, 
                        0x51, 0x2F, 0x1F, 0x1F, 0x20, 0x23])
        
        self.write_cmd(0x21)    # Inversion On
        self.write_cmd(0x11)    # Sleep Out
        time.sleep(0.05)
        self.write_cmd(0x29)    # Display On
        time.sleep(0.05)
    
    def set_window(self, x_start, y_start, x_end, y_end):
        """Set display window"""
        self.write_cmd(0x2A)    # Column Address Set
        self.write_data([0x00, x_start, 0x00, x_end])
        
        self.write_cmd(0x2B)    # Row Address Set
        self.write_data([0x00, y_start, 0x00, y_end])
        
        self.write_cmd(0x2C)    # Memory Write
    
    def show_image(self, image):
        """Display PIL image on LCD"""
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Resize image to fit LCD
        image = image.resize((self.width, self.height), Image.LANCZOS)
        
        # Convert to numpy array
        img_array = np.array(image)
        
        # Convert RGB888 to RGB565
        r = (img_array[:,:,0] >> 3) << 11
        g = (img_array[:,:,1] >> 2) << 5
        b = img_array[:,:,2] >> 3
        rgb565 = r | g | b
        
        # Set display window
        self.set_window(0, 0, self.width - 1, self.height - 1)
        
        # Convert to bytes and send
        self.digital_write(DC_PIN, GPIO.HIGH)
        self.digital_write(CS_PIN, GPIO.LOW)
        
        # Send pixel data
        for row in rgb565:
            for pixel in row:
                self.spi_writebyte([(pixel >> 8) & 0xFF, pixel & 0xFF])
        
        self.digital_write(CS_PIN, GPIO.HIGH)
    
    def clear(self, color=BLACK):
        """Clear screen with specified color"""
        image = Image.new('RGB', (self.width, self.height), 
                         ((color >> 11) << 3, ((color >> 5) & 0x3F) << 2, (color & 0x1F) << 3))
        self.show_image(image)
    
    def cleanup(self):
        """Clean up GPIO and SPI"""
        self.digital_write(BL_PIN, GPIO.LOW)  # Turn off backlight
        self.spi.close()
        GPIO.cleanup()

def create_rolling_text_image(text, position, width, height, font_size=32, text_color=(255, 255, 255), bg_color=(0, 0, 0)):
    """Create an image with rolling text"""
    # Create image
    image = Image.new('RGB', (width, height), bg_color)
    draw = ImageDraw.Draw(image)
    
    # Try to load a font, fall back to default if not available
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
    except:
        font = ImageFont.load_default()
    
    # Get text dimensions
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Calculate y position to center vertically
    y = (height - text_height) // 2
    
    # Draw text at specified x position
    draw.text((position, y), text, font=font, fill=text_color)
    
    return image, text_width

def main():
    """Main rolling hello demo"""
    print("Starting 2-inch LCD Rolling Hello Demo...")
    print("Pin Configuration:")
    print(f"  RST: GPIO{RST_PIN}")
    print(f"  DC:  GPIO{DC_PIN}")
    print(f"  BL:  GPIO{BL_PIN}")
    print(f"  CS:  GPIO{CS_PIN}")
    print("Press Ctrl+C to exit")
    
    # Initialize LCD
    lcd = LCD_2inch()
    
    try:
        # Clear screen
        lcd.clear(BLACK)
        time.sleep(1)
        
        # Rolling text parameters
        text = "Hello World!"
        font_size = 36
        text_speed = 3  # pixels per frame
        
        # Get text width for initial positioning
        temp_image = Image.new('RGB', (lcd.width, lcd.height), (0, 0, 0))
        temp_draw = ImageDraw.Draw(temp_image)
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
        except:
            font = ImageFont.load_default()
        
        bbox = temp_draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        
        # Start position (off screen to the right)
        position = lcd.width
        
        colors = [
            (255, 255, 255),  # White
            (255, 0, 0),      # Red
            (0, 255, 0),      # Green
            (0, 0, 255),      # Blue
            (255, 255, 0),    # Yellow
            (255, 0, 255),    # Magenta
            (0, 255, 255),    # Cyan
        ]
        color_index = 0
        frame_count = 0
        
        print("Rolling text animation started!")
        
        while True:
            # Change color every 60 frames
            if frame_count % 60 == 0:
                color_index = (color_index + 1) % len(colors)
            
            # Create image with text at current position
            image, _ = create_rolling_text_image(
                text, position, lcd.width, lcd.height, 
                font_size, colors[color_index], (0, 0, 0)
            )
            
            # Display image
            lcd.show_image(image)
            
            # Update position
            position -= text_speed
            
            # Reset position when text completely scrolls off screen
            if position < -text_width:
                position = lcd.width
            
            frame_count += 1
            time.sleep(0.05)  # Control animation speed
    
    except KeyboardInterrupt:
        print("\nExiting...")
    
    finally:
        # Clean up
        lcd.clear(BLACK)
        lcd.cleanup()
        print("LCD cleaned up. Goodbye!")

if __name__ == "__main__":
    main()
