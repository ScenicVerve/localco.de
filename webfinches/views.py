import os
import math
import itertools
from itertools import *
import json
import tempfile, zipfile
import cStringIO
import datetime
import numpy as np
from matplotlib import pyplot as plt


from django.http import HttpResponse
from django.core.servers.basehttp import FileWrapper
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response, redirect
from django.template import RequestContext
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User

from django.contrib.auth.views import login
from django.core.mail import send_mail
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout

import django.contrib.gis
from django.contrib.gis.geos import *
from django.contrib.gis.db import models
from django.contrib.gis.measure import D
from django.contrib.gis.gdal import *

from webfinches.forms import *
from webfinches.models import *

import topology.my_graph as mg
import topology.my_graph_helpers as mgh


def index(request):
    """A view for browsing the existing webfinches.
    """
    return render_to_response(
            'webfinches/index.html',
            {'webfinches':DataLayer.objects.all()},
            )

@login_required
def upload(request):
    """A view for uploading new data.
    """
    user = request.user
    if request.method == 'POST':
        upload = UploadEvent(user=user)
        upload.save()
        formset = ZipFormSet(request.POST, request.FILES)
        for form in formset:
            if form.is_valid() and form.has_changed():
                data_file = form.save(upload)
        return HttpResponseRedirect('/webfinches/review/')
    else:
        formset = ZipFormSet()

    c = {
            'formset':formset,
            }
    return render_to_response(
            'webfinches/upload.html',
            RequestContext(request, c),
            )

@login_required
def review(request):
    """
    A view for uploading new data.
    """
    user = request.user
    if request.method == 'POST': # someone is giving us data
        formset = LayerReviewFormSet(request.POST)
        
        if formset.is_valid():
            # For every layer in the layer form, write a PostGIS object to the DB
            for form in formset:

                srs = checkedPrj(form.cleaned_data['srs'])

                ds = DataSource(form.cleaned_data['file_location'])
                
                layer = ds[0]
                geoms = checkGeometryType(layer)              
                topo_json = run_topology(geoms)
                db_json = TopologyJSON(topo_json = topo_json, author = user)
                db_json.save()
                plt.show()

        return HttpResponseRedirect('/webfinches/compute/')
        
    else: # we are asking them to review data
        # get the last upload of this user
        upload = UploadEvent.objects.filter(user=user).order_by('-date')[0]
        data_files = DataFile.objects.filter(upload=upload)
        layer_data = [ f.get_layer_data() for f in data_files ]
        
        'we should get some error if the geometry does not have a projection of has a wrong geom type'
        formset = LayerReviewFormSet( initial=layer_data )
        
    c = {
            'formset':formset,
            }
    return render_to_response(
            'webfinches/review.html',
            RequestContext(request, c),
            )

@login_required
def compute(request):
    
    user = request.user
    if request.method == 'POST': # someone is editing site configuration
        pass

    else:
        # We are browsing data
        test_layers = PostLayerG.objects.filter(author=user).order_by('-date_edited')
        #test_layers = TopologyJSON.objects.filter(author=user).order_by('-date_edited')
        
    c = {
            'test_layers': test_layers,
    
            }
    return render_to_response(
            'webfinches/compute.html',
            RequestContext(request, c),
            )

"""
flatten all the geometry in the geometry collection
"""
def flattenAll(geoCo):
    lst = []
    for geo in geoCo:
        if not "Multi" in geo.geom_type:
            lst.append(geo)
        else:
            lst.extend(flattenAll(geo))
    return lst

def checkGeometryType(gdal_layer, srs=None):
    #datasource layer
    layer = gdal_layer
    # Get the GEOS geometries from the SHP file
    geoms = layer.get_geoms(geos=True)
    geom_type = layer.geom_type.name

    lst = []
    for geom in geoms:
        if srs:
            for geom in geoms:
                geom.srid = srs

        if geom.geom_type == 'Polygon':#return the boundary of the polygon as a linestring
            lst.append(geom.boundary)
        elif geom.geom_type == 'LinearRing' or geom.geom_type == 'LineString':#return the linestring as a closed one
            lst.append(geom.close_rings)
        elif "Multi" in geom.geom_type:#this is a geometry collection, return the flattened list
            lst.extend(flattenAll(geom))			
        else:#not supported geometry type, raise exception
            raise IOError(geom.geom_type+"is the wrong type of geometry to process")
    
    if len(lst)>0 and len(lst)<=1200:
        return lst
    
    elif len(lst)>1200:
        raise IOError(str(len(lst))+" too many polygons to process, maximum number of Polygons is 1,200")
    else:
        raise IOError("Your file is invalid")
    
"""
rewrite topology, using linestring list as input
"""
def run_topology(lst, name=None):

    blocklist = new_import(lst,name)
    g = blocklist[0]

    ep_geojson = g.myedges_geoJSON()
    myjs = json.loads(ep_geojson)
    
    map_roads = run_once(blocklist)
    return myjs

"""
rewrite run_once function from topology, using linestring list as input
"""
def run_once(blocklist):
    map_roads = 0
    plt.figure()

    for original in blocklist:
        if len(original.interior_parcels) > 0:
            block = original.copy()

            # define interior parcels in the block based on existing roads
            block.define_interior_parcels()

            # finds roads to connect all interior parcels for a given block
            block_roads = mgh.build_all_roads(block, wholepath=True)
            map_roads = map_roads + block_roads
        else:
            block = original.copy()

        block.plot_roads(master=original, new_plot=False)

    return map_roads

"""
rewrite new_import function from topology
"""
def new_import(lst, name=None):

    original = import_and_setup(lst)

    blocklist = original.connected_components()

    print("This map has {} block(s). \n".format(len(blocklist)))

    plt.figure()
    # plot the full original map
    for b in blocklist:
        # defines original geometery as a side effect,
        b.plot_roads(master=b, new_plot=False, update=True)

    blocklist.sort(key=lambda b: len(b.interior_parcels), reverse=True)

    return blocklist
    

"""
rewrite topology's import_and_setup function using linestring as input
"""
def import_and_setup(lst,component = 0,threshold=1,rezero=np.array([0, 0]), connected=False, name=""):
    # check that rezero is an array of len(2)
    # check that threshold is a float
    myG = graphFromLineString(lst, name, rezero)

    myG = myG.clean_up_geometry(threshold, connected)
    myG = graphFromLineString(lst,name) #create the graph from MyGragh class in topology
    print "start clean up"
    myG = myG.clean_up_geometry(threshold, connected)
    print myG
    if connected is True:
        return myG
    else:
        return myG.connected_components()[component]


"""
The function that use topology library to create MyGraph by input lineString
"""
def graphFromLineString(lst,name = None,rezero=np.array([0, 0])):
    nodedict = dict()
    plist = []
    for l in lst:
        l = np.array(l.coords)
        nodes = []
        for k in l:
            #print len(k)
            k = k-rezero
            myN = mg.MyNode(k)
            if myN not in nodedict:
                nodes.append(myN)
                nodedict[myN] = myN
            else:
                nodes.append(nodedict[myN])
            edges = [(nodes[i], nodes[i+1]) for i in range(0, len(nodes)-1)]
            plist.append(mg.MyFace(edges))

    myG = mg.MyGraph(name=name)

    for p in plist:
        for e in p.edges:
            myG.add_edge(mg.MyEdge(e.nodes))

    print("data loaded")

    return myG
    
"""
The function that check the projection information according to the file uploaded to the database
"""
def checkedPrj(srs0):
    if srs0.isnumeric():
        srs = int(srs0)
    elif srs0 != None:
        srs = int(srs0[srs0.find(':')+1:])
    else:
        #no srs information is found, raise exception
        print 'no srs information is found'
        srs = None
    return srs


"""
return the unit of the input gdal data source layer
"""
def getUnit(gdal_layer):
	uni = {}
	uni['UNIT'] = gdal_layer.srs['UNIT']
	uni['PRJUnit'] = gdal_layer.srs['PROJCS'][3]
	return gdal_layer.srs
