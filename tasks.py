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
'''
@app.task
def run_topology(lst, user, name=None):

    blocklist = new_import(lst,name)
    
    g = blocklist[0]

    ep_geojson = g.myedges_geoJSON()
    myjs = json.loads(ep_geojson)
    #print myjs
    db_json = TopoSaveJSON(topo_json = myjs, author = user)
    db_json.save()
    #map_roads = run_once(blocklist)

    return None
'''    

@app.task
def run_topology(lst, name=None, user = None):
    scale_factor = 1
    blocklist = new_import(lst,name,scale = scale_factor)#make the graph based on input geometry
    
    for i,g in enumerate(blocklist):
        js = {}
        #ALL THE PARCELS
        js['all'] = json.loads(g.myedges_geoJSON())
        
        #THE INTERIOR PARCELS
        inGragh = mgh.graphFromMyFaces(g.interior_parcels)
        js['interior'] = json.loads(inGragh.myedges_geoJSON())
        
        #THE ROADS GENERATED and save generating process into the database
        js['road'] = run_once(g,name = name,user = user)#calculate the roads to connect interior parcels, can extract steps
        
        lst.append(js)
        
        #save the output into the database
        lst_json = json.dumps(js)
        print lst_json
        db_json = TopoSaveJSON(name=name, topo_json = lst_json, author = user,index = i, kind = "output")
        db_json.save()
