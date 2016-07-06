#/usr/bin/python
import psycopg2
import os
import datetime
import json
import time
from flask import Blueprint, request
import station
class Trie:
    def __str__(self):
        result = '{ ' + 'SEARCH_TERM_VALUE : {0}, CHILDREN : {1}'.format(self.search_term_value, child_result) + ' }'
        return result

    def __init__(self, search_term_value=None, weight=0, parent=None):
        self.parent = parent
        self.search_term_value = search_term_value
        self.matches = tuple()
        self.children = []

    def child_values(self):
        return [ child.search_term_value for child in self.children ]

    def search(self, string):
        return self.search_stack(list(string[::-1]))

    def search_stack(self, stack):
        if len(stack) == 0:
            return self
        else:
            char = stack.pop()
            if char in self.child_values():
                child = [ child for child in self.children if char == child.search_term_value ][0]
                return child.search_stack(stack)
            else:
                return None
            
    def lv_search(self, term, start_distance=2, consumable_distance=2, index=0):
        result = set()
        #is suitable_match
        if consumable_distance - index > len(term) - len(self.term_value()):
            #print 'FOUND MATCH'
            if len(self.matches) > 0:
                distance = start_distance - (consumable_distance - index)
                result |= set(self.matches)

        #must be searched further
        if consumable_distance - index > 0 and len(term) > index:                
            for child in self.children:
                if child.search_term_value == term[index]:
                    #match condition no cost
                    search_result = child.lv_search(term, start_distance=start_distance, consumable_distance=consumable_distance + 1, index=index + 1)
                    if search_result:
                        if search_result not in result:
                            result |= search_result
            #print term, self.term_value()
            #insertion
                search_result = child.lv_search(term, start_distance=start_distance, consumable_distance=consumable_distance - 1, index=index)
                if search_result:
                    if search_result not in result:
                        result |= search_result
                        
            #insertion
            search_result = self.lv_search(term, start_distance=start_distance, consumable_distance=consumable_distance, index=index + 1)
            if search_result:
                if search_result not in result:
                    result |= search_result
                    

        if len(result) > 0:
            return result

        
    def insert(self, string, match):
        return self.insert_stack(list(string[::-1]), match)

    def insert_stack(self, stack, match):
        if len(stack) == 0:
            #I am the result
            if match not in self.matches:
                self.matches = self.matches + (match,)
        else:
            char = stack.pop()
            if char in self.child_values():
                #grab child
                child = [ child for child in self.children if char == child.search_term_value ][0]
                child.insert_stack(stack,match)
            else:
                #create new child
                child = Trie(search_term_value=char, parent=self)
                child.insert_stack(stack,match)
                self.children.append(child)

    def term_value(self):
        if self.parent is None:
            return ''
        return self.parent.term_value() + self.search_term_value

search_blueprint = Blueprint('search', __name__)
trie_query = '''SELECT "NAME" AS "SEARCH_TERM", "ID" AS "MATCH" FROM "META"."STATIONS" WHERE "META"."STATIONS"."WMO_ID" <> ''
                UNION ALL
                SELECT UPPER("META"."COUNTRIES"."NAME") AS "SEARCH_TERM", "META"."STATIONS"."ID" as "MATCH" FROM "META"."COUNTRIES", "META"."STATIONS"
                    WHERE SUBSTRING("META"."STATIONS"."ID" FOR 2) = "META"."COUNTRIES"."CODE" AND "META"."STATIONS"."WMO_ID" <> ''
                UNION ALL
                SELECT UPPER("META"."STATES"."NAME") AS "SEARCH_TERM", "META"."STATIONS"."ID" AS "MATCH" FROM "META"."STATES", "META"."STATIONS" 
                    WHERE "META"."STATIONS"."STATE" = "META"."STATES"."CODE" AND "META"."STATIONS"."WMO_ID" <> ''
                UNION ALL
                SELECT UPPER("META"."STATIONS"."ID") AS "SEARCH_TERM", "META"."STATIONS"."ID" AS "MATCH" FROM "META"."STATIONS"
                    WHERE "META"."STATIONS"."WMO_ID" <> ''  '''
 

trie = None
trie_update_time = None
def get_trie():
    global trie
    global trie_update_time
    
    if trie is None or trie_update_time is None or trie_update_time < datetime.datetime.now() - datetime.timedelta(days=1):
        conn = psycopg2.connect("host='{0}' dbname='{1}' user='{2}' password='{3}'".format(os.environ['INGEST_HOST'],
                                                                                           os.environ['INGEST_DB'],
                                                                                           os.environ['INGEST_USER'],
                                                                                           os.environ['INGEST_PASS']))
        cur = conn.cursor()
        cur.execute(trie_query)
        search_terms = []
        for row in cur:
            search_terms.append({'SEARCH_TERM' : row[0],
                              'MATCH' : (row[1],)})
        new_trie = Trie()
        for term in search_terms:
            new_trie.insert(term['SEARCH_TERM'], term['MATCH'])

        conn.close()
        trie = new_trie
        trie_update_time = datetime.datetime.now()
    return trie

def search(term):
    start = time.time()
    get_trie()
    search_matches = trie.lv_search(term.upper())
        
    if search_matches:
        result = {'RESULTS' : [], 'TIME' : time.time() - start }
        for match in list(search_matches):
            result['RESULTS'].append(station.get_station_info(match[0]))
        return result
    else:
        return None
    

@search_blueprint.route('/')
def run_search():
    term = request.args.get('term',None)
    return json.dumps(search(term))
#TODO: SYNONYMS

if __name__ == '__main__':
    from flask import Flask
    app = Flask(__name__)
    app.debug = True
    app.register_blueprint(search_blueprint, url_prefix="/search")
    app.run()
