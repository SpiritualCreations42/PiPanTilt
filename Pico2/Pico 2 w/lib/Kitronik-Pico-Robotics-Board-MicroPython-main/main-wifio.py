import network
import socket
from time import sleep
from picozero import pico_temp_sensor, pico_led
import machine
import rp2
import sys
import urequests
#Set hostname
hostname ="pico1"
ssid = "SC2025"
password = "april202025"

#Default hosted website text




def connect():
    #Connect to WLAN
    wlan = network.WLAN()
    wlan.active(True)
    wlan.connect(ssid, password)
    while wlan.isconnected() == False:
        print('Waiting for connection...')
        sleep(1)
    print(wlan.ifconfig())


connect()

import machine
import time

led = machine.Pin("LED", machine.Pin.OUT)

while True:
    led.on()
    time.sleep(1)
    led.off()
    time.sleep(1)
    
    #AllServoTest.py
# test code that ramps each servo from 0-180-0 
import PicoRobotics
import utime


board = PicoRobotics.KitronikPicoRobotics()
while True:
    for degrees in range(180):
        for servo in range(1,9):
            board.servoWrite(servo, degrees)
        utime.sleep_ms(10) #ramp speed over 10x180ms => approx 2 seconds.
    for degrees in range(180):
        for servo in range(1,9):
            board.servoWrite(servo, 180-degrees)
        utime.sleep_ms(10) #ramp speed over 10x180ms => approx 2 seconds.

