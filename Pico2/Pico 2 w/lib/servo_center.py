"""
Servo Center/Home Position Script for Pico 2 W with Kitronik Pico Robotics Board
Uses Kitronik PicoRobotics library to control servos

Hardware:
- Pico 2 W
- Kitronik Pico Robotics Board
- Pan servo (TD-8625MG) on servo channel 1
- Tilt servo (TD-8625MG) on servo channel 2

Note: Make sure PicoRobotics.py is uploaded to your Pico
"""

from PicoRobotics import KitronikPicoRobotics
import time

class ServoController:
    def __init__(self):
        # Initialize the Kitronik Pico Robotics board
        print("Initializing Kitronik Pico Robotics Board...")
        self.board = KitronikPicoRobotics()
        
        # Servo channels (1-indexed on the Kitronik board)
        self.pan_channel = 1    # Pan servo
        self.tilt_channel = 2   # Tilt servo
        
        print("Board initialized successfully!")
    
    def set_servo_degrees(self, channel, degrees):
        """
        Set servo to specific angle using Kitronik library
        channel: servo channel (1 or 2)
        degrees: angle in degrees (0-180)
        """
        if degrees < 0:
            degrees = 0
        elif degrees > 180:
            degrees = 180
            
        self.board.servoWrite(channel, degrees)
    
    def center_servos(self):
        """Set both servos to center position (90 degrees)"""
        print("Centering servos...")
        
        # Set pan servo to center (90 degrees)
        self.set_servo_degrees(self.pan_channel, 90)
        print(f"Pan servo (channel {self.pan_channel}): 90° (center)")
        
        # Set tilt servo to center (90 degrees)  
        self.set_servo_degrees(self.tilt_channel, 90)
        print(f"Tilt servo (channel {self.tilt_channel}): 90° (center)")
        
        # Give servos time to reach position
        time.sleep(2)
        print("Servos should now be in center position!")
    
    def test_movement(self):
        """Test servo movement with small adjustments"""
        print("\nTesting servo movement...")
        
        # Test pan servo
        print("Testing pan movement...")
        self.set_servo_degrees(self.pan_channel, 60)   # Left
        time.sleep(1)
        self.set_servo_degrees(self.pan_channel, 90)   # Center
        time.sleep(1)
        self.set_servo_degrees(self.pan_channel, 120)  # Right
        time.sleep(1)
        self.set_servo_degrees(self.pan_channel, 90)   # Back to center
        time.sleep(1)
        
        # Test tilt servo
        print("Testing tilt movement...")
        self.set_servo_degrees(self.tilt_channel, 60)  # Down
        time.sleep(1)
        self.set_servo_degrees(self.tilt_channel, 90)  # Center
        time.sleep(1)
        self.set_servo_degrees(self.tilt_channel, 120) # Up
        time.sleep(1)
        self.set_servo_degrees(self.tilt_channel, 90)  # Back to center
        time.sleep(1)
        
        print("Test complete - servos returned to center")
    
    def manual_control(self):
        """Interactive manual control for testing"""
        print("\nManual Control Mode")
        print("Commands:")
        print("  'p <angle>' - Set pan servo (e.g., 'p 90')")
        print("  't <angle>' - Set tilt servo (e.g., 't 45')")
        print("  'center' - Center both servos")
        print("  'test' - Run movement test")
        print("  'quit' - Exit manual control")
        
        while True:
            try:
                cmd = input("\n> ").strip().lower()
                
                if cmd == 'quit':
                    break
                elif cmd == 'center':
                    self.center_servos()
                elif cmd == 'test':
                    self.test_movement()
                elif cmd.startswith('p '):
                    try:
                        angle = int(cmd.split()[1])
                        self.set_servo_degrees(self.pan_channel, angle)
                        print(f"Pan set to {angle}°")
                    except (ValueError, IndexError):
                        print("Invalid format. Use: p <angle>")
                elif cmd.startswith('t '):
                    try:
                        angle = int(cmd.split()[1])
                        self.set_servo_degrees(self.tilt_channel, angle)
                        print(f"Tilt set to {angle}°")
                    except (ValueError, IndexError):
                        print("Invalid format. Use: t <angle>")
                else:
                    print("Unknown command")
                    
            except KeyboardInterrupt:
                break
        
        print("Exiting manual control...")

def main():
    print("Kitronik Servo Center/Home Position Script")
    print("==========================================")
    
    try:
        # Initialize servo controller
        servo_controller = ServoController()
        
        # Center both servos
        servo_controller.center_servos()
        
        print("\nOptions:")
        print("1. Keep servos centered (press Ctrl+C to exit)")
        print("2. Run movement test (uncomment line below)")
        print("3. Manual control (uncomment line below)")
        
        # Uncomment one of these lines as needed:
        # servo_controller.test_movement()
        # servo_controller.manual_control()
        
        print("\nServos are centered and ready for assembly!")
        print("Press Ctrl+C to exit...")
        
        # Keep script running to maintain servo position
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nExiting...")
    except ImportError as e:
        print(f"Error importing PicoRobotics library: {e}")
        print("Make sure PicoRobotics.py is uploaded to your Pico!")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()