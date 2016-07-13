#/usr/bin/python
import psycopg2
import os
import datetime
import json
import time
from flask import Blueprint, request

ghcn_data_blueprint = Blueprint('ghcn_data', __name__)


def run_queries(queries, station_id):
    conn = psycopg2.connect("host='{0}' dbname='{1}' user='{2}' password='{3}'".format(os.environ['INGEST_HOST'],
                                                                                       os.environ['INGEST_DB'],
                                                                                       os.environ['INGEST_USER'],
                                                                                       os.environ['INGEST_PASS']))
    cur = conn.cursor()
    query_results = {}
    for key in queries.keys():
        query_results[key] = None
        cur.execute(queries[key], (station_id,))
        for row in cur:
            record = {'VALUE' : row[0], 'MONTH' : row[1]}
            if key in query_results.keys() and query_results[key] != None:
                query_results[key].append(record)
            else:
                query_results[key] = [record]
        
            
    conn.close()
    return query_results


def get_composite_report(station_id):
    queries = {'TMAX' : '''SELECT AVG("VALUE"), "MONTH" FROM "GHCN_DATA"."GHCN_TMAX" WHERE "ID" = %s AND "Q_FLAG" IS NULL GROUP BY "MONTH" ORDER BY "MONTH"''',
               'TMIN' : '''SELECT AVG("VALUE"), "MONTH" FROM "GHCN_DATA"."GHCN_TMIN" WHERE "ID" = %s AND "Q_FLAG" IS NULL GROUP BY "MONTH" ORDER BY "MONTH"''',
               'PRCP' : '''SELECT AVG("SUMMED_MONTH_YEAR"."VALUE"), "SUMMED_MONTH_YEAR"."MONTH" FROM (SELECT SUM("VALUE") AS "VALUE", "MONTH" FROM "GHCN_DATA"."GHCN_PRCP"
                                                                                         WHERE "ID" = %s AND "Q_FLAG" IS NULL GROUP BY "MONTH", "YEAR") "SUMMED_MONTH_YEAR" 
                           GROUP BY "SUMMED_MONTH_YEAR"."MONTH" ORDER BY "MONTH"''',
               'SNOW' : '''SELECT AVG("SUMMED_MONTH_YEAR"."VALUE"), "SUMMED_MONTH_YEAR"."MONTH" FROM (SELECT SUM("VALUE") AS "VALUE", "MONTH" FROM "GHCN_DATA"."GHCN_SNOW"
                                                                                         WHERE "ID" = %s AND "Q_FLAG" IS NULL GROUP BY "MONTH", "YEAR") "SUMMED_MONTH_YEAR" 
                           GROUP BY "SUMMED_MONTH_YEAR"."MONTH" ORDER BY "MONTH"''',
               'SNWD' : '''SELECT AVG("VALUE"), "MONTH" FROM "GHCN_DATA"."GHCN_SNWD" WHERE "ID" = %s AND "Q_FLAG" IS NULL GROUP BY "MONTH" ORDER BY "MONTH"''',
               'AWDR' : '''SELECT AVG("VALUE"), "MONTH" FROM "GHCN_DATA"."GHCN_AWDR" WHERE "ID" = %s AND "Q_FLAG" IS NULL GROUP BY "MONTH" ORDER BY "MONTH"''',
               'AWND' : '''SELECT AVG("VALUE"), "MONTH" FROM "GHCN_DATA"."GHCN_AWND" WHERE "ID" = %s AND "Q_FLAG" IS NULL GROUP BY "MONTH" ORDER BY "MONTH"''',
               'TAVG' : '''SELECT AVG("VALUE"), "MONTH" FROM "GHCN_DATA"."GHCN_TAVG" WHERE "ID" = %s AND "Q_FLAG" IS NULL GROUP BY "MONTH" ORDER BY "MONTH"''',
               'TMAXEXTREME' : '''SELECT MAX("VALUE"), "MONTH" FROM "GHCN_DATA"."GHCN_TMAX" WHERE "ID" = %s AND "Q_FLAG" IS NULL GROUP BY "MONTH" ORDER BY "MONTH"''',
               'TMINEXTREME' : '''SELECT MIN("VALUE"), "MONTH" FROM "GHCN_DATA"."GHCN_TMIN" WHERE "ID" = %s AND "Q_FLAG" IS NULL GROUP BY "MONTH" ORDER BY "MONTH"''',
               'AVGCDDAYS' : '''SELECT AVG("YEAR_MONTH_COUNT"."COUNT"), "YEAR_MONTH_COUNT"."MONTH" FROM (SELECT COUNT(CASE WHEN "VALUE" > 183 THEN 1 END) AS "COUNT", "MONTH" FROM "GHCN_DATA"."GHCN_TAVG"
                                                                                                   WHERE "ID" = %s GROUP BY "YEAR", "MONTH") "YEAR_MONTH_COUNT"
                                GROUP BY "MONTH" ORDER BY "MONTH"''',
               'AVGHDDAYS' : '''SELECT AVG("YEAR_MONTH_COUNT"."COUNT"), "YEAR_MONTH_COUNT"."MONTH" FROM (SELECT COUNT(CASE WHEN "VALUE" < 183 THEN 1 END) AS "COUNT", "MONTH" FROM "GHCN_DATA"."GHCN_TAVG"
                                                                                                   WHERE "ID" = %s GROUP BY "YEAR", "MONTH") "YEAR_MONTH_COUNT"
                                GROUP BY "MONTH" ORDER BY "MONTH"'''}
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
