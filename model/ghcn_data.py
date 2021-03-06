#/usr/bin/python
import psycopg2
import os
import datetime
import json
import time
from flask import Blueprint, request
import calendar

ghcn_data_blueprint = Blueprint('ghcn_data', __name__)

def build_series(name, data):
    return {'name' : name, 'data' : data, 'zIndex' : 1, 'marker' : '{ fillColor: "white", lineWidth: 2, lineColor: Highcharts.getOptions().colors[0] }'}

def convert_data(element, conversion_factor):
    return [[calendar.month_name[item['MONTH']],round(item['VALUE']) / conversion_factor] for item in element] if element is not None else None

def construct_degree_days_composite(ghcn_composite):
    degree_days_composite = {'META' : None, 'VARS' : None, 'SERIES' : None}

    avghddays_data = {'name' : 'avghddays', 'data' : convert_data(ghcn_composite['AVGHDDAYS'], 1)}
    avgcddays_data = {'name' : 'avgcddays', 'data' : convert_data(ghcn_composite['AVGCDDAYS'], 1)}

    degree_days_composite['VARS'] = [ item for item in [avghddays_data, avgcddays_data] if item['data'] is not None ]
    degree_days_composite['META'] = {'title' : "'Derived Temperature Units'", 'type' : "'month'", 'yAxis-title' : "'Number of occurences'"}
    degree_days_composite['SERIES'] = []

    if avghddays_data['data'] is not None:
        degree_days_composite['SERIES'].append(build_series("'Heating Degree Days'", "avghddays"))

    if avgcddays_data['data'] is not None:
        degree_days_composite['SERIES'].append(build_series("'Cooling Degree Days'", "avgcddays"))

    return degree_days_composite


def construct_temperature_composite(ghcn_composite):
    temperature_composite = {'META' : None, 'VARS' : None, 'SERIES' : None}

    tmax_data = {'name' : 'tmax', 'data' : convert_data(ghcn_composite['TMAX'], 10)}
    tmin_data = {'name' : 'tmin', 'data' : convert_data(ghcn_composite['TMIN'], 10)}
    tavg_data = {'name' : 'tavg', 'data' : convert_data(ghcn_composite['TAVG'], 10)}
    tmaxextreme_data = {'name' : 'tmaxextreme', 'data' : convert_data(ghcn_composite['TMAXEXTREME'], 10)}
    tminextreme_data = {'name' : 'tminextreme', 'data' : convert_data(ghcn_composite['TMINEXTREME'], 10)}

    temperature_composite['VARS'] = [ item for item in [tmax_data, tmin_data, tavg_data, tmaxextreme_data, tminextreme_data] if item['data'] is not None ]
    temperature_composite['META'] = {'title' : "'Temperatures by Month'", 'type' : "'month'", 'yAxis-title' : "'Degrees Celsius'"}
    temperature_composite['SERIES'] = []

    if tmax_data['data'] is not None:
        temperature_composite['SERIES'].append(build_series("'Average TMAX'", "tmax"))

    if tmin_data['data'] is not None:
        temperature_composite['SERIES'].append(build_series("'Average TMIN'", "tmin"))

    if tavg_data['data'] is not None:
        temperature_composite['SERIES'].append(build_series("'Average TAVG'", "tavg"))

    if tmaxextreme_data['data'] is not None:
        temperature_composite['SERIES'].append(build_series("'Extreme TMAX'", "tmaxextreme"))

    if tminextreme_data['data'] is not None:
        temperature_composite['SERIES'].append(build_series("'Extreme TMIN'", "tminextreme"))

    return temperature_composite

def construct_precip_composite(ghcn_composite):
    precip_composite = {'META' : None, 'VARS' : None, 'SERIES' : None}
    prcp_data = {'name' : 'prcp', 'data' : convert_data(ghcn_composite['PRCP'], 10)}
    snow_data = {'name' : 'snow', 'data' : convert_data(ghcn_composite['SNOW'], 1)}
    snwd_data = {'name' : 'snwd', 'data' : convert_data(ghcn_composite['SNWD'], 1)}

    precip_composite['VARS'] = [ item for item in [prcp_data, snow_data, snwd_data] if item['data'] is not None ]
    precip_composite['META'] = {'title' : "'Precipitation by Month'", 'type' : "'month'", 'yAxis-title' : "'(mm)'"}
    precip_composite['SERIES'] = []

    if prcp_data['data'] is not None:
        precip_composite['SERIES'].append(build_series("'Average Precipitation'", "prcp"))

    if snow_data['data'] is not None:
        precip_composite['SERIES'].append(build_series("'Average Snowfall'", "snow"))

    if snow_data['data'] is not None:
        precip_composite['SERIES'].append(build_series("'Average Snowdepth'", "snwd"))

    return precip_composite

def run_queries(queries, station_id):
    conn = psycopg2.connect("host='{0}' dbname='{1}' user='{2}' password='{3}'".format(os.environ['INGEST_HOST'],
                                                                                       os.environ['INGEST_DB'],
                                                                                       os.environ['INGEST_USER'],
                                                                                       os.environ['INGEST_PASS']))
    cur = conn.cursor()
    query_results = {}
    for key in queries.keys():
        query_results[key] = None
        cur.execute(queries[key], {'id' : station_id})
        for row in cur:
            record = {'VALUE' : row[0], 'MONTH' : row[1]}
            if key in query_results.keys() and query_results[key] != None:
                query_results[key].append(record)
            else:
                query_results[key] = [record]
        
            
    conn.close()
    return query_results


def get_composite_report(station_id):
    queries = {'TMAX' : '''SELECT "VALUE", "MONTH" FROM "GHCN_DATA"."GHCN_SUMMARY" WHERE "ID" = %(id)s AND "TYPE" = 'TMAXAVG' ''',
               'TMIN' : '''SELECT "VALUE", "MONTH" FROM "GHCN_DATA"."GHCN_SUMMARY" WHERE "ID" = %(id)s AND "TYPE" = 'TMINAVG' ''',
               'PRCP' : '''SELECT "VALUE", "MONTH" FROM "GHCN_DATA"."GHCN_SUMMARY" WHERE "ID" = %(id)s AND "TYPE" = 'PRCPAVG' ''',
               'SNOW' : '''SELECT "VALUE", "MONTH" FROM "GHCN_DATA"."GHCN_SUMMARY" WHERE "ID" = %(id)s AND "TYPE" = 'SNOWAVG' ''',
               'SNWD' : '''SELECT "VALUE", "MONTH" FROM "GHCN_DATA"."GHCN_SUMMARY" WHERE "ID" = %(id)s AND "TYPE" = 'SNWDAVG' ''',
               'AWDR' : '''SELECT "VALUE", "MONTH" FROM "GHCN_DATA"."GHCN_SUMMARY" WHERE "ID" = %(id)s AND "TYPE" = 'AWDRAVG' ''',
               'AWND' : '''SELECT "VALUE", "MONTH" FROM "GHCN_DATA"."GHCN_SUMMARY" WHERE "ID" = %(id)s AND "TYPE" = 'AWNDAVG' ''',
               'TAVG' : '''SELECT "VALUE", "MONTH" FROM "GHCN_DATA"."GHCN_SUMMARY" WHERE "ID" = %(id)s  AND "TYPE" = 'TAVGAVG' ''',
               'TMAXEXTREME' : '''SELECT "VALUE", "MONTH" FROM "GHCN_DATA"."GHCN_SUMMARY" WHERE "ID" = %(id)s AND "TYPE" = 'TMAXEXTREME' ''',
               'TMINEXTREME' : '''SELECT "VALUE", "MONTH" FROM "GHCN_DATA"."GHCN_SUMMARY" WHERE "ID" = %(id)s AND "TYPE" = 'TMINEXTREME' ''',
               'AVGCDDAYS' : '''SELECT "VALUE", "MONTH" FROM "GHCN_DATA"."GHCN_SUMMARY" WHERE "ID" = %(id)s AND "TYPE" = 'AVGCDDAYS' ''',
               'AVGHDDAYS' : '''SELECT "VALUE", "MONTH" FROM "GHCN_DATA"."GHCN_SUMMARY" WHERE "ID" = %(id)s AND "TYPE" = 'AVGHDDAYS' '''}
    result = run_queries(queries, station_id)
    return result
    

@ghcn_data_blueprint.route('/get_composite_report/')
def get_composite_report_json():
    station_id = request.args.get('id', None)
    return json.dumps(get_composite_report(station_id))

if __name__ == '__main__':
    from flask import Flask
    app = Flask(__name__)
    app.debug = True
    app.register_blueprint(ghcn_data_blueprint, url_prefix="/ghcn_data/")
    app.run()
