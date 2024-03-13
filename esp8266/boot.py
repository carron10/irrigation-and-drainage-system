# boot.py -- run on boot-up

# D0 (GPIO16) - Pin(16)
# D1 (GPIO5) - Pin(5)
# D2 (GPIO4) - Pin(4)
# D3 (GPIO0) - Pin(0)
# D4 (GPIO2) - Pin(2)
# D5 (GPIO14) - Pin(14)
# D6 (GPIO12) - Pin(12)
# D7 (GPIO13) - Pin(13)
# D8 (GPIO15) - Pin(15)
#highest_moisture=408
#moderate_moisture=433
#low_moisture=690

# Objectives
#---Communication to server--- 
#1. Connect to server
#2. Register sensors--this is registering all sensors that are available---[To: Find a way to remove this step and make sure the server already know the sensors]
#3. fire sensor connected event / send information that a sensor is connected... [same as disconnection]
#4.  to send sensor readings to server after X mins/second as defined on the config file [or from the server]
#    --data to be sent in objective 4 above include the reading,time,and the sensor that initiated the record/

#----Communication From the server----
#1. Send config data[modify parameters] to the controller board, as stated in objective 4 above--- the server can be able to modify the interval on which the controller will send data
#2. Switch irrigation on/off--that is send information to control the behaviour of the modules
#3. ---send ping---/to check if a sensor is on/off