import time

# from main_fc.func import read_loop, blink_loop
import machine
import uasyncio as a
from dht import DHT11
from machine import Pin

pin=14 ##D5
sensor=Pin(pin,Pin.IN)
#test rainfall sensor pin
for i in range(50):
    time.sleep(1)
    print("VALUE",sensor.value())