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
    temperature_composite = ghcn_data.construct_temperature_composite(ghcn_composite)
    precip_composite = ghcn_data.construct_precip_composite(ghcn_composite)
    degree_days_composite = ghcn_data.construct_degree_days_composite(ghcn_composite)
    station_dict = { station_info['ID'] : station_info }

    return render_template('station.html', station_info=station_info, ghcn_composite=ghcn_composite,  degree_days_composite=degree_days_composite,
                                           temperature_composite=temperature_composite, precip_composite=precip_composite, station_dict=station_dict)

if __name__ == '__main__':
    app.run(threaded=True)
