from machine import Pin
import time
import network as net
import uasyncio as a
import gc
import machine
from dht import DHT11
from main_fc.async_websocket_client import AsyncWebsocketClient

humidity_sensor=DHT11(Pin(16))
adc=machine.ADC(0)
conversion_factor=100/(1024)

while True:

    rainCoverage=100-(adc.read()*conversion_factor)


    humidity_sensor.measure()
    temp=humidity_sensor.temperature()
    humidity=humidity_sensor.humidity()

    print("Moisture %2.2f %%" %rainCoverage)
    print("V:",adc.read())
    # print("Temperature %2.2f C" %temp)
    # print("Humididy %2.2f %%" %humidity)
    time.sleep(1)
