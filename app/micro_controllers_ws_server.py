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
    """Websocket instance, for commuticating with the microcroller

    Args:
        WebSocket (_type_): websocket instance
    """

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

# store the devices connected and the sensor values
connected_devices = {}
last_sensors_updates = {}


def send_command(command, require_return=False, time_out=7) -> bool:
    """Sent command to the micro controller

    Args:
        command (_type_):command to send
        require_return (bool, optional): require a return status. Defaults to False.
        time_out (int, optional):  Time to wait after sending the status . Defaults to 7.

    Returns:
        bool: whether the command was sent successfully or not
    """
    return send_data(
        {"data": {"cmd": command}, "event": "command"},
        require_return=require_return,
        time_out=time_out,
    )


def get_drainage_status(time_out=7):
    """To get drainage status from the micro controller

    Args:
        time_out (int, optional): time to wait for results. Defaults to 7.

    Returns:
        int: 1 or 0
    """
    return send_command("drainage status", require_return=True, time_out=time_out)


def get_irrigation_status(time_out=7) -> bool:
    """To get the irrigation status

    Args:
        time_out (int, optional): time to wait to return. Defaults to 7.

    Returns:
        bool:  Status or the irrigation . 
    """
    return send_command("irrigation status", require_return=True, time_out=time_out)


def get_sensor_value(sensor_name: str) -> str:
    """Get the current sensor value

    Args:
        sensor_name (str): name of the sensor

    Returns:
       int/None: sensor value 
    """
    if len(connected_devices.keys()) > 0:
        for k, v in connected_devices.items():
            if sensor_name in connected_devices[k]["sensors"]:
                return connected_devices[k]["sensors"][sensor_name][
                    "last_value"
                ]
    return None


def send_data(data: dict, time_out=7, require_return=False) -> bool:
    """To send data to the micro controleer

    Args:
        data (dict): data to send
        time_out (int, optional): time to wait for results (works if require_return is True). Defaults to 7.
        require_return (bool, optional): require results. Defaults to False.

    Returns:
        bool: if delivered or not.
    """
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


def get_all_connected_sensors(with_devices=False) -> dict:
    """To get all sensors connected

    Args:
        with_devices (bool, optional): Include the devices that the sensors are connected to. Defaults to False.

    Returns:
        dict: sensor list
    """
    global connected_devices
    if not with_devices:
        sensors = {}
        for k, v in connected_devices.items():
            for sensor, v in v["sensors"].items():
                sensors[sensor] = v
        return sensors
    else:
        connected_devices_copy = connected_devices.copy()
        if len(connected_devices_copy.keys()) > 0:
            for k, v in connected_devices_copy.items():
                if "ws" in connected_devices_copy[k]:
                    del connected_devices_copy[k]["ws"]
        return connected_devices_copy







@websocket.on("connect")
def on_connect(ws, *args, **kwargs):
    "Called when the websocket connects microcontroller"
    global websocket, connected_devices
    device = {"name": kwargs["devicename"], "ws": ws, "sensors": {}}
    connected_devices[kwargs["devicename"]] = device
    ws.send(
        json.dumps(
            {
                "data": {
                    "cmd": "config --socket_send_data_seconds 3 --send_sensor_status_seconds 2"
                },
                "event": "command",
            }
        )
    )


@websocket.on("reconnect")
def on_reconnect(ws, *args, **kwargs):
    """Function to be called when the micro controler is reconnecting, after disconnect, the server will wait for some
    seconds for the micro controller to reconnect, when it reconnect this function will be called

    Args:
        ws (_type_): websocket instance
    """
    try:
        #update the old instance with the new one
        connected_devices[kwargs["devicename"]]["ws"] = ws
    except:
        #if there an erroe, treat this as a new connection
        on_connect(ws, *args, **kwargs)


@websocket.on("disconnect")
def handle_disconnect(*args, **kwargs):
    """
    Called when the controller disconnects, this is called if the server waited for reconnection and no reconnnections. Therefore
    thi function is not called imediately after disconnect but after some seconds/mins
    """
    global connected_devices
    if kwargs["devicename"] in connected_devices:
        del connected_devices[kwargs["devicename"]]


@websocket.on("register_sensors")
def register_sensors(data: dict, ws:WebSocket, devicename:str):
    """After connection, this sensor should send/register its sensors. 

    Args:
        data (dict): a list of sensors
        ws (Websocket): A websocket instace for this connection
        devicename (str): the device name
    """
    global connected_devices
    if devicename in connected_devices:
        for sensor, v in data.items():
            connected_devices[devicename]["sensors"][sensor] = v
            connected_devices[devicename]["sensors"][sensor]["status"] = False
            connected_devices[devicename]["sensors"][sensor]["last_value"] = None


@websocket.on("sensor_update")
def sensor_update(data: dict, ws: WebSocket, devicename:str):
    """Called when there is new sensor values received

    Args:
        data (dict): list of sensor with their values, normal it one sensor with its values e.g {Humidity:12,Temperature:30}
        ws (Websocket): ws connection
        devicename (str): device name
    """
    global connected_devices, last_sensors_updates, db
    
    try:
        for k, v in data.items():
            last_sensors_updates[k] = v
            ##update databse
            stats = Statistics(for_=k, value=v, history_type="sensor_update")
            db.session.add(stats)
            connected_devices[devicename]["sensors"][k]["last_value"] = v
    except Exception as e:
        print(e)
        pass


@websocket.on("sensor_status")
def registor_sensors_status(data: dict, ws: WebSocket, devicename:str):
    """Called when the is new sensor status, e.g SoilMoisture disconnetin

    Args:
        data (dict): list of sensors with their statuses
        ws (WebSocket): connection instance
        devicename (str): device name
    """
    global connected_devices
    try:
        for sensor in data:
            if sensor not in connected_devices[devicename]["sensors"].keys():
                # Todo: Write the response , where unregistered sensor detected
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
    """To start/stop irrigation system, this function is called by scheules
    
    Args:
        what (str, optional): Irrigation or drainage. Defaults to "irrigation".
        start (bool, optional): start or stop . Defaults to False.
        call_back_fun (_type_, optional): A function to call back after sending the command. Defaults to None.
    """
    global scheduler
    action = "start" if start else "stop"
    
    ##Send the sart command e.g irrigation start
    ##Wait 40  seconds... This is to avoid sending command that won't reach the destination,
    # e.g start the irrigation and  get no results. Sad right?
    sent = send_command(f"{what} {action}", require_return=True, time_out=40)
    if sent:
        #after starting/stoping send a callback
        if call_back_fun:
            return call_back_fun(call_back_args)
        ##or else return cancel_Job in case this function was executed through a scheduler
        return schedule.CancelJob
