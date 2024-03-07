'''This module contains code to connect to the wifi. To config wifi check in config.json file..'''

#Todo : Add multiple wifi config, allowing the controller to do try and error, if fails, try another wifi..This should be done to servers also

import network as net
import uasyncio as a

# SSID - network name
# pwd - password
# attempts - how many time will we try to connect to WiFi in one cycle
# delay_in_msec - delay duration between attempts
async def wifi_connect(SSID: str, pwd: str, attempts: int = 3, delay_in_msec: int = 200) -> net.WLAN:
   
    wifi = net.WLAN(net.STA_IF)

    wifi.active(1)
    count = 1

    while not wifi.isconnected() and count <= attempts:
        print("WiFi connecting. Attempt {}.".format(count))
        if wifi.status() != net.STAT_CONNECTING:
            wifi.connect(SSID, pwd)
        await a.sleep_ms(delay_in_msec)
        count += 1

    if wifi.isconnected():
        print("ifconfig: {}".format(wifi.ifconfig()))
    else:
        print("Wifi not connected.")

    return wifi

