"""
Minimal ST7789V LCD test for Raspberry Pi Pico 2 W
This is a basic test that initializes the display and sends basic commands
"""

from machine import Pin, SPI
import time

class ST7789_Basic:
    def __init__(self, spi, width, height, reset, cs, dc, backlight=None):
        self.spi = spi
        self.width = width
        self.height = height
        self.reset = reset
        self.cs = cs
        self.dc = dc
        self.backlight = backlight
        
        # Initialize pins
        self.reset.init(Pin.OUT)
        self.cs.init(Pin.OUT)
        self.dc.init(Pin.OUT)
        if self.backlight:
            self.backlight.init(Pin.OUT)
            self.backlight.on()  # Turn on backlight
    
    def write_cmd(self, cmd):
        """Write command to display"""
        self.cs.on()
        self.dc.off()  # Command mode
        self.cs.off()
        self.spi.write(bytearray([cmd]))
        self.cs.on()
    
    def write_data(self, data):
        """Write data to display"""
        self.cs.on()
        self.dc.on()  # Data mode
        self.cs.off()
        if isinstance(data, int):
            self.spi.write(bytearray([data]))
        else:
            self.spi.write(data)
        self.cs.on()
    
    def reset_display(self):
        """Reset the display"""
        self.reset.on()
        time.sleep_ms(100)
        self.reset.off()
        time.sleep_ms(100)
        self.reset.on()
        time.sleep_ms(100)
    
    def init_display(self):
        """Initialize the ST7789V display"""
        self.reset_display()
        
        # Software reset
        self.write_cmd(0x01)
        time.sleep_ms(150)
        
        # Sleep out
        self.write_cmd(0x11)
        time.sleep_ms(120)
        
        # Color mode - 16bit
        self.write_cmd(0x3A)
        self.write_data(0x05)
        
        # Memory access control
        self.write_cmd(0x36)
        self.write_data(0x00)
        
        # Column address set
        self.write_cmd(0x2A)
        self.write_data(0x00)
        self.write_data(0x00)
        self.write_data(0x00)
        self.write_data(0xEF)  # 239
        
        # Row address set
        self.write_cmd(0x2B)
        self.write_data(0x00)
        self.write_data(0x00)
        self.write_data(0x01)
        self.write_data(0x3F)  # 319
        
        # Inversion on
        self.write_cmd(0x21)
        
        # Display on
        self.write_cmd(0x29)
        time.sleep_ms(100)
    
    def fill_screen(self, color):
        """Fill entire screen with a color"""
        # Set window
        self.write_cmd(0x2A)  # Column address set
        self.write_data(0x00)
        self.write_data(0x00)
        self.write_data(0x00)
        self.write_data(0xEF)
        
        self.write_cmd(0x2B)  # Row address set
        self.write_data(0x00)
        self.write_data(0x00)
        self.write_data(0x01)
        self.write_data(0x3F)
        
        # Start writing to memory
        self.write_cmd(0x2C)
        
        # Send color data (RGB565 format)
        color_bytes = bytearray([color >> 8, color & 0xFF])
        
        self.cs.on()
        self.dc.on()  # Data mode
        self.cs.off()
        
        # Send color data for entire screen
        for _ in range(self.width * self.height):
            self.spi.write(color_bytes)
        
        self.cs.on()

def test_basic_display():
    """Basic display test"""
    print("Initializing SPI...")
    spi = SPI(0, baudrate=40000000, sck=Pin(6), mosi=Pin(7))
    
    print("Initializing display...")
    display = ST7789_Basic(
        spi=spi,
        width=240,
        height=320,
        reset=Pin(3, Pin.OUT),
        cs=Pin(5, Pin.OUT),
        dc=Pin(4, Pin.OUT),
        backlight=Pin(2, Pin.OUT)
    )
    
    print("Initializing display registers...")
    display.init_display()
    
    # Test colors (RGB565 format)
    colors = [
        (0xF800, "Red"),      # Red
        (0x07E0, "Green"),    # Green  
        (0x001F, "Blue"),     # Blue
        (0xFFFF, "White"),    # White
        (0x0000, "Black"),    # Black
        (0xFFE0, "Yellow"),   # Yellow
    ]
    
    print("Testing colors...")
    for color, name in colors:
        print(f"Displaying {name}...")
        display.fill_screen(color)
        time.sleep(2)
    
    print("Display test completed!")
    print("If you saw different colored screens, your display is working correctly!")

if __name__ == "__main__":
    try:
        test_basic_display()
    except Exception as e:
        print(f"Error: {e}")
        print("Please check your wiring connections")