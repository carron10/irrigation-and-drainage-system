import gc
import json
import sys
import time

import network as net
import uasyncio as a

from .async_websocket_client import AsyncWebsocketClient
from .wifi import wifi_connect


class MainApp:
    def __init__(self, config, start_time) -> None:
        self.ws = AsyncWebsocketClient(config.get("socket_delay_ms"))
        self.events = {"connected": [], "disconnect": [],"*":[]}
        self.config = config
        self.start_time = start_time
        self.reconnect=False
        self.connection_trials=0

    async def run(self):
        # Try to connect to wifi
        wifi=None
        
        if self.config.get("wifi")["auto_connect"]:
            print("connect to configured wifi")
            wifi = await wifi_connect(
                self.config.get("wifi")["SSID"], self.config.get("wifi")["password"]
            )
            if wifi.isconnected():
                if "wifi_connected" in self.events:
                    for func in self.events["wifi_connected"]:
                        func(wifi)
        else:
            print("Connected to se")

        while True:
            # Garbage Collection
            gc.collect()
            # Try connect again to wifi if failed.....
            
            if wifi!=None:
                
                if not wifi.isconnected():
                    wifi = await wifi_connect(
                    self.config.get("wifi")["SSID"], self.config.get("wifi")["password"]
                )
                if not wifi.isconnected():
                    await a.sleep_ms(self.config.get("wifi")["delay_in_msec"])
                    continue

                # Fire wifi connected event
                if "wifi_connected" in self.events:
                    for func in self.events["wifi_connected"]:
                        await func(wifi)

            try:
                self.start_time = None
                print("Handshaking...", "{}{}".format(self.config.get("server"), ""))
                # Connect to the websocket
                if not await self.ws.handshake(
                    "{}{}".format(self.config.get("server"), "")
                ):
                    raise Exception("Handshake error.")

                self.start_time = time.time()
                # Websocket Connected

                if self.reconnect:
                    if "reconnected" in self.events:
                       for func in self.events["reconnected"]:
                         await func(self.ws)
                    self.reconnect=False
                else:
                    if "connected" in self.events:
                       for func in self.events["connected"]:
                        await func(self.ws)

                # Open websocket and wait for data
                while await self.ws.open():
                    # Receive Data
                    data = await self.ws.recv()
                    if data == None:
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

                    return_to=data['return'] if "return" in data else None
                    # Execute functions registered on this event
                    if event in self.events:
                        for func in self.events[event]:
                            await func(
                                data["data"] if "data" in data else None, self.ws,return_to
                            )

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

    async def fire(self, event: str, *args, **kwargs):
        print("Fired ",event)
        if event in self.events:
            for func in self.events[event]:
                await func(*args, **kwargs)
    async def disconnect_and_reconnect(self):
        if await self.ws.open():
            await self.ws.close()
            self.reconnect=True
                    