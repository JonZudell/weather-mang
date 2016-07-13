#/usr/bin/python
from flask import Flask, request, session, g, redirect, url_for, render_template
import psycopg2
import os
import calendar

app = Flask(__name__)
app.debug = True

from model import search, station, ghcn_data
app.register_blueprint(search.search_blueprint, url_prefix='/api/')
app.register_blueprint(station.station_blueprint, url_prefix='/api/')
app.register_blueprint(ghcn_data.ghcn_data_blueprint, url_prefix='/api/')

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
        precip_composite['SERIES'].append(build_series("'Average Rainfall'", "prcp"))

    if snow_data['data'] is not None:
        precip_composite['SERIES'].append(build_series("'Average Snowfall'", "snow"))

    if snow_data['data'] is not None:
        precip_composite['SERIES'].append(build_series("'Average Snowdepth'", "snwd"))

    return precip_composite


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search_results/')
def search_results():
    term = request.args.get('term', None)
    results = search.search(term)
    return render_template('search_results.html', results=results, term=term)

@app.route('/station_info/')
def station_info():
    station_id = request.args.get('station_id', None)
    station_info = station.get_station_info(station_id)

    ghcn_composite = ghcn_data.get_composite_report(station_id)
    temperature_composite = construct_temperature_composite(ghcn_composite)
    precip_composite = construct_precip_composite(ghcn_composite)
    degree_days_composite = construct_degree_days_composite(ghcn_composite)
    station_dict = { station_info['ID'] : station_info }

    return render_template('station.html', station_info=station_info, ghcn_composite=ghcn_composite,  degree_days_composite=degree_days_composite,
                                           temperature_composite=temperature_composite, precip_composite=precip_composite, station_dict=station_dict)

if __name__ == '__main__':
    app.run(threaded=True)
