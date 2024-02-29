"""This file contains functions to communicate with the Micro Controller  Only"""

from app.websocket import WebSocket
import time


websocket=WebSocket(route='/')

@websocket.on("data")
def print_data(data,ws):
    print(data)
    for i in range(2):
        time.sleep(1)
        print(f"nsn {i}")
        ws.send(f"Sooomm {i}")
    print("Heloo World")
        

@websocket.on("connect")
def print_data(data,ws):
    print("Connected")

@websocket.on("disconnect")
def handle_disconnect(ws):
    print("Closed")