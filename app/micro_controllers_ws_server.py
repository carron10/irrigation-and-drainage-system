"""This file contains functions to communicate with the Micro Controller  Only"""

from app.websocket import WebSocket
import time
import json
from app.models import User, Role, Notifications, Options, Statistics, Meta, FieldZone
from flask import Flask
from schedule import Scheduler
import schedule
from app.utils import generate_unique_string

db = None
app: Flask = None

scheduler: Scheduler = None


class InitSock(WebSocket):
    def __init__(self, application: Flask = None, route="/", schedule=None):
        global app, scheduler
        scheduler = scheduler
        app = application
        self.app = app
        super().__init__(application, route)

    def init_app(self, data_base, application, schedule=None):
        global db
        global app, scheduler
        scheduler = schedule
        db = data_base
        app = application
        return super().init_app(app, scheduler)


websocket = InitSock(route="/controller/<devicename>")
connected_devices = {}
last_sensors_updates = {}


def send_command(command, require_return=False, time_out=7) -> bool:
    return send_data(
        {"data": {"cmd": command}, "event": "command"},
        require_return=require_return,
        time_out=time_out,
    )

def get_sensor_value(sensor_name):
    if len(connected_devices.keys()) > 0:
        for k, v in connected_devices.items():
            if sensor_name in connected_devices[k]["sensors"]:
                return connected_devices[k]["sensors"][sensor_name][
                    "last_value"
                ]
    return None

def send_data(data, time_out=7, require_return=False) -> bool:
    done = False
    last_trial = None
    if require_return:
        uniq_strin = generate_unique_string()
        data["return"] = uniq_strin

        @websocket.on_temp_event(uniq_strin)
        def return_fun(*args, **kwargs):
            nonlocal done
            done = True
            websocket.remove_event(uniq_strin)

    def try_send():
        nonlocal last_trial
        current_time = time.time()
        if done:
            return
        if last_trial != None:
            if (current_time - last_trial) > 1:
                return
        last_trial = time.time()
        for k, v in connected_devices.items():
            if connected_devices[k]["ws"].connected:
                connected_devices[k]["ws"].send(json.dumps(data))

    if require_return:
        i = 0
        while i <= time_out:
            if done:
                return True
            try_send()
            time.sleep(0.5)
            i += 1
        return False
    else:
        try_send()
    return True


def get_all_connected_sensors():
    global connected_devices
    sensors = {}
    for k, v in connected_devices.items():
        for sensor, v in v["sensors"].items():
            sensors[sensor] = v
    return sensors


@websocket.on("reconnect")
def on_reconnect(ws, *args, **kwargs):
    global connected_devices
    connected_devices[kwargs["devicename"]]["ws"] = ws


@websocket.on("connect")
def on_connect(ws, *args, **kwargs):
    global websocket, connected_devices
    device = {"name": kwargs["devicename"], "ws": ws, "sensors": {}}
    connected_devices[kwargs["devicename"]] = device
    ws.send(
        json.dumps(
            {
                "data": {
                    "cmd": "config --socket_send_data_seconds 10 --send_sensor_status_seconds 5"
                },
                "event": "command",
            }
        )
    )


@websocket.on("disconnect")
def handle_disconnect(*args, **kwargs):
    global connected_devices
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
    global scheduler
    action = "start" if start else "stop"
    print("===Start/Stop irrigation called==")
    sent = send_command(f"{what} {action}",require_return=True,time_out=40)
    if sent:
        if call_back_fun:
            call_back_fun(call_back_args)
        return schedule.CancelJob
    
