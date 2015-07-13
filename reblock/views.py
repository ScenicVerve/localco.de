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


from django.http import HttpResponse
from django.core.servers.basehttp import FileWrapper
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response, redirect, render
from django.template import RequestContext
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse

from django.contrib.auth.views import login
from django.core.mail import send_mail
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.contrib.auth.models import User, UserManager

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

from reblock.models import UserProfile
from django.utils import text

import topology.my_graph as mg
import topology.my_graph_helpers as mgh
from django.utils import simplejson
from fractions import Fraction
from slugify import slugify


import datetime, random
from django.shortcuts import render_to_response, get_object_or_404
from django.core.mail import send_mail

from django.views.generic.list import ListView
from django.utils import timezone

center_lat = None
center_lng = None
default_srs = 24373

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
	    
		
	    elif not form.has_changed():
		return render_to_response(
		'reblock/browse_empty.html',
		{})
		
		#print 'no shp found'
		#return render_to_response(
		#'reblock/browse_empty.html',
		#{})

	    
	#    else:
	#	print 'no prj found'
	#
	#	return render_to_response(
	#	'reblock/browse_empty.html',
	#	{})
	#    elif not form.has_changed():
	#	return render_to_response(
	#	'reblock/browse_empty.html',
	#	{})
			
    else:
        formset = ZipFormSet()

    c = {
            'formset':formset,
            }
    return render_to_response(
            'reblock/upload.html',
            RequestContext(request, c),
            )


def register(request):
    context = RequestContext(request)
    registered = False

    if request.method == 'POST':
        user_form = UserForm(request.POST)
	
	if User.objects.filter(username=request.POST['username']).exists():
	    return render_to_response(
		'reblock/username_exists.html',
		{},
		context)
	
	else:    
	    #if user_form.is_valid():
	    # Save the user's form data to the database.
	    username = request.POST.get("username")
	    user_email = request.POST.get("email")
	    user_pwd1 = request.POST.get("password1")
	    user_pwd2 = request.POST.get("password2")
	    
	    if user_pwd1 == user_pwd2:
		user = User.objects.create_user(username, user_email, user_pwd1)
		user.save()
		registered = True
		message = 'Congratulations! You are registered! Please click on the link to log in to your profile.'+' '+'http://127.0.0.1:8000/login/'
		#message = 'Congratulations! You are registered! Please click on the link to log in to your profile.'+' '+'http://openreblock.berkeley.edu/login/'
		email = EmailMultiAlternatives('Openreblock - Registration confirmation',message,'openreblock@gmail.com', [user_email])
	    	email.send()
		return render_to_response(
		'reblock/registration_complete.html',
		{},
		context)
	    
	    else:
		registered = False
		return render_to_response(
		'reblock/register.html',{'user_form': user_form, 'registered': registered}, context)
	    ##    else:
	    #user = user_form.save()
	    #password1 =user.set_password(user.password)
	    #password2 =user.set_password(user.password)
	    #config_password1 = request.POST.get("password1")
	    #config_password2 = request.POST.get("password2")
	    #
	    
	    #    if config_password1 and config_password1 == config_password2:
	    #	final_password = config_password1
	    #	#print 'password match'
	    #	user.save()
	    #	registered = True
	    #	email = EmailMultiAlternatives('test','You are registered!','eleannapan@gmail.com', ['eleannapan@gmail.com'])
	    #	email.send()
	    #	return render_to_response(
	    #	'reblock/registration_complete.html',
	    #	{},
	    #	context)
	    #    
	    #    elif config_password1 and config_password1 != config_password2:
	    #	#password1 != password2:
	    #	print "password mismatch"
	    #	#raise forms.ValidationError("Passwords don't match")
	    #	registered = False
	    #	#print user_form.errors
	    #	return render_to_response(
	    #	 'reblock/register.html',
	    #	#{'user_form': user_form, 'registered': registered},
	    #	context)
	    ##    else:
	    #	print user_form.errors
    else:
	user_form = UserForm()
    
	return render_to_response(
		'reblock/register.html',
		{'user_form': user_form, 'registered': registered},
		context)

		
def forgot_password(request):
    context = RequestContext(request)
    registered = False
    if request.method == 'POST':
	#print 1111
        user_form = UserForm(request.POST)
	new = NewPassword(request.POST)
	if User.objects.filter(username=request.POST['username']).exists():
	    #print 11111
	    
	    config_username = request.POST.get("username")
	    user = User.objects.get(username__exact=config_username)
	    new_password1 = request.POST.get("new_password1")
	    user.set_password(new_password1)
	    #new_password2 = request.POST.get("new_password2")
	    user_email = user.email
	    #print user_email
	    
	    user.save()
	    message = 'Your new password has changed to: '+ new_password1+' '+'Use it to log back in openreblock.berkeley.edu'
	    email = EmailMultiAlternatives('password change',message ,'openreblock@gmail.com', [user_email])
	    email.send()
	    return HttpResponseRedirect('/set_new_password/') #this redirects correct

	else:
	    #print 2222
	    return render_to_response(
	    'reblock/forgot_password.html',
	    {'user_form': user_form, 'registered': registered},
	    context)
	    #go to register

    return render(request, 'reblock/forgot_password.html', {'new': NewPassword})


def set_new_password(request):
    context = RequestContext(request)
    
    #registered = False
    #if request.method == 'POST':
	#user_form = UserForm(request.POST)
	#if User.objects.filter(username=request.POST['username']).exists():
	#    u = User.objects.get(username__exact = username)
	#    u.set_password('new password')
	#    u.save()
    return render_to_response(
	'reblock/set_new_password.html',
	{},
	context)


#def password_change(request):
#    if request.method == 'POST':
#        form = PasswordChangeForm(user=request.user, data=request.POST)
#        if form.is_valid():
#            form.save()   
#    else:
#	pass

		
#def retrieve_password(request):
#    context = RequestContext(request)
#	    
#		
#
#    #form = UserForgotPasswordForm(None, request.POST)
#
#    #if form.is_valid():
#	
#	#form.save(from_email='eleannapan@gmail.com', email_template_name='/reblock/forgot_password/')
#	#form.save()
#    config_password1 = User.objects.filter(user_pwd1=request.POST['password1'])
#    email = EmailMultiAlternatives('test',config_password1,'eleannapan@gmail.com', ['eleannapan@gmail.com'])
#    email.send()
#	
#    return render_to_response(
#	'reblock/retrieve_password.html',
#	{}, context)

    #return HttpResponseRedirect('/login/')
    

@login_required
def user_logout(request):
    # Since we know the user is logged in, we can now just log them out.
    logout(request)

    # Take the user back to the homepage.
    return HttpResponseRedirect('/logout/')  


@login_required
def review(request):
    """
    A view for uploading new data.
    """
    user = request.user
    if request.method == 'POST': # someone is giving us data
        #formset = LayerReviewFormSet(request.POST)
        
        upload = UploadEvent.objects.filter(user=user).order_by('-date')[0]
        data_files = DataFile.objects.filter(upload=upload)
        layer_data = [ f.get_layer_data() for f in data_files ]
	
        
        #########get the information filled by user#########
        if len(str(request.POST.get("name")))>0 :
            name = request.POST.get("name")
        elif len(str(layer_data[0]['name']))>0:
            name = layer_data[0]['name']
        else:
            name = "default"
        if len(str(request.POST.get("location")))>0 :
            location = request.POST.get("location")
        else:
            location = "default"
        if len(str(request.POST.get("description")))>0 :
            desc = request.POST.get("description")
        else:
            desc = "-"
	if len(str(request.POST.get("barrier_index")))>0 :
	    b_index = request.POST.get("barrier_index")  
	else:
            b_index = "-"    
	#print b_index
        
        datainfo = {}
        datainfo["name"] = slugify(name)
        datainfo["location"] = slugify(location)
        datainfo["description"] = desc
        datainfo["srs"] = checkedPrj(layer_data[0]['srs'])
	#print datainfo["srs"]
        
        # For every layer in the layer form, write a PostGIS object to the DB
        ds = DataSource(layer_data[0]['file_location'])
        layer = ds[0]
                

        geoms = checkGeometryType(layer)
	#graph_indices = get_index(b_index)
	
        scale_factor2 = scaleFactor(geoms)
	
	num = BloockNUM.objects.filter(author=user).order_by('-date_edited').reverse()
	
	datainfo["num"] = len(num)
	
        try:
	    run_topology.delay(lst=geoms, name = layer.name, user = user,scale_factor = scale_factor2, data = datainfo, indices=b_index)

	    return HttpResponseRedirect('/reblock/compute/')
	
	except :
	    print 1111
	    return render_to_response(
	    'reblock/review.html',
	    RequestContext(request, c),
	    )
        
    else: # we are asking them to review data
        # get the last upload of this user
        upload = UploadEvent.objects.filter(user=user).order_by('-date')[0]
        data_files = DataFile.objects.filter(upload=upload)
        layer_data = [ f.get_layer_data() for f in data_files ]

        file_path = layer_data[0]['file_location']
        ds = DataSource( file_path )
        layer = ds[0]
        srs = layer_data[0]['srs']
        if not isnumber(srs):
            srs = default_srs
        ct = CoordTransform(SpatialReference(srs), SpatialReference(4326))
        
        reviewdic = []

        for feat in layer:
            geom = feat.geom # getting clone of feature geometry
            geom.transform(ct) # transforming
            reviewdic.append(json.loads(geom.json))

        
        reviewjson = json.dumps(reviewdic)
        
        formset = LayerReviewFormSet( initial=layer_data )
	
        c = {
                'test_layers': reviewjson,
                'formset':formset,
                'centerlat':center_lat,
                'centerlng':center_lng,
                }
        return render_to_response(
                'reblock/review.html',
                RequestContext(request, c),
                )


@login_required
def compute(request):
    
    user = request.user
    
    
    if request.method == 'POST': # someone is editing site configuration
        numlst = BloockNUM.objects.filter(author=user).order_by('-date_edited').reverse()

        try:
            link = int(request.POST.get("stepindex"))
        except:
            link = -1
        try:
            pr_id = int(request.POST.get("projindex"))
        except:
            pr_id = len(numlst)-1
        
        num = numlst[pr_id]
        
        ###########need raise exception if no data saved for current project id ################

        datt = num.datasave2_set.all().order_by('-date_edited')[0]
        
        if link == -1:
            return HttpResponseRedirect('/reblock/compute/'+str(user)+"_"+str(datt.prjname)+"_"+str(datt.location)+"_"+str(pr_id)+"/")
        else:
            return HttpResponseRedirect('/reblock/compute/'+str(user)+"_"+str(datt.prjname)+"_"+str(datt.location)+"_"+str(pr_id)+"/"+str(link))
        
    else:
        
        num = BloockNUM.objects.filter(author=user).order_by('-date_edited')[0]
        # We are browsing data
        number = num.number
        
        ori_layer = num.definebarriers_set.all().order_by('-date_edited') 
        ori_proj = project_meter2degree(layer = ori_layer,num = number)
        
        road_layers = num.roadjson4_set.all().order_by('-date_edited') 
        road_proj = project_meter2degree(layer = road_layers,num = number)
        
        inter_layers = num.interiorjson4_set.all().order_by('-date_edited')    
        inter_proj = project_meter2degree(layer = inter_layers,num = number)
        
        c = {
                'ori_proj': ori_proj,
                'road_proj': road_proj,
                'inter_proj': inter_proj,        
                }
                
        return render_to_response(
                'reblock/compute.html',
                RequestContext(request, c),
                )


@login_required
def reload(request):
    user = request.user
    num = BloockNUM.objects.filter(author=user).order_by('-date_edited')[0]

    # We are browsing data
    number = num.number
        
    ori_layer = num.definebarriers_set.all().order_by('-date_edited') 
    ori_proj = project_meter2degree(layer = ori_layer,num = number)
    road_layers = num.roadjson4_set.all().order_by('-date_edited') 
    road_proj = project_meter2degree(layer = road_layers,num = number)
    inter_layers = num.interiorjson4_set.all().order_by('-date_edited')    
    inter_proj = project_meter2degree(layer = inter_layers,num = number)

    dic = {}
    dic["ori"] = str(ori_proj)
    dic["rd"] = str(road_proj)
    dic["int"] = str(inter_proj)
    json = simplejson.dumps(dic)
    return HttpResponse(json, mimetype='application/json')


@login_required
def final_slut(request, slot_user, project_id, project_name, location):
    user = request.user
    
    ##########should be slotified user
    if slugify(str(user))==slot_user:
        if request.method == 'POST': # someone is editing site configuration
            pass
        else:
            num = BloockNUM.objects.filter(author=user).order_by('-date_edited').reverse()[int(project_id)]
            number = num.number
            ori_layer = num.definebarriers_set.all().order_by('-date_edited') 
            ori_proj = project_meter2degree(layer = ori_layer,num = number)
            
            road_layers = num.roadjson4_set.all().order_by('-date_edited') 
            road_proj = project_meter2degree(layer = road_layers,num = number)
            
            inter_layers = num.interiorjson4_set.all().order_by('-date_edited')    
            inter_proj = project_meter2degree(layer = inter_layers,num = number)

            c = {
                    'ori_proj': ori_proj,
                    'road_proj': road_proj,
                    'inter_proj': inter_proj,
                    }
                    
            return render_to_response(
                'reblock/steps.html',
                RequestContext(request, c),
                )

@login_required
def final_whole(request, slot_user, project_id, project_name, location):
    user = request.user
    
    ##########should be slotified user
    if slugify(str(user))==slot_user:
        if request.method == 'POST': # someone is editing site configuration
            pass
        else:
            num = BloockNUM.objects.order_by('-date_edited').reverse()[int(project_id)]
            number = num.number
            ori_layer = num.definebarriers_set.all().order_by('-date_edited') 
            ori_proj = project_meter2degree(layer = ori_layer,num = number)
            
            road_layers = num.roadjson4_set.all().order_by('-date_edited') 
            road_proj = project_meter2degree(layer = road_layers,num = number)
            
            inter_layers = num.interiorjson4_set.all().order_by('-date_edited')    
            inter_proj = project_meter2degree(layer = inter_layers,num = number)

            c = {
                    'ori_proj': ori_proj,
                    'road_proj': road_proj,
                    'inter_proj': inter_proj,
                    }
                    
            return render_to_response(
                'reblock/steps.html',
                RequestContext(request, c),
                )




@login_required
def steps_slut(request, step_index, slot_user, project_id, project_name, location):
    user = request.user
    
    ##########should be slotified user
    if slugify(str(user))==slot_user:
        if request.method == 'POST': # someone is editing site configuration
            pass
        else:
            num = BloockNUM.objects.filter(author=user).order_by('-date_edited').reverse()[int(project_id)]
            number = num.number

            ori_layer = num.definebarriers_set.all().order_by('-date_edited') 
            ori_proj = project_meter2degree(layer = ori_layer,num = number)

    ##################step data######################
            step_layers = num.intermediatejson6_set.all().order_by('-date_edited').reverse()   
            inter_proj = project_meter2degree(layer = step_layers,num = number,offset = int(step_index))
            road_proj = projectRd_meter2degree(layer = step_layers,num = number,offset = int(step_index))

            c = {
                    'ori_proj': ori_proj,
                    'road_proj': road_proj,
                    'inter_proj': inter_proj,
                    }
                    
            return render_to_response(
                'reblock/steps.html',
                RequestContext(request, c),
                )

"""
redirect to a page showing the recent reblocks created by the same user
"""
#@login_required
def recent(request):
    
    ##########should be slotified user
    if request.method == 'POST': # someone is editing site configuration
        pass
    else:            
        num = BloockNUM.objects.order_by('-date_edited')[:4]
        

        lstjson = []
        lstprjname = []
        lstlocation = []
        lstdes = []
        for i,n in enumerate(num):
            if len(n.datasave2_set.all())>0:
                datt = n.datasave2_set.all().order_by('-date_edited')[0]
                
                number = n.number

                lstprjname.append(str(datt.prjname))
                lstlocation.append(str(datt.location))
                lstdes.append(datt.description)
                ori_layer = n.definebarriers_set.all().order_by('-date_edited') 
                ori_proj = project_meter2degree(layer = ori_layer,num = number)
            
                #~ road_layers = n.roadjson4_set.all().order_by('-date_edited') 
                #~ road_proj = project_meter2degree(layer = road_layers,num = number)
                #~ inter_layers = n.interiorjson4_set.all().order_by('-date_edited')    
                #~ inter_proj = project_meter2degree(layer = inter_layers,num = number)
                
                lstjson.append(json.loads(ori_proj))
            
        lstjson = simplejson.dumps(lstjson)
        lstprjname = simplejson.dumps(lstprjname)
        lstlocation = simplejson.dumps(lstlocation)
        lstdes = simplejson.dumps(lstdes)
        
        c = {
        "lstjson" : lstjson,
        "lstprjname": lstprjname,
        "lstlocation": lstlocation,
        "lstdes": lstdes,       
        }
                    
        return render_to_response(
            'reblock/recent.html',
            RequestContext(request, c),
            )
#
"""
redirect to a page showing the recent reblocks created by the same user
"""
@login_required
def profile(request):
    user = request.user
    ##########should be slotified user
    if request.method == 'POST': # someone is editing site configuration
        pass
    else:            
        num = BloockNUM.objects.filter(author=user).order_by('-date_edited')[:4]
        
        lstlink = []
        lstjson = []
        lstprjname = []
        lstlocation = []
        lstdes = []
        for i,n in enumerate(num):
            if len(n.datasave2_set.all())>0:
                datt = n.datasave2_set.all().order_by('-date_edited')[0]
                
                number = n.number
                link = '/reblock/compute/'+str(user)+"_"+str(datt.prjname)+"_"+str(datt.location)+"_"+str(datt.d_id)+"/"
                lstlink.append(link)

                lstprjname.append(str(datt.prjname))
                lstlocation.append(str(datt.location))
                lstdes.append(datt.description)
                ori_layer = n.definebarriers_set.all().order_by('-date_edited') 
                ori_proj = project_meter2degree(layer = ori_layer,num = number)
            
                #~ road_layers = n.roadjson4_set.all().order_by('-date_edited') 
                #~ road_proj = project_meter2degree(layer = road_layers,num = number)
                #~ inter_layers = n.interiorjson4_set.all().order_by('-date_edited')    
                #~ inter_proj = project_meter2degree(layer = inter_layers,num = number)
                
                lstjson.append(json.loads(ori_proj))
            
        lstjson = simplejson.dumps(lstjson)
        lstlink = simplejson.dumps(lstlink)
        lstprjname = simplejson.dumps(lstprjname)
        lstlocation = simplejson.dumps(lstlocation)
        lstdes = simplejson.dumps(lstdes)
        
        c = {
        "lstlink" : lstlink,
        "lstjson" : lstjson,
        "username": str(user),
        "lstprjname": lstprjname,
        "lstlocation": lstlocation,
        "lstdes": lstdes,       
        }
                    
        return render_to_response(
            'reblock/profile.html',
            RequestContext(request, c),
            )


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

def run_once(original,name=None, user = None, block_index = 0, srs = None, barriers=None):

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


#def get_index(b_index):
#    #graph_indices =[]
#    if "," in b_index:  
#	ba= [int(i) for i in b_index.split(",")]
#	graph_indices = ba
#	return graph_indices


def match_barriers(b_index, original):
    #graph_indices = get_index(b_index)
    b_edges = []
    if "," in b_index:
	ba= [int(i) for i in b_index.split(",")]
	#print ba
	bar_edge = original.myedges()
	print len(bar_edge)
     
	for index in ba:
	    if index <= len(bar_edge):
    
		b_edges.append(bar_edge[index])
		b = set(b_edges)
		a = list(b)
		#print b_edges
	return a


"""
rewrite new_import function from topology

imports the file, plots the original map, and returns
a list of blocks from the original map.
"""
def new_import(lst, name=None,scale = 1, indices=None):
    original = import_and_setup(lst,scale = scale, threshold=1)#create and clean the graph.
    
    if indices:
	
	barriers = match_barriers(indices, original)
	print len(barriers)
	mgh.build_barriers(barriers)
	
	#print indices
	# assign theses to a variable called barriers
	# compute minimal paths with barriers
    else:
	print "NO"
	# compute without 

    blocklist = original.connected_components()

    # plot the full original map
    for b in blocklist:
        # defines original geometery as a side effect,
        pass
        b.plot_roads(master=b, new_plot=False, update=True)

    
    blocklist.sort(key=lambda b: len(b.interior_parcels), reverse=True)

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

    if vquiet is True:
        quiet = True

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
    if vquiet is False:
        pass
        #print("Begin w {} Interior Parcels".format(len(myG.interior_parcels)))

    md = 100

    while original.interior_parcels:############extract###########
        #save remaining interior parcel to the database
        gJson = simplejson.dumps(json.loads(mgh.graphFromMyFaces(original.interior_parcels).myedges_geoJSON()))
        roads = simplejson.dumps({"type": "FeatureCollection","features": [e.geoJSON(np.array([0, 0])) for e in original.myedges() if e.road]})
        
        number = BloockNUM.objects.filter(author=user).order_by('-date_edited')[0]
        
        db_json = IntermediateJSON6(name=name, topo_json = gJson, road_json = roads,author = user,step_index = len(original.interior_parcels),block_index = block_index, srs = srs, number = number)
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
	    all_paths = mgh.find_short_paths_all_parcels(original, flist, target_mypath,
						     barriers, quiet=quiet,
						     shortest_only=shortest_only)
	except nx.NetworkXNoPath:
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
