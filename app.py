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


def construct_temperature_composite(ghcn_composite):
    temperature_composite = {'META' : None, 'VARS' : None, 'SERIES' : None}

    tmax_data = {'name' : 'tmax', 'data' : convert_data(ghcn_composite['TMAX'], 10)}
    tmin_data = {'name' : 'tmin', 'data' : convert_data(ghcn_composite['TMIN'], 10)}
    tavg_data = {'name' : 'tavg', 'data' : convert_data(ghcn_composite['TAVG'], 10)}

    temperature_composite['VARS'] = [ item for item in [tmax_data, tmin_data, tavg_data] if item['data'] is not None ]
    temperature_composite['META'] = {'title' : "'Temperatures by Month'", 'type' : "'month'", 'yAxis-title' : "'Degrees Celsius'"}
    temperature_composite['SERIES'] = []

    if tmax_data['data'] is not None:
        temperature_composite['SERIES'].append(build_series("'Average TMAX'", "tmax"))

    if tmin_data['data'] is not None:
        temperature_composite['SERIES'].append(build_series("'Average TMIN'", "tmin"))

    if tavg_data['data'] is not None:
        temperature_composite['SERIES'].append(build_series("'Average TAVG'", "tavg"))

    return temperature_composite

@app.route('/')
def index():
    station_list = station.get_all_station_info()
    return render_template('index.html', station_list=station_list)

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

    return render_template('station.html', station_info=station_info, ghcn_composite=ghcn_composite, temperature_composite=temperature_composite)

if __name__ == '__main__':
    app.run()
