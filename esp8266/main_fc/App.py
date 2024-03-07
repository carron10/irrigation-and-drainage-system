import network as net
import uasyncio as a
import json
import gc
from .async_websocket_client import AsyncWebsocketClient
from .wifi import wifi_connect
import sys
import time

class MainApp:
    def __init__(self, config, lock,start_time) -> None:
        self.ws = AsyncWebsocketClient(config["socket_delay_ms"])
        self.events = {"connected": [], "disconnect": []}
        self.config = config
        self.lock = lock
        self.start_time=start_time
    async def run(self):
        # Try to connect to wifi
        wifi = await wifi_connect(
            self.config["wifi"]["SSID"], self.config["wifi"]["password"]
        )
        if wifi.isconnected():
            if "wifi_connected" in self.events:
                for func in self.events["wifi_connected"]:
                    func(wifi)
       
        while True:
            # Garbage Collection
            gc.collect()
            # Try connect again to wifi if failed.....
            if not wifi.isconnected():
                wifi = await wifi_connect(
                    self.config["wifi"]["SSID"], self.config["wifi"]["password"]
                )
                if not wifi.isconnected():
                    await a.sleep_ms(self.config["wifi"]["delay_in_msec"])
                    continue

                # Fire wifi connected event
                if "wifi_connected" in self.events:
                    for func in self.events["wifi_connected"]:
                        await func(wifi)

            try:
                self.start_time=None
                print("Handshaking...", "{}{}".format(self.config["server"], ""))
                # Connect to the websocket
                if not await self.ws.handshake(
                    "{}{}".format(self.config["server"], "")
                ):
                    raise Exception("Handshake error.")

                self.start_time=time.time()
                # Websocket Connected

                if "connected" in self.events:
                    for func in self.events["connected"]:
                        await func(self.ws)
                        
                # Open websocket and wait for data
                while await self.ws.open():
                    # Receive Data
                    data = await self.ws.recv()
                    
                    print("Data", data)
                    if data==None:
                        if "disconnect" in self.events:
                            for func in self.events["disconnect"]:
                                await func()
                    # Convert to Json Format
                    data = json.loads(data)
                    # Get Event from data
                    event = data["event"]
                    # Notify function registered to receive any events
                    for func in self.events["*"]:
                        await func(data, self.ws)
                    # end try

                    # Execute functions registered on this event
                    if event in self.events:
                        for func in self.events[event]:
                            await func(data["data"] if "data" in data else None, self.ws)
                            
                    
                    # Wait a moment
                    await a.sleep_ms(50)
            except Exception as ex:
                print("Exception: {}".format(ex))
                await a.sleep(1)

    def on(self, event: str):
        def inner(func):
            print("Event Added", event)
            if event in self.events:
                self.events[event].append(func)
            else:
                self.events[event] = [func]

        return inner
    async def fire(self,event:str,*args,**kwargs):
        if event in self.events:
            for func in self.events[event]:
               await func(*args,**kwargs)
