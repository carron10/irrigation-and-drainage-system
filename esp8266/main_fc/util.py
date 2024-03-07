import uasyncio as a
# from main_fc.func import read_loop, blink_loop
import machine
from dht import DHT11
import time



class RainDropSensor:
    def __init__(self) -> None:
        self.adc=machine.ADC(0)
        self.conversion_factor=100/(65535)
    def read(self):
        rainCoverage=100-(self.adc.read_u16()*self.conversion_factor)
        return round(rainCoverage,1)
    def read_rainfall_intensity(self):
        # Read the ADC value from the rain sensor (0-65535)
        adc_value = self.adc.read()

        # Convert the ADC value to a percentage (0-100)
        # Calibrate these values according to your specific sensor and requirements
        dry_value = 2000
        max_wet_value = 5000
        rainfall_percentage = max(0, min(100, (adc_value - dry_value) / (max_wet_value - dry_value) * 100))
        return rainfall_percentage
    def isconnected(self):
        #ToDo: Write code to detect if this sensor is connected oor not
        return not self.read_rainfall_intensity()==0
class HumidityTemperatureSensor:
    def __init__(self,pin=2) -> None:
        self.dht_sensor = DHT11(machine.Pin(pin))
    def isconnected(self):
        try:
            self.read()
            return True
        except Exception as ex:
            return False
        
    def read(self):
        # Get the temperature and humidity data
        self.dht_sensor.measure()
        temperature =self.dht_sensor.temperature()
        humidity =  self.dht_sensor.humidity()
        return temperature,humidity
    def read_temperature(self):
        temperature =self.dht_sensor.temperature()
        return temperature
    def read_humidity(self):
        humidity =  self.dht_sensor.humidity()
        return humidity
    
    
class SoilMoistureSensor:
    def __init__(self) -> None:
        self.adc=machine.ADC(0)
    def read(self):
        soil_moisture=self.adc.read()
        return round(soil_moisture,1)
    def isconnected(self):
        #ToDo: Write code to detect if this sensor is connected oor not
        return not self.read()==8 or self.read()==7


        
    
    


