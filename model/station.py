#/usr/bin/python
import psycopg2
import os
import datetime
import json
import time
from flask import Blueprint, request

station_blueprint = Blueprint('station', __name__)

stations = {}
states = {}
countries = {}
inventory = {}

def build_countries(cur):
    countries_query = '''SELECT * FROM "META"."COUNTRIES"'''
    cur.execute(countries_query)
    for row in cur:
        countries[row[0]] = row[1]

def build_states(cur):
    states_query= '''SELECT * FROM "META"."STATES"'''
    cur.execute(states_query)
    for row in cur:
        states[row[0]] = row[1]


def build_inventory(cur):
    inventory_query = '''SELECT "ID", "ELEMENT", "FIRSTYEAR", "LASTYEAR" FROM "META"."INVENTORY"
                         WHERE "ID" IN (SELECT "ID" FROM "META"."STATIONS" WHERE "WMO_ID" <> '')
                         AND "ELEMENT" IN (SELECT "ELEMENT" FROM "META"."ELEMENTS_DEFINITION") '''
    cur.execute(inventory_query)
    for row in cur:
        if row[0] in inventory.keys():
            inventory[row[0]].append({'ELEMENT' : row[1], 'FIRSTYEAR' : row[2], 'LASTYEAR' : row[3]})
        else:
            inventory[row[0]] = [{'ELEMENT' : row[1], 'FIRSTYEAR' : row[2], 'LASTYEAR' : row[3]}]
    

def build_stations(cur):
    station_info_query = '''SELECT * FROM "META"."STATIONS" WHERE "WMO_ID" <> '' '''
    cur.execute(station_info_query)
    for row in cur:
        station_info = {}
        station_info['ID'] = row[0]
        station_info['COUNTRY'] = countries[row[0][0:2]] if row[0][0:2] in countries.keys() else None
        station_info['LATITUDE'] = row[1]
        station_info['LONGITUDE'] = row[2]
        station_info['ELEVATION'] = row[3]
        station_info['STATE'] = states[row[4]] if row[4] in states.keys() else None
        station_info['NAME'] = row[5]
        station_info['INVENTORY'] = inventory[row[0]] if row[0] in inventory.keys() else None
      
        stations[row[0]] = station_info

def build_data():
    conn = psycopg2.connect("host='{0}' dbname='{1}' user='{2}' password='{3}'".format(os.environ['INGEST_HOST'],
                                                                                       os.environ['INGEST_DB'],
                                                                                       os.environ['INGEST_USER'],
                                                                                       os.environ['INGEST_PASS']))
    cur = conn.cursor()
    build_countries(cur)
    build_states(cur)
    build_inventory(cur)
    build_stations(cur)

    conn.close()

def get_station_info(station_id):
    if len(stations.keys()) == 0:
        build_data()
    
    if station_id in stations.keys():
        return stations[station_id]
    else:
        return None

@station_blueprint.route('/')
def get_station_info_json():
    station_id = request.args.get('id', None)
    return json.dumps(get_station_info(station_id))

if __name__ == '__main__':
    from flask import Flask
    app = Flask(__name__)
    app.debug = True
    app.register_blueprint(station_blueprint, url_prefix="/station/")
    app.run()
