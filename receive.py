from datetime import datetime
import json
import os
import requests
import subprocess
import sys
import threading
import traceback
import time

API_URL = os.getenv("TEMPBERRY_API_URL", None)

def log_unknown_entry(data):
    with open("unknown_entries.txt", "a") as myfile:
        myfile.write(str(data) + "\n")


def post_temperature_data(data):
    """
    Post temperature data to tempberry api
    :param data:
    :return:
    """

    with requests.Session() as s:
        try:
            print("<sending ", data, ">")
            r = s.post(API_URL, data)
            print(r)
            if r.status_code < 200 or r.status_code > 299:
                print(r.content)

            return r
        except:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
            print(datetime.now(), "post_data(): An error occured")
            print(''.join('!! ' + line for line in lines))

    return None


###################################################################################################
# MAIN
###################################################################################################

# read from rtl-433

# list of model names to completely skip
skip_models = [
    "Smoke-GS558", # unknown smoke detector
    "Proove-Security", # movement sensor, same as NExa-Security
    "Springfield-Soil", # some soil sensor, not sure whos
]

# start rtl 433 receiver with json output
result = subprocess.Popen(["rtl_433", "-F", "json"], stdout=subprocess.PIPE)

print("Processing stdout of rtl_433 -F json")

output = result.stdout

last_by_model = {}

print("waiting for output...")

for line in output:
    line = line.decode()
    print(line)
    if line.startswith("{"):
        # possible json
        code = json.loads(line)

        # check previous code by model
        model = code['model']
        if model in last_by_model and last_by_model[model] == code:
            # skip this entry
            print("<skipped (repeated)>")
            continue

        # check if this is a model that we should skip
        if model in skip_models:
            # skip this entry
            print("<skipped (by rule)>")
            continue

        # update last_by_model
        last_by_model[model] = code

        if model in ["GT-WT02", "Auriol-HG02832", "Nexus-TH"]:
            try:
                post_temperature_data(
                    {
                        'sensor_id': code['id'], 'temperature': code['temperature_C'],
                        'humidity': code['humidity'], 'battery': code['battery_ok'], 'source': 'raspberry'
                    }
                )
            except:
                print(code)
                raise
        elif model in ["Ambientweather-F007TH"]:
            sensor_id = "{}{}".format(5000, code['id'])
            try:
                post_temperature_data(
                    {
                        'sensor_id': sensor_id, 'temperature': round((code['temperature_F'] - 32)*5/9, 1),
                        'humidity': code['humidity'] * 1.0, 'battery': 0, 'source': 'raspberry'
                    }
                )
            except:
                print(code)
                raise

        elif model in ["inFactory-TH"]:
            try:
                post_temperature_data(
                    {
                        'sensor_id': code['id'], 'temperature': round((code['temperature_F'] - 32)*5/9, 1),
                        'humidity': code['humidity'] * 1.0, 'battery': 0, 'source': 'raspberry'
                    }
                )
            except:
                print(code)
                raise
        elif model in ["Opus-XT300"]:
            # {"time" : "2020-03-09 18:27:53", "model" : "Opus-XT300", "channel" : 1, "temperature_C" : 26, "moisture" : 99, "mic" : "CHECKSUM"}
            moisture = code['moisture']
            channel = code['channel']
            temperature = code['temperature_C']
            id = "{}{}".format(300, code['channel'])

            try:
               post_temperature_data(
                    {
                        'sensor_id': id, 'temperature': temperature,
                        'humidity': moisture, 'battery': 0, 'source': 'raspberry'
                    }
                )
            except:
                print(code)
                raise
        elif model in ["Acurite-606TX"]:
            # {"time" : "2022-06-22 13:36:38", "model" : "Acurite-606TX", "id" : 231, "battery_ok" : 1, "temperature_C" : 25.300, "mic" : "CHECKSUM"}
            temperature = code['temperature_C']
            id = '{}{}'.format(606, code['id'])
            battery = code['battery_ok']
            try:
               post_temperature_data(
                    {
                        'sensor_id': id, 'temperature': temperature,
                        'battery': battery, 'source': 'raspberry'
                    }
                )  
            except:
                print(code)
                raise

        else:
            log_unknown_entry(code)


# wait for thread to finish
th.join()

