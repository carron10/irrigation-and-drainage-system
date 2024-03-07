"""This file contains functions to communicate with the Micro Controller  Only"""

from app.websocket import WebSocket
import time
import json
from app.models import User, Role, Notifications, Options, Statistics, Meta, FieldZone

db = app = None


class InitSock(WebSocket):
    def __init__(self, application=None, route="/"):
        global app
        app = application
        super().__init__(application, route)

    def init_app(self, data_base, application):
        global db
        global app
        db = data_base
        app = application
        return super().init_app(app)


websocket = InitSock(route="/controller/<devicename>")
connected_devices = {}


@websocket.on("connect")
def print_data(ws, *args, **kwargs):
    global websocket
    device={"name":kwargs["devicename"],"ws":ws,"sensors":{}}
    connected_devices[kwargs["devicename"]] = device
    ws.send(
        json.dumps(
            {
                "data":{'cmd':"config --socket_send_data_seconds 40 --socket_reconnect_seconds 20"},
                "event": "command",
            }
        )
    )



@websocket.on("disconnect")
def handle_disconnect(*args, **kwargs):
    if kwargs["devicename"] in connected_devices:
        del connected_devices[kwargs["devicename"]]


@websocket.on("register_sensors")
def register_sensors(data, ws,devicename):
    global connected_devices
    for sensor in data:
        connected_devices[devicename]['sensors'][sensor]={}
        connected_devices[devicename]['sensors'][sensor]['status']=False


@websocket.on("sensor_update")
def sensor_update(data, ws,devicename):
    for k, v in data.items():
        stats = Statistics(for_=k, value=v, history_type="sensor_update")
        db.session.add(stats)
    # print(data)


@websocket.on("sensor_status")
def registor_sensors_status(data, ws,devicename):
    global connected_devices
    for sensor in data:
        if sensor not in connected_devices[devicename]['sensors'].keys():
            # Todo: Write the response , where unrestered sensor detected
            pass
        else:
            connected_devices[devicename]['sensors'][sensor]["status"] = data[sensor]
