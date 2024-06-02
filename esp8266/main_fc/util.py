import time

# from main_fc.func import read_loop, blink_loop
import machine
import uasyncio as a
from dht import DHT11


class RainDropSensor:
    def __init__(self, pin=14):
        self.sensor = machine.Pin(pin, machine.Pin.IN)
        self.last_time_check = None

    def should_wait(self):
        if self.last_time_check is not None:
            t_diff = time.time()-self.last_time_check
            if t_diff < 0.5:
                time.sleep(0.5-t_diff)
        self.last_time_check = time.time()

    def read(self):
        """check if it is raining or not

        Returns:
            bool:True if raining, false if not
        """
        self.should_wait()
        return self.sensor.value()==0

    def isconnected(self):
        # Always return true
        return True


class HumidityTemperatureSensor:
    def __init__(self, pin=2) -> None:
        self.dht_sensor = DHT11(machine.Pin(pin))
        self.last_time_check = None

    def should_wait(self):
        if self.last_time_check is not None:
            t_diff = time.time()-self.last_time_check
            if t_diff < 1.5:
                time.sleep(1.5-t_diff)
                print("Slept")
        self.last_time_check = time.time()

    def isconnected(self):
        try:
            self.read()
            return True
        except Exception as ex:
            return False

    def read(self):
        # Get the temperature and humidity data
        self.should_wait()
        self.dht_sensor.measure()
        temperature = self.dht_sensor.temperature()
        humidity = self.dht_sensor.humidity()
        return temperature, humidity

    def read_temperature(self):
        self.should_wait()
        self.dht_sensor.measure()
        temperature = self.dht_sensor.temperature()
        return temperature

    def read_humidity(self):
        self.should_wait()
        self.dht_sensor.measure()
        humidity = self.dht_sensor.humidity()
        return humidity


class SoilMoistureSensor:
    def __init__(self):
        self.adc = machine.ADC(0)

    def read(self):
        min_value = 30000
        max_value = 65535
        rain_coverage = ((max_value-self.adc.read_u16()) /
                         (max_value-min_value))*100
        if rain_coverage > 100:
            rain_coverage = 100
        return round(rain_coverage, 1)

    def isconnected(self):
        # ToDo: Write code to detect if this sensor is connected oor not
        value = self.adc.read()
        return not (value == 8 or value == 9 or value == 7)
    
