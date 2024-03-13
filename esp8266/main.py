from main_fc.App import MainApp  # Import main app...
import json
import time
from main_fc.commandlinehandler import CommandHandler
from main_fc.service_handlers import IrrigationService
from main_fc.util import (
    HumidityTemperatureSensor,
    RainDropSensor,
    SoilMoistureSensor,
)  ##Import sensor
import uasyncio as a


# Open config file and read data from it
f = open("../config.json")
text = f.read()
f.close()
config = json.loads(text)
del text
# --------------------------------

# Creat app instance
data_from_ws = ws = None
lock = a.Lock()
app = MainApp(config=config, lock=lock, start_time=None)

data = {}


# Define sensors
rain = RainDropSensor()
humidity_and_tempeture = HumidityTemperatureSensor(16)
moisture = SoilMoistureSensor()



handler = CommandHandler()

def config_service(options):
    print(options)
    global config
    for k, v in options.items():
        config[k] = v
    return "Config updated"



@app.on("command")
async def commandsController(data, ws):
    """This function will be used to execute commands from the server and send back the results to the event specified by the server"""
    cmd=data['cmd']
    return_to=data['return'] if "return" in data else None
    cmd_result=handler.process_command(cmd)
    if return_to is not None:
        await ws.send(json.dumps({"event":return_to,"data":cmd_result}))
    


@app.on("*")
async def debug_data(data, ws):
    "This function is used to receive any data that is sent from the server"
    global lock
    global data_from_ws
    await lock.acquire()
    data_from_ws = data
    lock.release()


@app.on("connected")
async def on_connect(websocket):
    '''After the websocket is connected to the server, this function will be executed....any data or configurations that needs to take place after execution will take place here'''
    global config
    global data
    data["connected"] = True
    global ws
    ws = websocket
    # register sensors here
    sensors = {"Humidity": {}, "Temperature":{}, "RainDrop": {"name":"Rainfall"}, "SoilMoisture": {"name": "Soil Moisture"}}

    data = {"event": "register_sensors", "data": sensors}
    if await ws.open():
        await ws.send(json.dumps(data))


@app.on("config")
async def on_config(data, ws):
    config_service(data)


@app.on("disconnect")
async def on_disconnect():
    global data
    print("Disconnected")
    data["connected"] = False


async def send_sensor_statuses_loop():
    """To send sensor statuses to server in async manner"""
    global lock
    global ws
    global rain
    global humidity_and_tempeture
    last_sent_time = None
    while True:
        if ws is not None:
            if await ws.open():
                try:
                    humidity_and_tempeture_on=humidity_and_tempeture.isconnected()
                    print("Sent status-------")
                    await ws.send(
                        json.dumps(
                            {
                                "event": "sensor_status",
                                "data": {
                                    "Temperature": humidity_and_tempeture_on,
                                    "Humidity":  humidity_and_tempeture_on,
                                    "RainDrop": rain.isconnected(),
                                    "SoilMoisture": moisture.isconnected(),
                                },
                            }
                        )
                    )
                    last_sent_time = time.time()
                except Exception as e:
                    print("Error[Sending sensor_status]: {}".format(e))
                    break

            if last_sent_time is not None:
                end_time = time.time()
                elapsed_time = end_time - last_sent_time
                t_diff = config["send_sensor_status_seconds"] - elapsed_time
                print("Waiting----",t_diff,config["send_sensor_status_seconds"])
                await a.sleep(1 if t_diff < 0 else t_diff)
            else:
                await a.sleep(1)
        await a.sleep(1)

async def send_moisture_loop():
    """To send moisture data to server in async manner"""
    global lock
    global ws
    global rain
    last_sent_time = None
    while True:
        if ws is not None:
            if await ws.open():
                if moisture.isconnected():
                    try:
                        await ws.send(
                            json.dumps(
                                {
                                    "data": {"SoilMoisture": moisture.read()},
                                    "event": "sensor_update",
                                }
                            )
                        )
                        last_sent_time = time.time()
                    except Exception as e:
                        print("Error[Soil_moisture]: {}".format(e))
                        break
                    # end try

                if last_sent_time is not None:
                    end_time = time.time()
                    elapsed_time = end_time - last_sent_time
                    t_diff = config["socket_send_data_seconds"] - elapsed_time
                    await a.sleep(2 if t_diff < 0 else t_diff)
                else:
                    await a.sleep(2)
        await a.sleep(1)


async def send_humidity_loop():
    """A loop to send humidity and temperature in async manner"""
    global lock
    global ws
    global rain
    global humidity_and_tempeture
    last_sent_time = None
    while True:
        if ws is not None:
            if await ws.open():
                try:
                    if humidity_and_tempeture.isconnected():
                        await a.sleep(2)
                        temp, humidity = humidity_and_tempeture.read()
                        await ws.send(
                            json.dumps(
                                {
                                    "data": {
                                        "Temperature": temp,
                                        "Humidity":humidity
                                    },
                                    "event": "sensor_update",
                                }
                            )
                        )
                        last_sent_time = time.time()
                except Exception as e:
                    print("Error[Humidity]: {}".format(e))
                    break
                if last_sent_time is not None:
                    end_time = time.time()
                    elapsed_time = end_time - last_sent_time
                    t_diff = config["socket_send_data_seconds"] - elapsed_time
                    await a.sleep(3 if t_diff < 0 else t_diff)
                else:
                    await a.sleep(3)
        await a.sleep(3)


async def send_rainfall_loop():
    """send rain drop data in async manner"""
    global lock
    global ws
    global rain
    global humidity_and_tempeture
    last_sent_time = None
    while True:
        if ws is not None:
            if await ws.open():
                if rain.isconnected():
                    try:
                        await ws.send(
                            json.dumps(
                                {
                                    "data": {
                                        "RainDrop": rain.read()
                                    },
                                    "event": "sensor_update",
                                }
                            )
                        )
                        last_sent_time = time.time()
                    except Exception as e:
                        print("Error[Sending Rainfall data]: {}".format(e))
                        break

                if last_sent_time is not None:
                    end_time = time.time()
                    elapsed_time = end_time - last_sent_time
                    t_diff = config["socket_send_data_seconds"] - elapsed_time
                    await a.sleep(1 if t_diff < 0 else t_diff)
                else:
                    await a.sleep(1)
        await a.sleep(1)


# Reconnect- the websocket should close automatical and open after a while to prevent block connection...
async def connect_and_reconnect():
    global ws
    global app
    while True:
        if ws is not None:
            if await ws.open() and app.start_time is not None:
                end_time = time.time()
                elapsed_time = end_time - app.start_time
                print("Time elapsed", elapsed_time)
                if elapsed_time > config["socket_reconnect_seconds"]:
                    if await ws.open():
                        await ws.close()
                        print("ws is open: " + str(await ws.open()))
                    else:
                        print("closed")
            await a.sleep(5)
        await a.sleep(2)


async def main():
    tasks = [
        app.run(),
        send_humidity_loop(),
        send_moisture_loop(),
        send_rainfall_loop(),
        send_sensor_statuses_loop(),
        connect_and_reconnect(),
    ]
    await a.gather(*tasks)

##Add services on command handler such that the service can send commands to execute these services
handler.add_service("irrigation", IrrigationService())
handler.add_service("config", config_service)

##Run the app
a.run(main())