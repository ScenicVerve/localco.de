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
import StringIO

from celery.result import AsyncResult
from settings import MEDIA_ROOT
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
from django.contrib.auth.models import User

import django.contrib.gis
from django.contrib.gis.geos import *
from django.contrib.gis.db import models
from django.contrib.gis.measure import D
from django.contrib.gis.gdal import *
from django.contrib.gis.gdal import SpatialReference, CoordTransform
from django.contrib.gis.geos import fromstr
from django.utils.encoding import smart_str

from tasks import *
from reblock.forms import *
from reblock.models import *
from reblock.reblock_helpers import *

from reblock.models import UserProfile
from django.utils import text

import topology.my_graph as mg
import topology.my_graph_helpers as mgh
from django.utils import simplejson
from slugify import slugify

import datetime, random
from django.shortcuts import render_to_response, get_object_or_404
from django.core.mail import send_mail

from django.views.generic.list import ListView
from django.utils import timezone

import mimetypes
from django.core.servers.basehttp import FileWrapper

center_lat = None
center_lng = None
default_srs = 24373


def index(request):
    '''
    A view for browsing the existing webfinches.
    '''
    return render_to_response(
            'reblock/index.html',
            {'reblock':DataLayer.objects.all()},
            )


@login_required
def upload(request):
    '''
    A view for uploading new data.
    In: Zip file : a zip file that contains all the necessary file formats
    Out: reblock.model.UploadEvent : Redirects to review page
    '''
    user = request.user
    #if the user provides data
    if request.method == 'POST':
        upload = UploadEvent(user=user)
        upload.save()
        
        formset = ZipFormSet(request.POST, request.FILES)
        for form in formset:
	    #check if the file is in the correct format or if a file has been uploaded
            if form.is_valid() and form.has_changed():
                data_file = form.save(upload)
                return HttpResponseRedirect('/reblock/review/')
	    #if nothing has been uploaded notify user that no zip is uploaded
            elif not form.has_changed():
                return render_to_response(
                'reblock/browse_empty.html',
                {})           
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
    '''
    A view for user registration.
    In: html post : user provides: username, email, password1, password2(confirm)
    Out:reblock.form.UserForm : A form model that is based in django User built-in form model
    '''
    context = RequestContext(request)
    registered = False
    
    #if the user provides data
    if request.method == 'POST':
        user_form = UserForm(request.POST)
	
	#check if the username already exists in the database
	#redirects to an html page that notifies the user that the username is already in use and allows user to register again
        if User.objects.filter(username=request.POST['username']).exists():
            return render_to_response(
            'reblock/username_exists.html',
            {},
            context)
	
        else:
	    #check if username does not already exist get the input user data from the website
	    #check if the user data is valid
            if user_form.is_valid():
		username = request.POST.get("username")
		user_email = request.POST.get("email")
		user_pwd1 = request.POST.get("password1")
		user_pwd2 = request.POST.get("password2")
		
		#check if he passwords match
		if user_pwd1 == user_pwd2:
		    #create user
		    user = User.objects.create_user(username, user_email, user_pwd1)
		    #save user in the database
		    user.save()
		    registered = True
		    #send email to the user to confirm the registration
		    message = 'Congratulations! You are registered! Please click on the link to log in to your profile.'+' '+'http://openreblock.berkeley.edu/login/'
		    email = EmailMultiAlternatives('Openreblock - Registration confirmation',message,'openreblock@gmail.com', [user_email])
		    email.send()
		    return render_to_response(
		    'reblock/registration_complete.html',
		    {},
		    context)
		
		else:
		    #if passwords do not match notify user accordingly
		    registered = False
		    return render_to_response(
		    'reblock/register.html',{'user_form': user_form, 'registered': registered}, context)		
	    else:
		#if user data is not valid notify user and allow to register again
		registered = False
		return render_to_response('reblock/registration_failed.html',{'user_form': user_form, 'registered': registered}, context)		
    else:
        user_form = UserForm()
    
    return render_to_response(
        'reblock/register.html',
        {'user_form': user_form, 'registered': registered},
        context)


def forgot_password(request):
    '''
    A view for forgot password case.
    In: html post : user provides: username in order to set a new password
    Out:reblock.form.NewPassword : A form model that is based in django User built-in form model 
    '''
    context = RequestContext(request)
    registered = False
    
    #if the user provides data
    if request.method == 'POST':
        user_form = UserForm(request.POST)
	new = NewPassword(request.POST)
	
	#check if username does not already exist get the input user data from the website
	if User.objects.filter(username=request.POST["username"]).exists():
	    #based on the username retrieve the email and allow user to set new password
	    config_username = request.POST.get("username")
	    user = User.objects.get(username__exact=config_username)
	    #user new password input
	    new_password1 = request.POST.get("new_password1")
	    #ste new password
	    user.set_password(new_password1)
	    #get user email based on the username
	    user_email = user.email
	    #save user
	    user.save()
	    #email the user with the new password
	    message = 'Your new password has changed to: '+ new_password1+' '+'Use it to log back in openreblock.berkeley.edu'
	    email = EmailMultiAlternatives('password change',message ,'openreblock@gmail.com', [user_email])
	    email.send()
	    return HttpResponseRedirect('/set_new_password/') #this redirects correct
	
	else:
	    return render_to_response(
	    'reblock/forgot_password.html',
	    {'user_form': user_form, 'registered': registered},
	    context)

    return render(request, 'reblock/forgot_password.html', {'new': NewPassword})


def set_new_password(request):
    '''
    A view when new password is set.
    In: html post : user request to set new pasword by providing the username
    Out:redirect page : Redirects to set-new password.html where the user can log in with the new password 
    '''
    #redirects to login
    context = RequestContext(request)
    return render_to_response(
    'reblock/set_new_password.html',
    {},
    context)


@login_required
def review(request):
    '''
    Function that is triggered when a file is uploaded. It will visualize the uploaded shp file by overlay it to the map after projection
    In: htlm post : user can input name, location, description and barrier index for the file before the calculation starts.
    Out: html : Redirets to html compute when the user starts the calculation of the file
    '''
    user = request.user
    if request.method == 'POST': # if compute button is pressed, will lead to the computation in celery, and redirect to compute page     
        
        #get the latest upload event and datafile from database
        upload = UploadEvent.objects.filter(user=user).order_by('-date')[0]
        data_files = DataFile.objects.filter(upload=upload)
        layer_data = [ f.get_layer_data() for f in data_files ]

        #get the input information from the user: name, location, description, barrier index

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
        
        datainfo = {}
        
        # get the geometry(shapefile)
        ds = DataSource(layer_data[0]['file_location'])
        layer = ds[0]
                
        #check geometry type and flatten geometry collection, save as linestring list
        geoms = checkGeometryType(layer)
        start = StartSign2.objects.filter(author=user).order_by('-date_edited').reverse()
        
        #save data that will be passed to tasks
        datainfo["num"] = len(start)
        datainfo["name"] = slugify(name)
        datainfo["location"] = slugify(location)
        datainfo["description"] = desc
        datainfo["srs"] = checkedPrj(layer_data[0]['srs'])
        
        #run tasks for the computation
        mytask = run_topology.delay(geoms, name = layer.name, user = user,scale_factor = 1, data = datainfo,  indices=b_index)

        return HttpResponseRedirect('/reblock/compute/')

    else:
	#ask the user to review data
        # get the last upload of this user
        upload = UploadEvent.objects.filter(user=user).order_by('-date')[0]
        data_files = DataFile.objects.filter(upload=upload)
        layer_data = [ f.get_layer_data() for f in data_files ]
        file_path = layer_data[0]['file_location']
        ds = DataSource( file_path )
        layer = ds[0]
        srs = layer_data[0]['srs']
        
        #check if srs exist, if not, use the default srs to do the projection process
        if not isnumber(srs):
            srs = default_srs
        
        #set up projection method for current srs
        ct = CoordTransform(SpatialReference(srs), SpatialReference(4326))
        
        #holder for input geometry as geojson after projection
        reviewdic = []
        
        for feat in layer:
            # getting clone of feature geometry
            geom = feat.geom 
            
            #projection for the input geometry(just converted from .shp to gdal object)
            geom.transform(ct) # transforming
            
            #save the projected gdal object, save as geojson
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
    '''
    Function that is triggered after pressing "Start Calculation" button in review
    will show to computation process and result
    In: html post : Button "Start Calculation": user input for the calculation to start
    Out: html redirect: Provides a unique url based on project name, location, and project id 
    '''
    user = request.user
    if request.method == 'POST': # the user is checking a specific project or step
        startlst = StartSign2.objects.filter(author=user).order_by('-date_edited').reverse()
        try:
            link = int(request.POST.get("stepindex"))
        except:
            link = -1
        try:
            pr_id = int(request.POST.get("projindex"))
        except:
            pr_id = len(startlst)-1
        
        start = startlst[pr_id]
        datt = start.datasave5_set.all().order_by('-date_edited')[0]
        
        #redirect link
        if link == -1:#redirect to a specific project
            return HttpResponseRedirect('/reblock/compute/'+str(user)+"_"+str(datt.prjname)+"_"+str(datt.location)+"_"+str(pr_id)+"/")
        else:#redirect to a specific step of a given project
            return HttpResponseRedirect('/reblock/compute/'+str(user)+"_"+str(datt.prjname)+"_"+str(datt.location)+"_"+str(pr_id)+"/"+str(link))
        
    else: #redirect to a temp url for the current project, that will show the computation process/result
        startlst = StartSign2.objects.filter(author=user).order_by('-date_edited').reverse()
        
        #use the length of startlist as current id
        pr_id = len(startlst)
        return HttpResponseRedirect('/reblock/compute/'+str(user)+"_"+str("newproject")+"_"+str("newlocation")+"_"+str(pr_id)+"/")


@login_required
def reload(request):
    '''
    Function to reload map in steps.html. Returns geojson of the related project.
    In: proj_id : after user request the file is retrieved from the database based on the project id
    Out: Geojson : The final geojson from the database.
    '''
    user = request.user
    GET = request.GET
    
    #get the requested project id
    pr_id = GET['pr_id']
    print "project:................"+str(pr_id)
    
    #locate the project according to project id
    start = StartSign2.objects.filter(author=user).order_by('-date_edited').reverse()[int(pr_id)]
    num = start.bloocknum2_set.all().order_by('-date_edited')[0]
    
    #block number for this project
    number = num.number
    print "final reloading........."
    
    #get original geometry for this project
    ori_layer = start.definebarriers2_set.all().order_by('-date_edited') 
    ori_proj = project_meter2degree(layer = ori_layer,num = number)
    
    #get road geometry for this project
    road_layers = start.roadjson6_set.all().order_by('-date_edited') 
    road_proj = project_meter2degree(layer = road_layers,num = number)
    
    #get interior_parcel geometry for this project
    inter_layers = start.interiorjson6_set.all().order_by('-date_edited')    
    inter_proj = project_meter2degree(layer = inter_layers,num = number)
    
    #save shapefiless
    saveshp(start = start, user = user,prid =pr_id,  layer = ori_layer,num = number, name = "original")
    saveshp(start = start, user = user,prid =pr_id,  layer = road_layers,num = number, name = "road")
    saveshp(start = start, user = user,prid =pr_id,  layer = inter_layers,num = number, name = "interior")
    zippath = zipSave(name = "shp_file.zip", start = start, user = user, prid = pr_id)

    #save the geometries to a dictionary
    dic = {}
    dic["ori"] = str(ori_proj)
    dic["rd"] = str(road_proj)
    dic["int"] = str(inter_proj)
    
    #save the current step amount(step_index) to the dictionary
    step_layers = start.intermediatejson7_set.all().order_by('-date_edited').reverse()   
    step_index = len(step_layers)/number-1
    if step_index>=0:
        dic["stepnumber"] = int(step_index+1)
    else:
        dic["stepnumber"] = 0
    dic["zip"] = zippath
    
    #return the geojson to html page
    json = simplejson.dumps(dic)
    return HttpResponse(json, mimetype='application/json')


@login_required
def download(request):
    '''
    Fuction that allows user to download the shapefile
    In: html post : user request to download the shapefile
    Out: html : directs to an html page with a button for downloading the shapefile
    ''' 
    user = request.user
    GET = request.GET
    
    mypath = GET['path']
    the_file = str(mypath)
    filename = os.path.basename(the_file)
    f = open(mypath, 'r')

    response = HttpResponse(f, content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename=' + filename
    return response


@login_required
def check_step(request):
    '''
    Fuction that 
    In: proj_id :  project id
    Out: geojson : intermediate geojsons that are passed to html
    ''' 
    user = request.user
    GET = request.GET
    
    #get the requested project id
    pr_id = GET['pr_id']
    
    #get the requested project step
    step = GET['step']
    print "project:................"+str(pr_id)
    dic = {}
    
    #locate the project according to project id
    start = StartSign2.objects.filter(author=user).order_by('-date_edited').reverse()[int(pr_id)]
    num = start.bloocknum2_set.all().order_by('-date_edited')[0]
    
    #block number for this project
    number = num.number
    
    #get all steps(model) list for this project
    step_layers = start.intermediatejson7_set.all().order_by('-date_edited').reverse()   
    step_index = len(step_layers)/number-1
    
    #get original geometry
    ori_layer = start.definebarriers2_set.all().order_by('-date_edited') 
    ori_proj = project_meter2degree(layer = ori_layer,num = number)

    dic["ori"] = str(ori_proj)
    
    #if all step is 
    if int(step)<int(step_index+1):

        step_layers = start.intermediatejson7_set.all().order_by('-date_edited').reverse()   

        print "final reloading........."
        road_layers = start.roadjson6_set.all().order_by('-date_edited') 
        road_proj = project_meter2degree(layer = road_layers,num = number)
        
        inter_proj = project_meter2degree(layer = step_layers,num = number,offset = int(step))
        road_proj = project_meter2degree(layer = step_layers,num = number,offset = int(step), topo=False)
        
        dic["rd"] = str(road_proj)
        dic["int"] = str(inter_proj)
    else:
        road_layers = start.roadjson6_set.all().order_by('-date_edited') 
        road_proj = project_meter2degree(layer = road_layers,num = number)

        inter_layers = start.interiorjson6_set.all().order_by('-date_edited')    
        inter_proj = project_meter2degree(layer = inter_layers,num = number)
        dic["rd"] = str(road_proj)
        dic["int"] = str(inter_proj)  

    if step_index>=0:
        dic["stepnumber"] = int(step_index+1)
    else:
        dic["stepnumber"] = 0

    json = simplejson.dumps(dic)
    return HttpResponse(json, mimetype='application/json')


@login_required
def reload_step(request):
    '''
    Fuction that outputs the last step of the calculation
    In: proj_id : project id
    Out: steps geojsons : pass the current calculation state
    ''' 
    user = request.user
    GET = request.GET
    pr_id = GET['pr_id']
    print "project.........:................"+str(pr_id)
    dic = {}
    
    #staarting state
    start = StartSign2.objects.filter(author=user).order_by('-date_edited').reverse()[int(pr_id)]
    print "fix"
    print "reload step............start = "+str(start)
    
    if start:
        dic["start"] = 1
    else:
        dic["start"] = 0
    
    step = len(start.stepstart2_set.all())
    
    print "reload step............step = "+str(step)
    
    if step:
        dic["step"] = 1
    else:
        dic["step"] = 0
    
    try:
        num = start.bloocknum2_set.all().order_by('-date_edited')[0]
        number = num.number

        ori_layer = start.definebarriers2_set.all().order_by('-date_edited') 
        ori_proj = project_meter2degree(layer = ori_layer,num = number)
	
        #step data
        step_layers = start.intermediatejson7_set.all().order_by('-date_edited').reverse()   
        step_index = len(step_layers)/number-1
        print step_index
        if step_index>=0:
	    
            #reproject the json in decimal degrees in order to display on the background map
            inter_proj = project_meter2degree(layer = step_layers,num = number,offset = int(step_index))
            road_proj = project_meter2degree(layer = step_layers,num = number,offset = int(step_index), topo=False)
            
            dic["ori"] = str(ori_proj)
            dic["rd"] = str(road_proj)
            dic["int"] = str(inter_proj)
	    
            #final state
            finish = len(start.finishsign3_set.all())
            if finish:
                dic["finish"] = 1
            else:
                dic["finish"] = 0
        else:
            finish = len(start.finishsign3_set.all())
            if finish:
                dic["finish"] = 1
            else:
                dic["finish"] = 0
    
        print "reload step............finish = "+str(finish)
    except:
        pass
  
    if step_index>=0:
        dic["stepnumber"] = int(step_index+1)
    else:
        dic["stepnumber"] = 0
    
    #all the geojsons
    json = simplejson.dumps(dic)

    return HttpResponse(json, mimetype='application/json')


@login_required
def final_slut(request, slot_user, project_id, project_name, location):
    '''
    Function that gets the info from url from "compute" and passes the project id to the steps page
    In: user, project_name, location, proj_id : information retrieved from the url
    Out: redirect to steps.html page 
    '''  
    user = request.user
    #should be slotified user
    if slugify(str(user))==slot_user:
	
	#if user is editing site configuration
        if request.method == 'POST': 
            pass
        else:            

            c = {
                    'project_id': int(project_id),
                    }
                    
            return render_to_response(
                'reblock/steps.html',
                RequestContext(request, c),
                )


def recent(request):
    '''
    Function that redirects to a page that shows the recent reblocks from the database
    In: html home page
    Out: geojson : The most recent projects as geojsons. Current number is set to 3 in the recent.html page (toload = 3)
    '''
    #retrieve input from request
    if request.method == 'POST':
        pass
    else:            
        startlst = StartSign2.objects.order_by('-date_edited')
        if len(startlst)<3:
            start = startlst
        else:
            start = startlst[:3]
        
        lstjson = []
        lstprjname = []
        lstlocation = []
        lstdes = []
	
	#get geojson from database
        for i,n in enumerate(start):
            if len(n.bloocknum2_set.all())>0:
                datt = n.datasave5_set.all().order_by('-date_edited')[0]
                num = n.bloocknum2_set.all().order_by('-date_edited')[0]
                number = num.number

                lstprjname.append(str(datt.prjname))
                lstlocation.append(str(datt.location))
                lstdes.append(datt.description)
                
                ori_layer = n.definebarriers2_set.all().order_by('-date_edited') 
                ori_proj = project_meter2degree(layer = ori_layer,num = number)
                
                lstjson.append(json.loads(ori_proj))
		
        #pass as a json to the recent.html
        lstjson = simplejson.dumps(lstjson)
        lstprjname = simplejson.dumps(lstprjname)
        lstlocation = simplejson.dumps(lstlocation)
        lstdes = simplejson.dumps(lstdes)
        
        c = {
        "lstjson" : lstjson,
        "lstprjname": lstprjname,
        "lstlocation": lstlocation,
        "lstdes": lstdes,    
        "allnum" :   len(startlst),
        }
                    
        return render_to_response(
            'reblock/recent.html',
            RequestContext(request, c),
            )


def recent_index(request):
    '''
    Function that indicates which project to retrieve from database to load more, (default: 3 at a time)
    In: loadnum, loadstart : loadnum is passed from recent.html
    Out: geojson : a geojson for the specific project passed to recent.html
    '''
    GET = request.GET
    loadnum = int(GET['loadnum']);
    loadstart = int(GET['index'])
    loadend = loadstart+loadnum
    print "load start :"+str(loadstart)
    print "load end :"+str(loadend)

    if request.method == 'POST':
        pass
    else:            
        startlst = StartSign2.objects.order_by('-date_edited')
        start = startlst[loadstart:loadend]
        
        lstjson = []
        lstprjname = []
        lstlocation = []
        lstdes = []
        
	#get geojson from database
        for i,n in enumerate(start):
            if len(n.bloocknum2_set.all())>0:
                datt = n.datasave5_set.all().order_by('-date_edited')[0]
                num = n.bloocknum2_set.all().order_by('-date_edited')[0]
                number = num.number

                lstprjname.append(str(datt.prjname))
                lstlocation.append(str(datt.location))
                lstdes.append(datt.description)
                
                ori_layer = n.definebarriers2_set.all().order_by('-date_edited') 
                ori_proj = project_meter2degree(layer = ori_layer,num = number)

                lstjson.append(simplejson.loads(ori_proj))
         
	#pass as a json to the recent.html    
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
        
        json = simplejson.dumps(c)
        print "json loaded"
        return HttpResponse(json, mimetype='application/json')


@login_required
def profile(request):
    '''
    Function that redirects to a page that shows the recent reblocks from the database
    In: html post : user request to view the profile page
    Out: geojson : The most recent projects as geojsons uploaded by the user. Current number is set to 3 in the profile.html page (toload = 3)
    '''
    #retrieve input from request
    user = request.user
    if request.method == 'POST': 
        pass
    else:
        
        startlst = StartSign2.objects.filter(author=user).order_by('-date_edited')
	#if the projects' number is less than 3, return all the list
        if len(startlst)<3:
            start = startlst
	#else return only the first 3    
        else:
            start = startlst[:3]

        lstlink = []
        lstjson = []
        lstprjname = []
        lstlocation = []
        lstdes = []
	
	#get geojson from database
        for i,n in enumerate(start):
            if len(n.bloocknum2_set.all())>0:
                datt = n.datasave5_set.all().order_by('-date_edited')[0]
                num = n.bloocknum2_set.all().order_by('-date_edited')[0]
                number = num.number
                link = '/reblock/compute/'+str(user)+"_"+str(datt.prjname)+"_"+str(datt.location)+"_"+str(datt.d_id)+"/"
                lstlink.append(link)

                lstprjname.append(str(datt.prjname))
                lstlocation.append(str(datt.location))
                lstdes.append(datt.description)

                ori_layer = n.definebarriers2_set.all().order_by('-date_edited') 
                ori_proj = project_meter2degree(layer = ori_layer,num = number)
                
                lstjson.append(simplejson.loads(ori_proj))
		
        #pass as a json to the profile.html    
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
        "allnum" :   len(startlst),      
        }
                    
        return render_to_response(
            'reblock/profile.html',
            RequestContext(request, c),
            )


@login_required
def profile_index(request):
    '''
    Function that indicates which project to retrieve from database to load more in the user profile, (default: 3 at a time)
    In: user, loadnum, loadstart : user information for current project (name, location etc.), loadnum is passed from profile.html
    Out: geojson for the specific project passed to profile.html
    '''
    GET = request.GET
    user = request.user
    loadnum = int(GET['loadnum']);
    loadstart = int(GET['index']) 
    loadend = loadstart+loadnum
    print "load start :"+str(loadstart)
    print "load end :"+str(loadend)

    if request.method == 'POST': 
        pass
    else:            
        startlst = StartSign2.objects.order_by('-date_edited')
	#split list based on the 2 required indices (loadstart, loadend)
        start = startlst[loadstart:loadend]
        
        lstjson = []
        lstprjname = []
        lstlocation = []
        lstdes = []
        lstlink = []
        
	#get geojson from database
        for i,n in enumerate(start):
            if len(n.bloocknum2_set.all())>0:
                datt = n.datasave5_set.all().order_by('-date_edited')[0]
                num = n.bloocknum2_set.all().order_by('-date_edited')[0]
                number = num.number
                link = '/reblock/compute/'+str(user)+"_"+str(datt.prjname)+"_"+str(datt.location)+"_"+str(datt.d_id)+"/"
                lstlink.append(link)

                lstprjname.append(str(datt.prjname))
                lstlocation.append(str(datt.location))
                lstdes.append(datt.description)
                
                ori_layer = n.definebarriers2_set.all().order_by('-date_edited') 
                ori_proj = project_meter2degree(layer = ori_layer,num = number)

                lstjson.append(simplejson.loads(ori_proj))
		
	#pass as a json to the profile.html    
        lstjson = simplejson.dumps(lstjson)
        lstprjname = simplejson.dumps(lstprjname)
        lstlocation = simplejson.dumps(lstlocation)
        lstdes = simplejson.dumps(lstdes)
        lstlink = simplejson.dumps(lstlink)
        
        c = {
        "lstlink" : lstlink,
        "lstjson" : lstjson,
        "lstprjname": lstprjname,
        "lstlocation": lstlocation,
        "lstdes": lstdes,     
        }
               
        json = simplejson.dumps(c)
        print "json loaded"
        return HttpResponse(json, mimetype='application/json')


