"""This file contains functions to communicate with the Micro Controller  Only"""

from app.websocket import WebSocket
import time
import json
from app.models import User, Role, Notifications, Options, Statistics, Meta, FieldZone
from flask import Flask
import schedule

db = None
app: Flask = None


class InitSock(WebSocket):
    def __init__(self, application: Flask = None, route="/"):
        global app
        app = application
        self.app = app
        super().__init__(application, route)

    def init_app(self, data_base, application):
        global db
        global app
        db = data_base
        app = application
        return super().init_app(app)


websocket = InitSock(route="/controller/<devicename>")
connected_devices = {}
last_sensors_updates = {}


def get_all_connected_sensors():
    sensors = {}
    for k, v in connected_devices.items():
        for sensor, v in v["sensors"].items():
            sensors[sensor] = v
    return sensors


@websocket.on("connect")
def print_data(ws, *args, **kwargs):
    global websocket
    device = {"name": kwargs["devicename"], "ws": ws, "sensors": {}}
    connected_devices[kwargs["devicename"]] = device
    ws.send(
        json.dumps(
            {
                "data": {
                    "cmd": "config --socket_send_data_seconds 30 --send_sensor_status_seconds 5"
                },
                "event": "command",
            }
        )
    )


@websocket.on("disconnect")
def handle_disconnect(*args, **kwargs):
    if kwargs["devicename"] in connected_devices:
        del connected_devices[kwargs["devicename"]]


@websocket.on("register_sensors")
def register_sensors(data, ws, devicename):
    global connected_devices
    if devicename in connected_devices:
        for sensor, v in data.items():
            connected_devices[devicename]["sensors"][sensor] = v
            connected_devices[devicename]["sensors"][sensor]["status"] = False
            connected_devices[devicename]["sensors"][sensor]["last_value"] = None


@websocket.on("sensor_update")
def sensor_update(data, ws, devicename):
    global connected_devices
    try:
        for k, v in data.items():
            last_sensors_updates[k] = v
            stats = Statistics(for_=k, value=v, history_type="sensor_update")
            db.session.add(stats)
            connected_devices[devicename]["sensors"][k]["last_value"] = v
    except:
        pass


@websocket.on("sensor_status")
def registor_sensors_status(data, ws, devicename):
    global connected_devices
    try:
        for sensor in data:
            if sensor not in connected_devices[devicename]["sensors"].keys():
                # Todo: Write the response , where unrestered sensor detected
                pass
            else:
                connected_devices[devicename]["sensors"][sensor]["status"] = data[
                    sensor
                ]
    except:
        pass
    #   print('An exception occurred')


def start_stop_irrigation_and_drainage(
    what="irrigation", start: bool = False, call_back_fun=None, call_back_args=None
):
    """To start/stop irrigation system
    Args:
        what (str, optional): Irrigation or drainage. Defaults to "irrigation".
        start (bool, optional): start or stop . Defaults to False.
        call_back_fun (_type_, optional): A function to call back after sending the command. Defaults to None.
    """
    action = "start" if start else "stop"
    
    stop = False
    ##Ensure the  command is sent
    while not stop:
        try:
            if len(connected_devices.keys()) > 0:
                for k, v in connected_devices.items():
                    ws = connected_devices[k]["ws"]
                    if ws.connected:
                        ws.send(
                            json.dumps(
                                {
                                    "event": "command",
                                    "data": {"cmd": f"{what} {action}"},
                                }
                            )
                        )
                    stop=True
        except:
            print("Waiting for components to connect")
        time.sleep(1)

    if call_back_fun:
        call_back_fun(call_back_args)
        
    return schedule.CancelJob


