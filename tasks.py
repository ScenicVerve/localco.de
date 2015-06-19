from celery import Celery
from webfinches.models import *
from webfinches.models import User

from webfinches.views import *
#run_once
import topology.my_graph as mg
import topology.my_graph_helpers as mgh

app = Celery('tasks', broker='amqp://guest@localhost//')

"""
rewrite topology, using linestring list as input
"""
@app.task
def run_topology(lst, user, name=None):

    blocklist = new_import(lst,name)
    
    g = blocklist[0]

    ep_geojson = g.myedges_geoJSON()
    myjs = json.loads(ep_geojson)
    #print myjs
    db_json = TopologyJSON(topo_json = myjs, author = user)
    db_json.save()
    #map_roads = run_once(blocklist)
    return None


'''
@app.task
def add(x,y):
    s = x + y
    return s

#add.delay(1,2)
'''