#!/usr/bin/env python
# Eneristics: Eclipse IoT Challenge

import pymongo
from pymongo import *
from bson.json_util import loads, dumps
import time
import pytz
from datetime import datetime, timedelta

mongo_names = dict(connection_string='mongodb://localhost:27017/', db_name='readings', tags_collection = 'sensortags',
                   weather_collection = 'weather', db_json_collection='dbjson', hvac_collection='hvac',
                   mode_key='q_temp_now', mode_rising="rising", mode_falling="falling", mode_stable="stable")
device_map = dict(sensortag1="24:71:89:C1:3E:02", sensortag2="24:71:89:1A:59:02", sensortag3="24:71:89:C0:B4:01",
                  sensortag4="24:71:89:E6:8D:82")


# db.json file info
dir_path = '/home/pi/jsonServer/'
file_name = 'db.json'
NUM_POLLS_PERIOD = 60

# Params: connection_string mongo_names['connection_string'], db mongo_names['db_name'],
# collection mongo_names['collection_name']
# Insert a bson document into the specified MongoDB. Expects
def insert_bson_mongo(connection_string, db_name, collection, bson_object) :
    client = MongoClient(connection_string)
    db = client[db_name]
    collection = db[collection]
    collection.insert_one(bson_object)
    results = collection.find({ 'created_at' : 123 })
    client.close()


def convert_time(timestamp):
    utc_time = datetime(1970, 1, 1) + timedelta(milliseconds=timestamp)
    utc_time.strftime('%A, %B %d, %Y %H:%M:%S %p UTC')
    est = utc_time.replace(tzinfo=pytz.utc).astimezone(pytz.timezone('US/Eastern'))
    est.strftime('%A, %B %d, %Y %H:%M:%S %p %Z')
    return str(est)

# return the number of periods over num_polls periods, that were labelled heating
# *****DOES NOT DESTROY CONNECTION ******
def get_heating_over_period(num_polls):
    # connect to mongo: readings-sensortags
    client = MongoClient(mongo_names['connection_string'])
    db = client[mongo_names['db_name']]
    collection = db[mongo_names['hvac_collection']]

    is_heating = False
    heating_polls = 0
    counter = 0

    for sensorttag_data in collection.find().sort("timestamp", DESCENDING).limit(num_polls):
        counter = counter + 1
        try:
            if sensorttag_data[mongo_names['mode_key']]==mongo_names['mode_rising']:
                if is_heating == False:
                    is_heating = True
                    heating_polls = heating_polls + 1
                else:
                    heating_polls = heating_polls + 1
            elif sensorttag_data[mongo_names['mode_key']]==mongo_names['mode_stable']:
                if is_heating == True:
                    heating_polls = heating_polls + 1
            elif sensorttag_data[mongo_names['mode_key']]==mongo_names['mode_falling']:
                is_heating = False
        except KeyError:
            print("key error in: " + str(sensorttag_data))

    return heating_polls

def generate_db_json() :

    # connect to mongo: readings-sensortags
    client = MongoClient(mongo_names['connection_string'])
    db = client['readings']
    collection = db['sensortags']


    json_object = {}
    json_object["role_id"] = "dbjson" #primary / hash key changed from dbjson dbjson1 Feb 20 to accomodate new columns
    millis = int(round(time.time() * 1000))  
    json_object["timestamp"] = str(millis) #sort key

    # find the latest sensortag1 and add an id=1 to it. Then add it to sensortags
    for sensortag_data in collection.find({"device_id":device_map['sensortag1']}).sort("timestamp", DESCENDING).limit(1):
        
        tagId = "st1_"
        timestamp = float(sensortag_data["timestamp"])
        timestamp = convert_time(timestamp)
        json_object[tagId+"ambient"] = sensortag_data["ambient"]       
        json_object[tagId+"humidity"] = sensortag_data["humidity"]
        json_object[tagId+"TS_EST"] = timestamp
 
    # find the latest sensortag1 and add an id=1 to it. Then add it to sensortags
    for sensortag_data in collection.find({"device_id": device_map['sensortag2']}).sort("timestamp", DESCENDING).limit(1):
        tagId = "st2_"
        timestamp = float(sensortag_data["timestamp"])
        timestamp = convert_time(timestamp)
        json_object[tagId+"ambient"] = sensortag_data["ambient"]
        json_object[tagId+"humidity"] = sensortag_data["humidity"]
        json_object[tagId+"TS_EST"] = timestamp


    # find the latest sensortag1 and add an id=1 to it. Then add it to sensortags
    for sensortag_data in collection.find({"device_id": device_map['sensortag3']}).sort("timestamp", DESCENDING).limit(1):
        tagId = "st3_"
        timestamp = float(sensortag_data["timestamp"])
        timestamp = convert_time(timestamp)
        json_object[tagId+"ambient"] = sensortag_data["ambient"]
        json_object[tagId+"humidity"] = sensortag_data["humidity"]
        json_object[tagId+"TS_EST"] = timestamp

 
    # find the latest sensortag1 and add an id=1 to it. Then add it to sensortags
    for sensortag_data in collection.find({"device_id": device_map['sensortag4']}).sort("timestamp", DESCENDING).limit(1):
        tagId = "st4_"
        timestamp = float(sensortag_data["timestamp"])
        timestamp = convert_time(timestamp)
        json_object[tagId+"ambient"] = sensortag_data["ambient"]
        json_object[tagId+"humidity"] = sensortag_data["humidity"]
        json_object[tagId+"TS_EST"] = timestamp

    # connect to mongo: readings-weather
    db = client['readings']
    collection = db[mongo_names['weather_collection']]

    # find the latest
    for weather_data in collection.find().sort("timestamp", DESCENDING).limit(1):
        print(weather_data) #for crontab /home/pi/cronlog/cron.log
        tagId = "we1_"
        json_object[tagId+"temperature"] = weather_data["temperature"]
        json_object[tagId+"humidity"] = weather_data["humidity"]
        json_object[tagId+"windUnits"] = weather_data["windUnits"]
        json_object[tagId+"pressure"] = weather_data["pressure"]
        json_object[tagId+"windDirection"] = weather_data["windDirection"]
        json_object[tagId+"windSpeed"] = weather_data["windSpeed"]
        json_object[tagId+"timestamp"] = weather_data["timestamp"]

    heating_periods = get_heating_over_period(NUM_POLLS_PERIOD)
    json_object["heating_periods"] = heating_periods
    json_object["cooling_periods"] = NUM_POLLS_PERIOD - heating_periods

    return json_object

# params writeable_json:json to put in the db.json file
# Open the file at dir_path+file_name and write the writeable_json to it
def write_db_json_file(writeable_json) :
    with open(dir_path + file_name, 'w') as f:
        f.write(writeable_json)

def write_db_json_mongo(final_json_object):
    # get mongo ready
    client = MongoClient(mongo_names['connection_string'])
    db = client[mongo_names['db_name']]
    collection = db[mongo_names['db_json_collection']]
    final_json_object =loads(final_json_object)
    collection.insert_one(final_json_object)

    # TESTING -> retrieve the last document from the db
    #time_sorted_results = collection.find().sort("insert_time", -1)
    #counter = 0
    #for single_result in time_sorted_results:
    #    if counter == 0:
    #        print("This is the latest entry: ")
    #        print(str(single_result))
    #        break
    #    break

    client.close()

# Params json_object: json object to add heat_loss to
# Add heat_loss to the json_object. Includes two KVP, kWh and BTU.
def add_heat_loss(json_object):
    heat_loss = {}
    heat_loss['"kWh"'] = 20000
    heat_loss['"BTU"'] = 40000
    json_object['"heat_loss"']= [heat_loss]
    return json_object

# Params json_object: json object to add time_to_heat to
# Add time_to_heat ('time' in minutes and 'time_to_heat' in minutes) to the json_object
def add_time_to_heat(json_object):
    heat_time = {}
    heat_time['"time"']=15
    json_object['"time_to_heat"']=[heat_time] # minutes
    return json_object

# Params json_object: json object to add insert_time as flag for identifying current db.json in mongo 
# Add insert_time to the json_object. Includes current time.
def add_insert_time(json_object):
    insert_time = {}
    insert_time['"insert_time"'] = str(int(time.time()))
    json_object['"flag_insert_time"']=[insert_time] # flag for sorting in mongo
    return json_object

# Params json_object: json object to add insert_time as flag for identifying current db.json in mongo
# Add insert_time to the json_object. Includes current time.
def add_rt_heat_loss(json_object):
    # find the latest sensortag1 and add an id=1 to it. Then add it to sensortags
    json_object["rt_hl_kwh"] = str((.0464 / .15 * 884) * (float(json_object["st3_ambient"]) - float(json_object["we1_temperature"]))/1000)
    json_object["rt_hl_btu"] = str((.0464 / .15 * 884) * (float(json_object["st3_ambient"]) - float(json_object["we1_temperature"]))/1000 * 3412)
    json_object["rt_hl_carbon"] = str((.0464 / .15 * 884) * (float(json_object["st3_ambient"]) - float(json_object["we1_temperature"])) / 1000 * .0005925)
    json_object["rt_hl_carbon_yr"] = str((.0464 / .15 * 884) * (float(json_object["st3_ambient"]) - float(json_object["we1_temperature"])) / 1000 * .0005925 * 24 * 30 * 5)
    # print("TESTING RT_HEAT_LOSS DATA: " + str(json_object))

    return json_object

# Main loop. Build the initial json, from mongodb sensortags and weather. Add various json KVPs, and output to MongoDB
# and the db.json file.
if __name__ == "__main__":

    # initial json string
    json_object= generate_db_json()

    # insert other functions here...

    # Calculate Real Time Heat Loss
    json_object = add_rt_heat_loss(json_object)


    # convert json_object to string and build db.json file
    # json_object = str(json_object).replace("u'","'")
    # json_object = str(json_object).replace("'","\"")
    # write_db_json_file(str(json_object))

    # write the final object to the DB
    json_object = str(json_object).replace("u'","'")
    json_object = str(json_object).replace("'","\"")
    write_db_json_mongo(str(json_object))
