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
from django.contrib.gis.gdal import SpatialReference, CoordTransform
from django.contrib.gis.geos import fromstr

from tasks import *
from reblock.forms import *
from reblock.models import *

import topology.my_graph as mg
import topology.my_graph_helpers as mgh


def index(request):
    """A view for browsing the existing webfinches.
    """
    return render_to_response(
            'reblock/index.html',
            {'reblock':DataLayer.objects.all()},
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
        return HttpResponseRedirect('/reblock/review/')
    else:
        formset = ZipFormSet()

    c = {
            'formset':formset,
            }
    return render_to_response(
            'reblock/upload.html',
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
		print srs
                """
                geoms = checkGeometryType(layer)
                #topo_json = add.delay(1 , 2)
                topo_json = run_topology.delay(geoms, user)
                #db_json = TopologyJSON(topo_json = topo_json, author = user)
                #db_json.save()

                #plt.show()
                """
		geoms = checkGeometryType(layer)
		#print user
                scale_factor = scaleFactor(geoms)
                run_topology.delay(geoms, name = layer.name, user = user, scale_factor = scale_factor)
		# retrieve object from db
		

        '''
		srs = checkedPrj(form.cleaned_data['srs'])
		
		ds = DataSource(form.cleaned_data['file_location'])
		layer = ds[0]
		geoms = checkGeometryType(layer)
		scale_factor = scaleFactor(geoms)
		run_topology.delay(geoms, name = layer.name, user = user)
		'''

        return HttpResponseRedirect('/reblock/compute/')
        
    else: # we are asking them to review data
        # get the last upload of this user
        upload = UploadEvent.objects.filter(user=user).order_by('-date')[0]
        data_files = DataFile.objects.filter(upload=upload)
        layer_data = [ f.get_layer_data() for f in data_files ]
	
	file_path = layer_data[0]['file_location']
	ds = DataSource( file_path )
        layer = ds[0]
        srs = layer_data[0]['srs']
        
	geoms = checkGeometryType(layer)
        ct = CoordTransform(SpatialReference(srs), SpatialReference(3857))
        for feat in layer:
            geom = feat.geom # getting clone of feature geometry
            geom.transform(ct) # transforming
            #print geom
	    test = geom.json
	    print test
        
        'we should get some error if the geometry does not have a projection or has a wrong geom type'
        formset = LayerReviewFormSet( initial=layer_data )
	
    c = {
            'formset':formset,
            }
    return render_to_response(
            'reblock/review.html',
            RequestContext(request, c),
            )

@login_required
def compute(request):
    
    user = request.user
    if request.method == 'POST': # someone is editing site configuration
        pass

    else:
        # We are browsing data
        test_layers = RoadJSON2.objects.filter(author=user).order_by('-date_edited')
	
	# this gives us the db object
	# then we extract the json attrib
	myjson = test_layers[0].topo_json
	
	# we use gdal to load json as a GDAL datalayer
	new_layer= DataSource(myjson)[0]
	#print new_layer[0]
    
	srs = 3421
	
	# reproject geoms into new srs
	new_proj =[]
	coord_transform = CoordTransform(SpatialReference(srs), SpatialReference(3857))
	for feat in new_layer:
	    geom = feat.geom 
	    
	    geom.transform(coord_transform)
	    
	    new_proj.append(json.loads(geom.json))
	new_proj = json.dumps(new_proj)
	print new_proj
	    

	
	
	# we pass reprojected geoms to javascript
	
	# we display geometries on leaflet
	
    c = {
            'test_layers': test_layers,
    
            }
    return render_to_response(
            'reblock/compute.html',
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

'''def run_topology(lst, name=None, user = None, scale_factor=1):

    blocklist = new_import(lst,name,scale = scale_factor)#make the graph based on input geometry
    print blocklist
    
    for i,g in enumerate(blocklist):
        #ALL THE PARCELS
        parcels = json.loads(g.myedges_geoJSON())
        db_json = BlockJSON2(name=name, topo_json = parcels, author = user,block_index = i)
        db_json.save()

        #THE INTERIOR PARCELS
        inGragh = mgh.graphFromMyFaces(g.interior_parcels)
        in_parcels = json.loads(inGragh.myedges_geoJSON())
        db_json = InteriorJSON2(name=name, topo_json = in_parcels, author = user,block_index = i)
        db_json.save()
        
        #THE ROADS GENERATED and save generating process into the database
        road = run_once(g,name = name,user = user,block_index = i)#calculate the roads to connect interior parcels, can extract steps
        db_json = RoadJSON2(name=name, topo_json = road, author = user,block_index = i)
        db_json.save()
'''

"""
rewrite run_once function from topology, using linestring list as input

Given a list of blocks, builds roads to connect all interior parcels and
plots all blocks in the same figure.
"""

def run_once(original,name=None, user = None, block_index = 0):

    plt.figure()

    if len(original.interior_parcels) > 0:
        block = original.copy()

        # define interior parcels in the block based on existing roads
        block.define_interior_parcels()

        # finds roads to connect all interior parcels for a given block(with steps)
        block_roads = build_all_roads(block, wholepath=True,name = name, user = user)
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
    print "start creating graph based on input geometry"
    myG = graphFromLineString(lst, name, rezero,scale = scale)#create the graph. can't directly show step
    print "start clean up"
    myG = myG.clean_up_geometry(threshold, connected)#clean the graph. can't directly show step
    print "Finish cleaning up"
    print myG
    if component is None:
        return myG
    else:
        return myG.connected_components()[component]

"""
rewrite function in mgh
"""

def build_all_roads(myG, master=None, alpha=2, plot_intermediate=False,
                    wholepath=False, original_roads=None, plot_original=False,
                    bisect=False, plot_result=False, barriers=False,
                    quiet=False, vquiet=False, strict_greedy=False,
                    outsidein=False,name=None, user = None,block_index = 0):

    """builds roads using the probablistic greedy alg, until all
    interior parcels are connected, and returns the total length of
    road built. """

    if vquiet is True:
        quiet = True

    if plot_original:
        myG.plot_roads(original_roads, update=False,
                       parcel_labels=False, new_road_color="blue")

    shortest_only = False
    if strict_greedy is True:
        shortest_only = True

    added_road_length = 0
    # plotnum = 0
    if plot_intermediate is True and master is None:
        master = myG.copy()

    myG.define_interior_parcels()

    target_mypath = None
    if vquiet is False:
        print("Begin w {} Interior Parcels".format(len(myG.interior_parcels)))

    md = 100

    while myG.interior_parcels:############extract?###########
        #save remaining interior parcel to the database
        gJson = mgh.graphFromMyFaces(myG.interior_parcels).myedges_geoJSON()
        db_json = IntermediateJSON3(name=name, topo_json = gJson, author = user,step_index = len(myG.interior_parcels),block_index = block_index)
        db_json.save()
        
        result, depth = mgh.form_equivalence_classes(myG)

        # flist from result!
        flist = []

        if md == 3:
            flist = myG.interior_parcels
        elif md > 3:
            if outsidein is False:
                result, depth = mgh.form_equivalence_classes(myG)
                while len(flist) < 1:
                    md = max(result.keys())
                    flist = flist + result.pop(md)
            elif outsidein is True:
                result, depth = form_equivalence_classes(myG)
                md = max(result.keys())
                if len(result[md]) == 0:
                    md = md - 2
                flist = list(set(result[3]) - set(result.get(5, [])))

        if quiet is False:
            print("Cur max depth is {}; {}".format(md, len(flist)) +
                  " parcels at current depth. \n" +
                  "{0:.1f} new roads so far".format(added_road_length))

        # potential segments from parcels in flist

        all_paths = mgh.find_short_paths_all_parcels(myG, flist, target_mypath,
                                                 barriers, quiet=quiet,
                                                 shortest_only=shortest_only)

        # choose and build one
        target_ptup, target_mypath = mgh.choose_path(myG, all_paths, alpha,
                                                 strict_greedy=strict_greedy)

        if wholepath is False:
            added_road_length += target_mypath[0].length
            myG.add_road_segment(target_mypath[0])

        if wholepath is True:
            for e in target_mypath:
                added_road_length += e.length
                myG.add_road_segment(e)

        myG.define_interior_parcels()
        if plot_intermediate:
            myG.plot_roads(master, update=False)
            # plt.savefig("Int_Step"+str(plotnum)+".pdf", format='pdf')
            # plotnum += 1

        remain = len(myG.interior_parcels)
        if quiet is False:
            print("\n{} interior parcels left".format(remain))
        if vquiet is False:
            if remain > 300 or remain in [50, 100, 150, 200, 225, 250, 275]:
                pass
                # print "{} interior parcels left".format(remain)

    # update the properties of nodes & edges to reflect new geometry.

    myG.added_roads = added_road_length
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
