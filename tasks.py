from celery import Celery
from webfinches.models import *

from webfinches.views import *
#, run_once
import topology.my_graph as mg
import topology.my_graph_helpers as mgh

app = Celery('tasks', broker='amqp://guest@localhost//')

"""
rewrite topology, using linestring list as input
"""
@app.task
def run_topology(lst, name=None):

    blocklist = new_import(lst,name)
    
    g = blocklist[0]

    ep_geojson = g.myedges_geoJSON()
    myjs = json.loads(ep_geojson)
    print myjs
    #map_roads = run_once(blocklist)
    return myjs


'''
@app.task
def add(x,y):
    s = x + y
    return s

#add.delay(1,2)
'''