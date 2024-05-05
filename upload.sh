cd esp8266
k=$(find . -maxdepth 1 -type f -print)
mpremote fs cp $k :
cd main_fc
k2=$(find . -type f -print)
# echo $k2
mpremote fs cp $k2 :main_fc/
mpremote soft-reset
mpremote reset