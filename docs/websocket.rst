.. _websockets:

WebSocket URLs and Events
=========================

Introduction
------------

The micro controllers will be connected to the server using websocket. Websocket are good to allow real time communication between the server and the micro controller.
When an event happen in the micro control this, data will be sent to the server specifying the event. Below is the Websocket URL that will be used and the list of some of the 
event. There is only one url for all the communication. Simular the client(which is the dashboard) will connect to the server using websocket, this is good for sending data that need real time communication or fror debuging

Micro Controller WebSocket URL
-------------------------------

**URL**: ws://[IP_ADDRESS/DOMAIN]/

**Description**: Websocket for communication between controlleer board and server.

**Events**:

- **temperature**:This is the event fired for new temperature record, the data below will be sent to the server when this even happen.
    .. code-block:: json

        {
            "event": "temperature",
            "data": 
            {
            "time":8273663,
            "record": 223
            }
        }

    Upon receiving the above data the server will have to decide on what to do with the data, save into the data or some computation

- **irrigation_started**: This event is fired when irrigation is starting.
    .. code-block:: json

        {
            "event": "irrigation_started",
            "data": {
           "time": 8273663,
           "zones": ["zone1", "zone2"]
            }
        }

    As from the above examples, one can see that all the data sent from the controller(s) to the server will be in the format

    .. code-block:: json

        {
            "event": "event name",
            "data": "Data here"
        }

    More other events are:

- **irrigation_stopped**: This event is fired when irrigation is starting.
- **sensor_disconnected**: Fired when of of the sensor disconnect. The data will be as below.
    .. code-block:: json

        {
            "event": "sensor_disconnected",
            "data": 
            {
            "time":1122,
            "sensor":"humidity and sensor"
            }
        }

- **humidity**: Fired on receiving humidity record.
- **soil_moisture**: Fired on receiving soil moisture record.



Client WebSocket
---------------------------

**URL**: ws://[IP_ADDRESS/DOMAIN]/clients/:id

**Description**: Connect the client into the server, *id* is the user_id of the client e.g. The client doesn't usual send data to the server using 
websocket. Therefore the above events are events that will be fired in the client side upon receiving data from the server: given that the user is in the page which require websocket

**Events**:

- **temperature**: Temperature, this is data sent to the client if there want to view temperature in real time.
- **humidity**: Event fired when the user want to view humidity in real time.

Many more data can be sent to client if they connect to the websocket url above...