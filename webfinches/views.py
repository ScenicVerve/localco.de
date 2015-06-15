import os
import math
import itertools
from itertools import *
import json
import tempfile, zipfile
import cStringIO
import datetime

from django.http import HttpResponse
from django.core.servers.basehttp import FileWrapper
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response, redirect
from django.template import RequestContext
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User

from webfinches.forms import *
from webfinches.models import *
from django.contrib.auth.views import login
from django.core.mail import send_mail
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout

import django.contrib.gis
from django.contrib.gis.geos import *
from django.contrib.gis.db import models
from django.contrib.gis.measure import D
from django.contrib.gis.gdal import *



import numpy as np
from matplotlib import pyplot as plt
import webfinches.topology.my_graph_helpers as mgh
import webfinches.topology.my_graph as mg


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
                '''
                Check srs data
                '''

                loaded_layer = load_layer(form, user)
                #if form.cleaned_data['srs'].isnumeric():
                #    srs = int(form.cleaned_data['srs'])
                #else:
                #    srs = int(form.cleaned_data['srs'][form.cleaned_data['srs'].find(':')+1:])
                ## Write the layer to the DB
                #loaded_layer = load_layer(form.cleaned_data['file_location'], srs, user)

                srs = checkedPrj(form.cleaned_data['srs'])
                ds = DataSource(form.cleaned_data['file_location'])
                layer = ds[0]
                #print getUnit(layer)
                geoms = checkGeometryType(layer)
                
                run_topology(geoms)

                #myG = graphFromLineString(geoms,'testGragh') #create the graph from MyGragh class in topology
                #print myG
                #print "start clean up"
                #myG = myG.clean_up_geometry(1, False)
                #print myG
                
                # Write the layer to the DB
                #loaded_layer = load_layer(form.cleaned_data['pathy'], srs, user)
                #print loaded_layer

                #print loaded_layer.author, loaded_layer.date_added, loaded_layer.geometry_type
                
        return HttpResponseRedirect('/webfinches/configure/')
        
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
                    

#@login_required
#def browse(request):
#    """A view for browsing and editing layers"""
#    user = request.user
#    if request.method == 'POST': # someone is giving us data
#        formset = LayerReviewFormSet(request.POST)
#        if formset.is_valid():
#            for form in formset:
#                if form.cleaned_data['srs'].isnumeric():
#                    srs = int(form.cleaned_data['srs'])
#                else:
#                    srs = int(form.cleaned_data['srs'][form.cleaned_data['srs'].find(':')+1:])
#                # Write the layer to the DB
#                loaded_layer = load_layer(form.cleaned_data['file_location'], srs, user)
#                
#        return HttpResponseRedirect('/webfinches/configure/')
#
#    else:
#        layers = DataLayer.objects.filter(author=user).order_by('-date_edited')
#        browsing_data = [ l.get_browsing_data() for l in layers ]
#        # do I need to convert these to dicts?
#        formset = LayerBrowseFormSet(initial=browsing_data)
#    
#    c = {
#            'formset': formset,            
#            }
#    return render_to_response(
#            'webfinches/browse.html',
#            RequestContext( request, c ),
#            )
#
#@login_required
#def browse_empty(request):
#    c = {
#            'layers': None,
#    
#            }
#    return render_to_response(
#            'webfinches/browse_empty.html',
#            RequestContext(request, c),
#            )

@login_required
def compute(request):
	
	
	
	
	pass

@login_required
def configure(request):
    """
    A view that contains ajax scripts for sorting and dealing with layers,
    in order to build SiteConfigurations
    """
    user = request.user
    if request.method == 'POST': # someone is editing site configuration
        #Here we are getting some user variables
        layers = PostLayerG.objects.filter(author=user).order_by('-date_edited')
        # Get site_layer from checkboxes
        site_id = request.POST.get("site_layer")
        site_layer = PostLayerG.objects.get(id=site_id)
        # We get the SiteConfiguration name entered by the user
        config_name = request.POST.get("name") 
        # Get radius for query
        try:
            radius = int(request.POST.get("radius"))
        except ValueError:
            # We give them a predefined Radius if no radius or an invalid radius is selected
            radius = 1000 
        # We get the SRS code. If the user doesn't provide an srs code, use the site's srs code
        if len(request.POST.get("srs")) == 0: 
            config_srs = site_layer.layer_srs
        elif request.POST.get("srs").isnumeric():
            config_srs = int(request.POST.get("srs"))
        else:
            config_srs = int(request.POST.get("srs")[request.POST.get("srs").find(':')+1:])
                    
        # Get other_layers from checkboxes
        other_ids = request.POST.getlist("other_layers")
        if len(other_ids) > 0:
            other_layers = [PostLayerG.objects.get(id=other_layers_id) for other_layers_id in other_ids]
            # Create a PostSiteConfig with the layers
            configuration = load_configuration(author=user, config_name=config_name, site_layer=site_layer, other_layers=other_layers, config_srs=config_srs, radius=radius)
            print configuration, configuration.site.all()[0].features.all()
            
        else:
            configuration = load_configuration(author=user, config_name=config_name, site_layer=site_layer, config_srs=config_srs, radius=radius)
            print configuration, configuration.site.all()[0].features.all()
            
        
        return HttpResponseRedirect('/webfinches/create_sites/')

    else:
        # We are browsing data
        test_layers = PostLayerG.objects.filter(author=user).order_by('-date_edited')
        
    c = {
            'test_layers': test_layers,
    
            }
    return render_to_response(
            'webfinches/configure.html',
            RequestContext(request, c),
            )


"""
rewrite topology, using linestring list as input
"""
def run_topology(lst, name=None):

    blocklist = new_import(lst,name)

    g = blocklist[0]

    ep_geojson = g.myedges_geoJSON()
    print ep_geojson

    map_roads = run_once(blocklist)

    plt.show()

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
flatten all the geometry in the geometry collection
"""
def flattenAll(geoCo):
    lst = []
    for geo in geoCo:
        if not len(geo)>1:
            lst.append(geo)
        else:
            lst.extend(flattenAll(geo))
    return lst

"""
The function that will check (and flatten) the input shape file
if it contains certain geometry to process, it will flatten the geometry collection and return as linestrings
otherwise, it raise a exception
"""
def checkGeometryType(gdal_layer):
    #datasource layer
    layer = gdal_layer
    # Get the GEOS geometries from the SHP file
    geoms = layer.get_geoms(geos=True)
    geom_type = layer.geom_type.name
	
    lst = []
    
    geoms = flattenAll(geoms)#flatten process
    
    for geom in geoms:
        if geom.geom_type == 'Polygon':#return the boundary of the polygon as a linestring
			lst.append(geom.boundary)
        elif geom.geom_type == 'LinearRing' or geom.geom_type == 'LineString':#return the linestring as a closed one
			lst.append(geom.close_rings)		
        else:#not supported geometry type, raise exception
            raise IOError(geom.geom_type+"is the wrong type of geometry to process")
    
    
    return lst

    
    
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


"""
Reproject the file if needed based on the result of checkprj and getunit function
"""
def reProject():
	
	pass


"""
This function loads shape files to the DB. Every geometry is an individual numpy array
with the vertices as tuples
"""
def load_shp(layer, srs):
    #print layer.srs
    # Get the layer name
    geom_type = layer.geom_type
    geoms = layer.get_geoms(geos=True)
    if srs:
        for geom in geoms:
            geom.srid= srs
    # If the geometries are polygons, turn them into linestrings.
    if geom_type == 'Polygon' or geom_type == 'MultiPolygon':
        geoms = [geom.boundary for geom in geoms]

    shapes = []
    # For every geometry, get their GIS Attributes and save them in a new object.
    for num, geom in enumerate(geoms):
        verts = geom.coords
        'here we are going to plug-in eleannas code that translates geometries into np arrays'
    
        # save the object to the DB
        #db_geom = PostGeometries(id_n = num, name = name, srs = srs, atribs = str_dict, geom = geom)
        #db_geom.save()
        #shapes.append(db_geom)
    return shapes

"""
This function loads shape files to the DB and serializes their attributes. Every object is collection of features
with a dictionary as a property.
"""
def load_layer(form, author):
    shp_path = form.cleaned_data['file_location']
    if form.cleaned_data['srs'].isnumeric():
        srs = int(form.cleaned_data['srs'])
    else:
        srs = None #int(form.cleaned_data['srs'][form.cleaned_data['srs'].find(':')+1:])
        
    # Set a GDAL datsource
    print shp_path
    ds = DataSource(shp_path)
    layer = ds[0]
    # Get the layer name
    name = layer.name
    geometry_type = layer.geom_type.name
    
    #db_layer = PostLayerG(layer_name=name, layer_srs=srs, author=author, geometry_type=geometry_type)
    #db_layer.save()
    
    # load the shapes to the db
    shapes = load_shp(layer, srs)
    # For every geometry, get their GIS Attributes and save them in a new object.
    #for shape in shapes:
    #    db_layer.features.add(shape)
    #return db_layer

#"""
#This function loads site configurations to the DB and relates them to other PostGeom objects as site and other_layers. 
#Every object is an individual configuration with a site, site id, srs for transformation, and PostGeom objects.
#"""
#def load_configuration(author, config_name, site_layer, other_layers=None, radius=1000, config_srs=None):
#    if config_srs == None:
#        config_srs = site_layer.layer_srs
#    
#    # Create the configuration db object
#    db_config = PostConfigurationB(author=author, config_name=config_name, radius=radius, config_srs=config_srs)
#    # Save it to the DB
#    db_config.save()
#    # Add the site foreign key relationship
#    db_config.site.add(site_layer)
#    
#    # For every other layer in other_layers, add the m2m relationship
#    if other_layers:
#        for other_layer in other_layers:
#            db_config.other_layers.add(other_layer)
#    return db_config


"""
This function takes a postgis query, and turns it into a Finches geoJSON
"""
def query_to_json(query, site=False, other_sites=False, srs= None):
    # this will have to change to the configuration srs
    geometries = []
    # for every shape in the query
    for shape in query:
        geometry = shape.geom
        # maybe we will reproject all of them into the site's coordinate system
        if srs:
            geometry = shape.geom.transform(srs, True)
        # get a geoJSON object
        geometry = json.loads(geometry.json)
        # create a blank dictionary
        geom_dict = { }
        # add the geometry to the dict
        geom_dict['geometry'] = geometry
        # add a feature tag to the dict
        geom_dict['type'] = 'Feature'
        # get the GIS attribute dictionary into a single dict entry
        geom_dict['properties'] = eval(shape.atribs)
        # add the dictionary to a list of geometries
        geometries.append(geom_dict)
    # get the name of the layer
    site_name = query[0].name
    # if this is the site layer, name it like that
    if site:
        site_name = 'site'
    # if these are other sites, name them like that
    if other_sites:
        site_name = 'other_sites'
    # create the geoJSON for this layer
    geojson_dict = {"type": "Layer", "name":site_name, "contents":{"type": "Feature Collection", "features":geometries}}
    return geojson_dict
    
def temp_zip(data):
    # Writes a temporary zipfile with any string input and cleans it up afterwards.
    
    zipdata = cStringIO.StringIO() # Create the file object
    zip_file = zipfile.ZipFile(zipdata, "a") # Create the zipfile
    i = -1
    for json in data: # Get individual jsons from sitesets
        i += 1
        zip_file.writestr(str(i) + '.txt',json) # Write individual txt files into zip file
    zip_file.close()
    zipdata.flush()
    ret_zip = zipdata.getvalue() # Gets the data from the temp file object before deleting it
    #zipdata.close() # Deletes the temp file object
    
    # generate the file
    response = HttpResponse(FileWrapper(zipdata), 'rb')
    response['Content-Disposition'] = 'attachment; filename=site_set.zip'
    zipdata.seek(0)
    return response
    

