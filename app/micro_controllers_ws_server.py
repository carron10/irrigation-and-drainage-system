"""This file contains functions to communicate with the Micro Controller  Only"""

from app.websocket import WebSocket
import time


websocket=WebSocket(route='/')

@websocket.on("data")
def print_data(data,ws):
    print(data)
    for i in range(100):
        time.sleep(2)
        ws.send(f"Sooomm {i}")
        

@websocket.on("connect")
def print_data(data,ws):
    print("Connected")