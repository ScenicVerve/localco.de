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
    '''
    Function to check if the nput is number or not
    '''
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
    '''
    Function that saves a json layer as a shape file and compresses it in a zip format.
    In: layer : A json layer
    Out: shapefile : 
    '''
    #convert json to OGRGeojson
    ori_shp = json_gdal(layer = layer, num = num, offset = offset)
    l= []
    for feat in ori_shp:
        geom = feat.geom
        c_geom = geom.coords
        #create a list with the coordinates of the polygons
        l.append(c_geom)
    #create a list of lists of the points	
    points = [[[pt[0],pt[1]]for pt in poly]for poly in l]
    #create a shapefile writer
    w = shapefile.Writer(shapefile.POLYLINE)
    #write the points of the polygons as a shapefile  
    w.poly(points)

    # get the media root (check models.py)
    # (this is the path) make a directory on media with the name of the url
    
    datt = start.datasave5_set.all().order_by('-date_edited')[0]
    #redirect link
    mypath = str(user)+"/"+str(datt.prjname)+"_"+str(datt.location)+"_"+str(prid)+"/"
    print MEDIA_ROOT
    path = MEDIA_ROOT+"/uploads/"+mypath+"source/"
    print path
    try:
        w.save(path+name)
        print name+" save successfull!!!!!!!!!!!!"
    except:
        pass


def zipSave(name = "Python.zip", start = None, user = None, prid = None):
    '''
    Function that zips all shapefiles of the related project
    In: name, start model, username, project id
    Out: zip file for shapefiles
    '''
    datt = start.datasave5_set.all().order_by('-date_edited')[0]
    #redirect link
    
    mypath = str(user)+"/"+str(datt.prjname)+"_"+str(datt.location)+"_"+str(prid)+"/"
    path2 = MEDIA_ROOT+"/uploads/"+mypath
    if not os.path.isdir(path2):
	os.path.mkdir(path2)
    filename = path2+str(prid)+"_"+name
    zipf = zipfile.ZipFile(filename, 'w', compression = zipfile.ZIP_DEFLATED)
    zipdir(path2+"source/", zipf)
    zipf.close()
    return filename
    

def zipdir(path2, ziph):
    '''
    Function that zips all files in the path
    In: path
    Out: zip file
    '''
    # ziph is zipfile handle
    for root, dirs, files in os.walk(path2):
        for fily in files:
	    #write zip file
	    ziph.write(os.path.join(root, fily), arcname=fily)
        
	    
def json_gdal(layer = None, num =1, offset=0):
    '''
    Function to convert a json into a OGRGeojson
    In: A json layer 
    Out: An OGRGeojson : a gdal object from datasource
    '''
    for la in layer[offset*num:num+offset*num]:
        myjson = la.topo_json
        new_layer= DataSource(myjson)[0]
        return new_layer


def project_meter2degree(layer = None, num = 1, offset = 0, topo=True):
    '''
    Function to reproject gdal layer(in meters) to degree, and output geojson file
    num is the amount of block to keep from the layer
    In: layer : a json layer with a meter or feet projection
    Out: json : a json reprojected to decimal degrees in order to be displayed on a background map
    '''
    layer_json = []
    for la in layer[offset*num:num+offset*num]:
        if topo:
            myjson = la.topo_json
        else:
            myjson = la.road_json
	#convert json to gdal object    
        new_layer= DataSource(myjson)[0]
	#get the srs
        srs = la.srs
	#check if srs is not numerical
        if not isnumber(srs):
	    #if not numerical assign default srs
            srs = default_srs
        new_proj =[]
	#reproject gdal layer
        coord_transform = CoordTransform(SpatialReference(srs), SpatialReference(4326))
        for feat in new_layer:
            geom = feat.geom               
            geom.transform(coord_transform)               
            new_proj.append(json.loads(geom.json))
        layer_json.extend(new_proj)
    #save new layer as a json
    layer_json = json.dumps(layer_json)
    return layer_json


def flattenAll(geoCo):
    '''
    Function to flatten all the geometry in the geometry collection and returns a list of linestring objects
    In: geoCo : geometry collection
    Out: lst : a flattened list of linestring objects 
    '''
    lst = []
    for geo in geoCo:
        if not len(geo.boundary)>1:
            lst.append(geo.boundary)
        else:
            lst.extend(flattenAll(geo))
    return lst

def checkGeometryType(gdal_layer, srs=None):
    '''
    Function to check the type of the input geometry and returns a list of linestring objects
    In: gdal layer : a datasource layer
    Out: lst: a list of linestring objects
    '''
    #datasource layer
    layer = gdal_layer
    # Get the GEOS geometries from the SHP file
    geoms = layer.get_geoms(geos=True)
    geom_type = layer.geom_type.name

    lst = []
    for geom in geoms:
	#check if there is an srs
        if srs:
            for geom in geoms:
                geom.srid = srs
	#if type is polygon 
        if geom.geom_type == 'Polygon':#return the boundary of the polygon as a linestring
            lst.append(geom.boundary)
	#if type is a LinearRing
        elif geom.geom_type == 'LinearRing' or geom.geom_type == 'LineString':#return the linestring as a closed one
            lst.append(geom.close_rings)
	#if it is a geometry collection call flattenAll() function and return a flattened list
        elif len(geom)>1:
            lst.extend(flattenAll(geom))			
        else:#not supported geometry type, raise exception
            raise IOError(geom.geom_type+"is the wrong type of geometry to process")
    return lst
    #if len(lst)>0 and len(lst)<=6000:
    #    return lst
    #
    #elif len(lst)>6000:
    #    raise IOError(str(len(lst))+" too many polygons to process, maximum number of Polygons is 6000")
    #else:
    #    raise IOError("Your file is invalid")


def run_once(original,name=None, user = None, block_index = 0, srs = None, barriers=False):
    '''
    Rewrite run_once function from topology, using linestring list as input

    Given a list of blocks, builds roads to connect all interior parcels and
    plots all blocks in the same figure.
    In: original : graph
    Out: roads : all the roads that connect interior parcels
    '''
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
    '''
    Function that matches the indices that the user inputs with the equivalent indices of the graph.
    In: b_index (string with the user indices) : A string of integers that the user types in review.html
    Out: barrier_edges: a list of edges : a list of edges that are the barriers the user selected
    '''
    b_edges = []
    #split the string based on commas to get the integers as a list
    if "," in b_index:
        bar_indices= [int(i) for i in b_index.split(",")]
	#get the edges of the original graph
        bar_edge = original.myedges()
         
        for index in bar_indices:
	    #check if the user indices exist in the indices of the graph
            if index <= len(bar_edge):
		#create a list of the edges that the user selected
                b_edges.append(bar_edge[index])
		#create a set of the edges to remove duplicate barriers
                b = set(b_edges)
		#create a list of the final barriers
                barrier_edges = list(b)
        return barrier_edges


def new_import(lst, name=None,scale = 1, indices=None):
    '''
    Rewrite new_import function from topology
    '''
    '''
    Function that imports the file, plots the original map, and returns
    a list of blocks from the original map.
    In: lst, indices : linestring objects and edges as linestrings input from the user as barriers
    Out: blocklist : a list of blocks from the original map
    '''
    #create and clean the graph.
    original = import_and_setup(lst,scale = scale, threshold=1)
    
    #if there are indices from the user input
    if not indices == "-":
        barriers = match_barriers(indices, original)
	#call build_barriers function from topology.my_graph_helpers()
        mgh.build_barriers(barriers)
    else:
	# compute without 
	pass

    blocklist = original.connected_components()

    # plot the full original map
    for b in blocklist:
        # defines original geometery as a side effect,
        b.plot_roads(master=b, new_plot=False, update=True)
    
    blocklist.sort(key=lambda b: len(b.interior_parcels), reverse=True)
    return blocklist
    

def import_and_setup(lst,component = None,threshold=1, byblock=True, name="",scale = 1):
    '''
    Rewrite topology's import_and_setup function using linestring as input
    In: lst : geometry as a list of linestrings
    Out: myG : graph from linestrings
    '''
    print "start creating graph based on input geometry"
    #create the graph. can't directly show step
    myG = graphFromLineString(lst, name,scale = scale)
    print "start clean up"
    #clean the graph. can't directly show step
    myG = myG.clean_up_geometry(threshold, byblock=byblock)
    print "Finish cleaning up"
    print myG
    
    if component is None:
        return myG
    else:
        return myG.connected_components()[component]


def build_all_roads(original, master=None, alpha=2, plot_intermediate=False,
                    wholepath=False, original_roads=None, plot_original=False,
                    bisect=False, plot_result=False, barriers=False,
                    quiet=False, vquiet=False, strict_greedy=False,
                    outsidein=False,name=None, user = None,block_index = 0, srs = None):

    '''
    Builds roads using the probablistic greedy alg, until all
    interior parcels are connected, and returns the total length of road built.
    In: original : graph 
    Out: added_road_lenght : total lenght of roads built
    '''
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
    
    while original.interior_parcels:
        #save remaining interior parcel to the database
        gJson = simplejson.dumps(json.loads(mgh.graphFromMyFaces(original.interior_parcels).myedges_geoJSON()))
        roads = simplejson.dumps({"type": "FeatureCollection","features": [e.geoJSON(np.array([0, 0])) for e in original.myedges() if e.road]})
        
        start = StartSign2.objects.filter(author=user).order_by('-date_edited')[0]
        number = start.bloocknum2_set.all().order_by('-date_edited')[0]
                
        #delay to test intermediate steps
        #time.sleep(3)
	
	#save the intermediate steps
        db_json = IntermediateJSON7(name=name, topo_json = gJson, road_json = roads,author = user,step_index = len(original.interior_parcels),block_index = block_index, srs = srs, number = number, start = start)
        db_json.save()

        result, depth = mgh.form_equivalence_classes(original)

        # flist from result
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
        #try create minimal paths
	try:
	    all_paths = mgh.find_short_paths_all_parcels(original, flist, target_mypath,barriers, quiet=quiet,shortest_only=shortest_only)
	    
	#if user has selected too many barriers raise error
	except nx.NetworkXNoPath:
	    #send email to notify the user that the calculation failed because too many barriers are selected
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

        remain = len(original.interior_parcels)
        if quiet is False:
            pass #print("\n{} interior parcels left".format(remain))
        if vquiet is False:
            if remain > 300 or remain in [50, 100, 150, 200, 225, 250, 275]:
                pass

    # update the properties of nodes & edges to reflect new geometry.
    original.added_roads = added_road_length
    return added_road_length


def graphFromLineString(lst,name = None,rezero=np.array([0, 0]),scale = 1):
    '''
    The function that use topology library to create MyGraph by input lineString
    In: lst : geometry as a list of linestrings
    Out: myG : graph from linestrings
    '''
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
       
    
def checkedPrj(srs0):
    '''
    Function that checks the projection information according to the file uploaded to the database
    In: srs : initial srs
    Out: srs : checked srs
    '''
    #check if srs is numerical
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


def rescale_mygraph(myG, rezero=np.array([0, 0]), rescale=np.array([1, 1])):
    '''
    rescale_mygraph from original topology
    '''
    '''
    Function that returns a new graph (with no interior properties defined), rescaled under
    a linear function newloc = (oldloc-rezero)*rescale  where all of those are
    (x,y) numpy arrays.  Default of rezero = (0,0) and rescale = (1,1) means
    the locations of nodes in the new and old graph are the same.
    '''
    scaleG = mg.MyGraph()
    for e in myG.myedges():
        n0 = e.nodes[0]
        n1 = e.nodes[1]
        nn0 = mg.MyNode((n0.loc-rezero)*rescale)
        nn1 = mg.MyNode((n1.loc-rezero)*rescale)
        scaleG.add_edge(mg.MyEdge((nn0, nn1)))

    return scaleG


'''
These functions are not used in the current version of open reblock
The scale factor is default to 1 in review.views.py
'''
#def scaleFactor(geoms):
#
#    '''
#    Function that checks and gets scale factor of the input geometries
#    In: geoms : geometry as linestrings
#    Out:area : rescaled geoms
#    '''
#    #contain srs information
#    if checkedPrj:
#        return 1.0
#    #fulfil 2 decimal places criteria
#    elif checkDistunguish:
#        area = aveArea(geoms)
#        if area<10:
#            return 20.0/area
#        elif area >100:
#            return 80.0/area
#        else:
#            return 1.0
#    else:
#        area = aveArea(geoms)
#        return 50.0/area
#
#
#def checkDistunguish(geoms, threshold=0.001):
#    '''
#    Function that checks if the geos are distinguishable (defined by threshold)s
#    '''
#    c = abs( geoms[0].coords[0][0] - geoms[0].coords[1][0])
#    return c>threshold
#    
#    
#def aveArea(geoms):
#    '''
#    Function that calculates the average area af all the parcels
#    '''
#    lst = [Polygon(LinearRing(g.coords)).area for g in geoms]
#    return sum(lst) / float(len(lst))
#
#
#def getUnit(gdal_layer):
#    '''
#    Function that returns the units of the input gdal datasource layer
#    '''
#    uni = {}
#    uni['UNIT'] = gdal_layer.srs['UNIT']
#    uni['PRJUnit'] = gdal_layer.srs['PROJCS'][3]
#    return gdal_layer.srs
