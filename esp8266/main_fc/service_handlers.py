import utime
from machine import Pin


class IrrigationService:
    def __init__(self,pin:int=5) -> None:
        """To start and stop the irrigation service
        
        Args:
            pin (int, optional):The pin that the relay is connected to. Defaults to 5.
        """
        self.relay_pin = Pin(pin, Pin.OUT)
    def start(self, options=None):
        """To start irrigation

        Args:
            options (dict): _description_
        """
        print("Irrigation Start")
        self.relay_pin.value(1)

    def stop(self, options=None):
        """To stop the irrigation

        Args:
            options (_type_): To param needed
        """
        print(f"Stopping Irrigation system.....")
        self.relay_pin.value(0)
        
    def schedule(self, options):
        
        """Schedule to be done by the server"""
        pass

class DrainageService:
    def __init__(self,pin=5) -> None:
        self.relay_pin = Pin(pin, Pin.OUT)
    def start(self,options=None):
        #Todo: Add code to start drainage--- this is will be switch a pin On
        print("Drainage Started")
        self.relay_pin.value(1)
    def stop(self,options=None):
        #Todo: Add code to stop drainage--- this is will be switch a pin Off
        print("Drainage Stopped")
        self.relay_pin.value(0)