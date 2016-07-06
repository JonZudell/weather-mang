#/usr/bin/python
from flask import Flask, request, session, g, redirect, url_for, render_template
import psycopg2
import os

app = Flask(__name__)
app.debug = True

from model import search, station, ghcn_data
app.register_blueprint(search.search_blueprint, url_prefix='/api/')
app.register_blueprint(station.station_blueprint, url_prefix='/api/')
app.register_blueprint(ghcn_data.ghcn_data_blueprint, url_prefix='/api/')

def construct_temperature_composite(ghcn_composite):
    temperature_composite = {'META' : None,
                             'VARS' : None,
                             'SERIES' : None}
    tmax_data = {'name' : 'tmax', 'data' : [[item['MONTH'],round(item['VALUE'])] for item in ghcn_composite['TMAX']]} if ghcn_composite['TMAX'] is not None else None
    tmin_data = {'name' : 'tmin', 'data' : [[item['MONTH'],round(item['VALUE'])] for item in ghcn_composite['TMIN']]} if ghcn_composite['TMIN'] is not None else None
    tavg_data = {'name' : 'tavg', 'data' : [[item['MONTH'],round(item['VALUE'])] for item in ghcn_composite['TAVG']]} if ghcn_composite['TAVG'] is not None else None
    temperature_composite['VARS'] = [ item for item in [tmax_data, tmin_data, tavg_data] if item is not None ]
    temperature_composite['META'] = {'title' : "'Average Temperatures by Month'", 'type' : "'month'", 'yAxis-title' : "'tenths of &#7451;'"}
    
    temperature_composite['SERIES'] = [{'name' : "'Average TMAX'", 'data' : 'tmax', 'zIndex' : 1, 'marker' : '{ fillColor: "white", lineWidth: 2, lineColor: Highcharts.getOptions().colors[0] }'},
                                       {'name' : "'Average TMIN'", 'data' : 'tmin', 'zIndex' : 1, 'marker' : '{ fillColor: "white", lineWidth: 2, lineColor: Highcharts.getOptions().colors[0] }'},
                                       {'name' : "'Average TAVG'", 'data' : 'tavg', 'zIndex' : 1, 'marker' : '{ fillColor: "white", lineWidth: 2, lineColor: Highcharts.getOptions().colors[0] }'}]
    return temperature_composite

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
    return render_template('station.html', station_info=station_info, ghcn_composite=ghcn_composite, temperature_composite=temperature_composite)

if __name__ == '__main__':
    app.run()
