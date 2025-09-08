import network
import socket
from time import sleep
from picozero import pico_temp_sensor, pico_led
import machine
import rp2
import sys
import urequests
import umqtt.simple
import PicoRobotics
board = PicoRobotics.KitronikPicoRobotics()
import mip
import phew
import microdot
from phew import logging, server
from machine import Pin

#Set hostname
hostname ="Pico2w"
ssid = "SC2025"
password = "april202025"

# Initialize onboard LED
# On Raspberry Pi Pico W, use 'LED' in quotes to refer to the onboard LED
# Note that the onboard LED is controlled by the WiFi chip, not a simple GPIO
led = Pin('LED', Pin.OUT)

mqtt_server = "192.168.1.129"  # Or "localhost" if applicable
mqtt_port = 1883  # Or the port you configured Mosquitto to use
mqtt_client_id = "Pico2w"
mqtt_topic_sub = b"Pico2w" # Replace with the topic you want to subscribe to

# Callback function for received messages
def sub_cb(topic, msg):
    print("Received message on topic: {}".format(topic.decode('utf-8')))
    print("Message: {}".format(msg.decode('utf-8')))
    # Add your code here to process the received message

# Function to connect to MQTT broker
def mqtt_connect():
    client = MQTTClient(mqtt_client_id, mqtt_server, port=mqtt_port)
    client.set_callback(sub_cb) # Set the callback function before connecting
    client.connect()
    print('Connected to %s MQTT Broker' % (mqtt_server))
    return client

led = machine.Pin('LED', machine.Pin.OUT)
def connect():
    #Connect to WLAN
    wlan = network.WLAN()
    wlan.active(True)
    wlan.connect(ssid, password)
    while wlan.isconnected() == False:
        print('Waiting for connection...')
        sleep(1)
    print(wlan.ifconfig())
    led.value(1) # Turn on the LED
connect()
                 
def index(request):
    response = "Hello World"
    return response

server.add_route('/', index, methods=['GET'])

logging.info("Started Webserver")

server.run()
    
    # Main loop
try:
    connect_to_internet(wifi_ssid, wifi_password)
    client = mqtt_connect()
    client.subscribe(mqtt_topic_sub)  # Subscribe to the topic

    while True:
        client.check_msg() # Check for new messages
        time.sleep(1) # Keep the loop running and prevent blocking

except OSError as e:
    print('Failed to connect to the MQTT Broker or Network:', e)
    # Handle connection errors or implement reconnection logic
    
