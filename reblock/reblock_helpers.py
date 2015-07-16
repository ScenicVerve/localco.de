import os
import math
import itertools
from itertools import *
import json
import tempfile, zipfile
import cStringIO
import datetime
import numpy as np
import networkx as nx
import time
import shapefile
import StringIO

from celery.result import AsyncResult
from settings import MEDIA_ROOT
from django.core.urlresolvers import reverse

import django.contrib.gis
from django.contrib.gis.geos import *
from django.contrib.gis.db import models
from django.contrib.gis.measure import D
from django.contrib.gis.gdal import *
from django.contrib.gis.gdal import SpatialReference, CoordTransform

from tasks import *
from reblock.forms import *
from reblock.models import *
from reblock.views import *
from django.utils import text

import topology.my_graph as mg
import topology.my_graph_helpers as mgh
from django.utils import simplejson
from fractions import Fraction

import datetime, random
from django.views.generic.list import ListView

center_lat = None
center_lng = None
default_srs = 24373
	
	
def isnumber(s):
    s = str(s)
    try:
        float(s)
        return True
    except ValueError:
        try: 
            Fraction(s)
            return True
        except ValueError: 
            return False
	

def saveshp(layer = None, num = 1, offset = 0, name = "_", start = None, user = None, prid = None):
        #ori_shp = shapefile.Writer(shapefile.POLYLINE)
    ori_shp = json_gdal(layer = layer, num = num, offset = offset)
    l= []
    for feat in ori_shp:
        geom = feat.geom
        c_geom = geom.coords
        #print c_geom
        l.append(c_geom)
    points = [[[pt[0],pt[1]]for pt in poly]for poly in l]

    w = shapefile.Writer(shapefile.POLYLINE)
    
    w.poly(points)
    # get the media root (check models.py)
    # (this is the path) make a directory on media with the name of the url
    
    datt = start.datasave5_set.all().order_by('-date_edited')[0]
    #redirect link
    mypath = str(user)+"/"+str(datt.prjname)+"_"+str(datt.location)+"_"+str(prid)+"/"
    path = MEDIA_ROOT+mypath
    try:
        w.save(path+name)
        print name+" save successfull!!!!!!!!!!!!"
    except:
        pass
    #~ # zip the contents of the folder into a zipfile

    #~ # pass the zipfile file path to the html
    

def json_gdal(layer = None, num =1, offset=0):
    """
    Function to convert a json into a OGRGeojson
    In: A json layer 
    Out: An OGRGeojson : a gdal object from datasource
    """
    for la in layer[offset*num:num+offset*num]:
        myjson = la.topo_json
        new_layer= DataSource(myjson)[0]
        return new_layer    
    
    
"""
function to reproject gdal layer(in meters) to degree, and output geojson file
num is the amount of block to keep from the layer
"""

def project_meter2degree(layer = None, num = 1, offset = 0):
    layer_json = []
    for la in layer[offset*num:num+offset*num]:
    
        myjson = la.topo_json
        new_layer= DataSource(myjson)[0]
        srs = la.srs
        if not isnumber(srs):
            srs = default_srs
        new_proj =[]
        coord_transform = CoordTransform(SpatialReference(srs), SpatialReference(4326))
        for feat in new_layer:
            geom = feat.geom
                
            geom.transform(coord_transform)
                
            new_proj.append(json.loads(geom.json))
        layer_json.extend(new_proj)
    layer_json = json.dumps(layer_json)
    return layer_json

"""
function to reproject gdal layer(in meters) to degree, and output geojson file
num is the amount of block to keep from the layer
"""
def projectRd_meter2degree(layer = None, num = 1, offset = 0):
    layer_json = []
    for la in layer[offset*num:num+offset*num]:
    
        myjson = la.road_json
        new_layer= DataSource(myjson)[0]
        srs = la.srs
        if not isnumber(srs):
            srs = default_srs
        new_proj =[]
        coord_transform = CoordTransform(SpatialReference(srs), SpatialReference(4326))
        for feat in new_layer:
            geom = feat.geom
                
            geom.transform(coord_transform)
                
            new_proj.append(json.loads(geom.json))
        layer_json.extend(new_proj)
    layer_json = json.dumps(layer_json)
    return layer_json

def centroid(geom):
    lst = [Polygon(LinearRing(g.coords)).centroid for g in geom]
    lstx = [l.coords[0] for l in lst]
    lsty = [l.coords[1] for l in lst]
    return (sum(lstx) / float(len(lstx)),sum(lsty) / float(len(lsty)))
    
    
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
rewrite run_once function from topology, using linestring list as input

Given a list of blocks, builds roads to connect all interior parcels and
plots all blocks in the same figure.
"""

def run_once(original,name=None, user = None, block_index = 0, srs = None, barriers=False):

    if len(original.interior_parcels) > 0:
        block = original.copy()        
        # define interior parcels in the block based on existing roads
        block.define_interior_parcels()        
        # finds roads to connect all interior parcels for a given block(with steps)
        block_roads = build_all_roads(block, wholepath=True,name = name, user = user, srs = srs,barriers=barriers)
        
    else:
        block = original.copy()    
    roads = simplejson.dumps({"type": "FeatureCollection",
                           "features": [e.geoJSON(np.array([0, 0])) for e in block.myedges() if e.road]})
        
    block.plot_roads(master=original, new_plot=False)
    return roads


def match_barriers(b_index, original):
    """
    Function to match the indices that the user inputs with the equivalent indices of the graph.
    In: b_index (string with the user indices) : A string of integers that the user types in review.html
    Out: barrier_edges: a list of edges : a list of edges that are the barriers the user selected
    """
    b_edges = []
    if "," in b_index:
        bar_indices= [int(i) for i in b_index.split(",")]
        bar_edge = original.myedges()
         
        for index in bar_indices:
            if index <= len(bar_edge):
        
                b_edges.append(bar_edge[index])
                b = set(b_edges)
                barrier_edges = list(b)
        return barrier_edges


"""
rewrite new_import function from topology

imports the file, plots the original map, and returns
a list of blocks from the original map.
"""
def new_import(lst, name=None,scale = 1, indices=None):
    original = import_and_setup(lst,scale = scale, threshold=1)#create and clean the graph.
    print indices
    if not indices == "-":
        barriers = match_barriers(indices, original)
        mgh.build_barriers(barriers)

    #~ if isinstance(indices, list):#if indices:
        #~ barriers = match_barriers(indices, original)
        #~ print barriers
        #~ mgh.build_barriers(barriers)

    else:
        print "NO"
        # compute without 

    blocklist = original.connected_components()

    # plot the full original map
    for b in blocklist:
        # defines original geometery as a side effect,
        b.plot_roads(master=b, new_plot=False, update=True)

    
    blocklist.sort(key=lambda b: len(b.interior_parcels), reverse=True)
    print blocklist

    return blocklist
    

"""
rewrite topology's import_and_setup function using linestring as input
"""
def import_and_setup(lst,component = None,threshold=1, byblock=True, name="",scale = 1):
    # check that rezero is an array of len(2)
    # check that threshold is a float
    print "start creating graph based on input geometry"

    myG = graphFromLineString(lst, name,scale = scale)#create the graph. can't directly show step

    print "start clean up"
    myG = myG.clean_up_geometry(threshold, byblock=byblock)#clean the graph. can't directly show step
    print "Finish cleaning up"
    print myG
    if component is None:
        return myG
    else:
        return myG.connected_components()[component]

"""
rewrite function in mgh
"""

def build_all_roads(original, master=None, alpha=2, plot_intermediate=False,
                    wholepath=False, original_roads=None, plot_original=False,
                    bisect=False, plot_result=False, barriers=False,
                    quiet=False, vquiet=False, strict_greedy=False,
                    outsidein=False,name=None, user = None,block_index = 0, srs = None):

    """builds roads using the probablistic greedy alg, until all
    interior parcels are connected, and returns the total length of
    road built. """

    quiet = vquiet

    if plot_original:
        original.plot_roads(original_roads, update=False,
                       parcel_labels=False, new_road_color="blue")

    shortest_only = False
    if strict_greedy is True:
        shortest_only = True

    added_road_length = 0
    # plotnum = 0
    if plot_intermediate is True and master is None:
        master = original.copy()

    original.define_interior_parcels()
    target_mypath = None
    md = 100
    while original.interior_parcels:############extract###########
        #save remaining interior parcel to the database
        gJson = simplejson.dumps(json.loads(mgh.graphFromMyFaces(original.interior_parcels).myedges_geoJSON()))
        roads = simplejson.dumps({"type": "FeatureCollection","features": [e.geoJSON(np.array([0, 0])) for e in original.myedges() if e.road]})
        
        start = StartSign2.objects.filter(author=user).order_by('-date_edited')[0]
        number = start.bloocknum2_set.all().order_by('-date_edited')[0]
                
        ##############delay to test intermediate steps##############
        time.sleep(3)
        ############################################################

        db_json = IntermediateJSON7(name=name, topo_json = gJson, road_json = roads,author = user,step_index = len(original.interior_parcels),block_index = block_index, srs = srs, number = number, start = start)
        db_json.save()

        result, depth = mgh.form_equivalence_classes(original)

        # flist from result!
        flist = []

        if md == 3:
            flist = original.interior_parcels
        elif md > 3:
            if outsidein is False:
                result, depth = mgh.form_equivalence_classes(original)
                while len(flist) < 1:
                    md = max(result.keys())
                    flist = flist + result.pop(md)
            elif outsidein is True:
                result, depth = form_equivalence_classes(original)
                md = max(result.keys())
                if len(result[md]) == 0:
                    md = md - 2
                flist = list(set(result[3]) - set(result.get(5, [])))

        if quiet is False:
            pass

        # potential segments from parcels in flist
	try:
	    all_paths = mgh.find_short_paths_all_parcels(original, flist, target_mypath,barriers, quiet=quiet,shortest_only=shortest_only)
	    
	except nx.NetworkXNoPath:
	    
	    message = "You selected too many barriers! Try selecting less."
	    email = EmailMultiAlternatives('Open Reblock notification. Calculation Failed!',message,'openreblock@gmail.com', [user.email])
	    email.send()
	    raise IOError("Select less edges!")
	    
        # choose and build one
        target_ptup, target_mypath = mgh.choose_path(original, all_paths, alpha,
                                                 strict_greedy=strict_greedy)

        if wholepath is False:
            added_road_length += target_mypath[0].length
            original.add_road_segment(target_mypath[0])

        if wholepath is True:
            for e in target_mypath:
                added_road_length += e.length
                original.add_road_segment(e)

        original.define_interior_parcels()
        if plot_intermediate:
            original.plot_roads(master, update=False)
            # plt.savefig("Int_Step"+str(plotnum)+".pdf", format='pdf')
            # plotnum += 1

        remain = len(original.interior_parcels)
        if quiet is False:
            pass #print("\n{} interior parcels left".format(remain))
        if vquiet is False:
            if remain > 300 or remain in [50, 100, 150, 200, 225, 250, 275]:
                pass

    # update the properties of nodes & edges to reflect new geometry.
    original.added_roads = added_road_length
    return added_road_length


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
    if isnumber(srs0):
        srs = int(srs0)
    elif srs0 != None:
        try: srs = int(srs0[srs0.find(':')+1:])
        except: srs = None
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