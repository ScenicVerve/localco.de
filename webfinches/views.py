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
                scale_factor = scaleFactor(geoms)
                
                topo_json = run_topology(geoms, name = layer.name, user = user, scale_factor = 0.1)
                
                plt.show()

        return HttpResponseRedirect('/webfinches/compute/')
        
    else: # we are asking them to review data
        # get the last upload of this user
        upload = UploadEvent.objects.filter(user=user).order_by('-date')[0]
        data_files = DataFile.objects.filter(upload=upload)
        layer_data = [ f.get_layer_data() for f in data_files ]
        
        'we should get some error if the geometry does not have a projection or has a wrong geom type'
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
        #test_layers = PostLayerG.objects.filter(author=user).order_by('-date_edited')
        test_layers = TopoJSON.objects.filter(author=user).order_by('-date_edited')
        #print test_layers.all()
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
        if not len(geo.boundary)>1:
            lst.append(geo.boundary)
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
        elif len(geom)>1:#this is a geometry collection, return the flattened list
            lst.extend(flattenAll(geom))			
        else:#not supported geometry type, raise exception
            raise IOError(geom.geom_type+"is the wrong type of geometry to process")
    
    
    
    
    if len(lst)>0 and len(lst)<=6000:
        return lst
    
    elif len(lst)>6000:
        raise IOError(str(len(lst))+" too many polygons to process, maximum number of Polygons is 1,200")
    else:
        raise IOError("Your file is invalid")
    
"""
rewrite topology, using linestring list as input, save data to the database
"""
def run_topology(lst, name=None, user = None, scale_factor=1):

    blocklist = new_import(lst,name,scale = scale_factor)#make the graph based on input geometry
    
    for i,g in enumerate(blocklist):
        js = {}
        #ALL THE PARCELS
        js['all'] = json.loads(g.myedges_geoJSON())
        
        #THE INTERIOR PARCELS
        inGragh = mgh.graphFromMyFaces(g.interior_parcels)
        js['interior'] = json.loads(inGragh.myedges_geoJSON())
        
        #THE ROADS GENERATED  
        js['road'] = run_once(g)#calculate the roads to connect interior parcels, can extract steps
        
        lst.append(js)
        lst_json = json.dumps(js)
        db_json = TopoJSON(name=name, topo_json = lst_json, author = user,blockNum = i)
        db_json.save()

"""
rewrite run_once function from topology, using linestring list as input

Given a list of blocks, builds roads to connect all interior parcels and
plots all blocks in the same figure.
"""
def run_once(original):
    plt.figure()

    if len(original.interior_parcels) > 0:
        block = original.copy()

        # define interior parcels in the block based on existing roads
        block.define_interior_parcels()

        # finds roads to connect all interior parcels for a given block(with steps)
        block_roads = mgh.build_all_roads(block, wholepath=True)
    else:
        block = original.copy()
    
    roads = json.dumps({"type": "FeatureCollection",
                           "features": [e.geoJSON() for e in block.myedges() if e.road]})
        
    block.plot_roads(master=original, new_plot=False)
    return roads


"""
rewrite new_import function from topology

imports the file, plots the original map, and returns
a list of blocks from the original map.
"""
def new_import(lst, name=None,scale = 1):

    original = import_and_setup(lst,scale = scale)#create and clean the graph. 
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
def import_and_setup(lst,component = None,threshold=1,rezero=np.array([0, 0]), connected=False, name="",scale = 1):
    # check that rezero is an array of len(2)
    # check that threshold is a float
    myG = graphFromLineString(lst, name, rezero,scale = scale)#create the graph. can't directly show step
    print "start clean up"
    myG = myG.clean_up_geometry(threshold, connected)#clean the graph. can't directly show step
    print myG
    if component is None:
        return myG
    else:
        return myG.connected_components()[component]


"""
The function that use topology library to create MyGraph by input lineString
"""
def graphFromLineString(lst,name = None,rezero=np.array([0, 0]),scale = 1):
    nodedict = dict()
    plist = []
    for l in lst:
        l = np.array(l.coords)
        nodes = []
        for k in l:#k is coordinates
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
    if scale != 1:
        myG = rescale_mygraph(myG,rezero,scale)
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
scaleFactor function, judge and get scale factor of the input geometries
"""
def scaleFactor(geoms):
    if checkedPrj:#contain srs information
        return 1.0
    elif checkDistunguish:#fulfil 2 decimal places criteria
        area = aveArea(geoms)
        if area<10:
            return 20.0/area
        elif area >100:
            return 80.0/area
        else:
            return 1.0
    else:
        area = aveArea(geoms)
        return 50.0/area

"""
rescale graph from original topology
"""
def rescale_mygraph(myG, rezero=np.array([0, 0]), rescale=np.array([1, 1])):

    """returns a new graph (with no interior properties defined), rescaled under
    a linear function newloc = (oldloc-rezero)*rescale  where all of those are
    (x,y) numpy arrays.  Default of rezero = (0,0) and rescale = (1,1) means
    the locations of nodes in the new and old graph are the same.
    """

    scaleG = mg.MyGraph()
    for e in myG.myedges():
        n0 = e.nodes[0]
        n1 = e.nodes[1]
        nn0 = mg.MyNode((n0.loc-rezero)*rescale)
        nn1 = mg.MyNode((n1.loc-rezero)*rescale)
        scaleG.add_edge(mg.MyEdge((nn0, nn1)))

    return scaleG


"""
check if the geos are distinguishable(defined by threshold)
"""
def checkDistunguish(geoms, threshold=0.001):
    c = abs( geoms[0].coords[0][0] - geoms[0].coords[1][0])
    return c>threshold
    
"""
calculate the average area of all parcels
"""
def aveArea(geoms):
    lst = [Polygon(LinearRing(g.coords)).area for g in geoms]
    return sum(lst) / float(len(lst))

"""
return the unit of the input gdal data source layer
"""
def getUnit(gdal_layer):
	uni = {}
	uni['UNIT'] = gdal_layer.srs['UNIT']
	uni['PRJUnit'] = gdal_layer.srs['PROJCS'][3]
	return gdal_layer.srs
