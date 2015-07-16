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

center_lat = None
center_lng = None
default_srs = 24373


def index(request):
    """A view for browsing the existing webfinches.
	In:
	Out: 
    """
    return render_to_response(
            'reblock/index.html',
            {'reblock':DataLayer.objects.all()},
            )

@login_required
def upload(request):
    """
    A view for uploading new data.
    In: Zip file : a zip file that contains all the necessary file formats
    Out: reblock.model.UploadEvent: Description
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
    """
    A view for user registration.
    In: - : -
    Out:reblock.form.UserForm : A form model that is based in django User built-in form model
    """
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
		return render_to_response(
		'reblock/registration_failed.html',{'user_form': user_form, 'registered': registered}, context)
		
    else:
        user_form = UserForm()
    
    return render_to_response(
        'reblock/register.html',
        {'user_form': user_form, 'registered': registered},
        context)


def forgot_password(request):
    """
    A view for forgot password case.
    In: - : -
    Out:reblock.form.NewPassword : A form model that is based in django User built-in form model 
    """
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
    """
    A view when new password is set.
    In: - : -
    Out:redirect page : Redirects to set-new password.html where the user can log in with the new password 
    """
    #redirects to login
    context = RequestContext(request)
    return render_to_response(
    'reblock/set_new_password.html',
    {},
    context)


@login_required
def review(request):
    """
    review function, triggered when file is uploaded
    will visualize the uploaded shp file by overlay it to the map after projection
    """
    user = request.user
    if request.method == 'POST': # if compute button is pressed, will lead to the computation in celery, and redirect to compute page     
        
        #get the latest uploadevent and datafile from database
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
        print mytask, 'checking whatsup', type(mytask)
        return HttpResponseRedirect('/reblock/compute/')

    else:
	# we are asking them to review data
        # get the last upload of this user
        upload = UploadEvent.objects.filter(user=user).order_by('-date')[0]
        data_files = DataFile.objects.filter(upload=upload)
        layer_data = [ f.get_layer_data() for f in data_files ]
        
        print upload
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


"""
compute function, trigger after pressing compute button in preview

will show to computation process and result
"""

@login_required
def compute(request):
    
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


"""
reload function, called to reload map in steps.html
will return geojson of related project
"""
@login_required
def reload(request):
    ##########need to save shapefile here##############
    
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


    saveshp(start = start, user = user,prid =pr_id,  layer = ori_layer,num = number, name = "original");
    saveshp(start = start, user = user,prid =pr_id,  layer = road_layers,num = number, name = "road");
    saveshp(start = start, user = user,prid =pr_id,  layer = inter_layers,num = number, name = "interior");

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
    
    #return the geojson to html page
    json = simplejson.dumps(dic)
    return HttpResponse(json, mimetype='application/json')



@login_required
def check_step(request):
    ##########need to save shapefile here##############
    
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
        road_proj = projectRd_meter2degree(layer = step_layers,num = number,offset = int(step))
        
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


"""
reload the last step of the project
"""
@login_required
def reload_step(request):
    user = request.user
    GET = request.GET
    pr_id = GET['pr_id']
    print "project.........:................"+str(pr_id)
    dic = {}
    
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
	
        ##################step data######################
        step_layers = start.intermediatejson7_set.all().order_by('-date_edited').reverse()   
        step_index = len(step_layers)/number-1
        print step_index
        if step_index>=0:
            
            inter_proj = project_meter2degree(layer = step_layers,num = number,offset = int(step_index))
	    
            road_proj = projectRd_meter2degree(layer = step_layers,num = number,offset = int(step_index))
            
            dic["ori"] = str(ori_proj)
            dic["rd"] = str(road_proj)
            dic["int"] = str(inter_proj)
            
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

            c = {
                    'project_id': int(project_id),
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
            start = StartSign2.objects.order_by('-date_edited').reverse()[int(project_id)]
            num = start.bloocknum2_set.all().order_by('-date_edited')[0]
            number = num.number
            ori_layer = start.definebarriers2_set.all().order_by('-date_edited') 
            ori_proj = project_meter2degree(layer = ori_layer,num = number)
	    
            
            road_layers = start.roadjson6_set.all().order_by('-date_edited') 
            road_proj = project_meter2degree(layer = road_layers,num = number)
	    
            inter_layers = start.interiorjson6_set.all().order_by('-date_edited')    
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
            start = StartSign2.objects.filter(author=user).order_by('-date_edited').reverse()[int(project_id)]
            num = start.bloocknum2_set.all().order_by('-date_edited')[0]
            number = num.number
            ori_layer = start.definebarriers2_set.all().order_by('-date_edited') 
            ori_proj = project_meter2degree(layer = ori_layer,num = number)
	    

    ##################step data######################
            step_layers = start.intermediatejson7_set.all().order_by('-date_edited').reverse()   
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
def recent(request):
    
    ##########should be slotified user
    if request.method == 'POST': # someone is editing site configuration
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
        "allnum" :   len(startlst),
        }
                    
        return render_to_response(
            'reblock/recent.html',
            RequestContext(request, c),
            )

"""
redirect to a page showing the recent reblocks created by the same user
"""
def recent_index(request):

    GET = request.GET

    loadnum = int(GET['loadnum']);
    loadstart = int(GET['index'])
    
    
    loadend = loadstart+loadnum
    print "load start :"+str(loadstart)
    print "load end :"+str(loadend)
    ##########should be slotified user
    if request.method == 'POST': # someone is editing site configuration
        pass
    else:            
        startlst = StartSign2.objects.order_by('-date_edited')
        start = startlst[loadstart:loadend]
        
        lstjson = []
        lstprjname = []
        lstlocation = []
        lstdes = []
        
        
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

                #~ road_layers = n.roadjson4_set.all().order_by('-date_edited') 
                #~ road_proj = project_meter2degree(layer = road_layers,num = number)
                #~ inter_layers = n.interiorjson4_set.all().order_by('-date_edited')    
                #~ inter_proj = project_meter2degree(layer = inter_layers,num = number)
                lstjson.append(simplejson.loads(ori_proj))
            
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
        
        startlst = StartSign2.objects.filter(author=user).order_by('-date_edited')
        if len(startlst)<3:
            start = startlst
        else:
            start = startlst[:3]


        lstlink = []
        lstjson = []
        lstprjname = []
        lstlocation = []
        lstdes = []
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

"""
redirect to a page showing the recent reblocks created by the same user
"""
@login_required
def profile_index(request):

    GET = request.GET
    user = request.user
    loadnum = int(GET['loadnum']);
    loadstart = int(GET['index']) 
    loadend = loadstart+loadnum
    print "load start :"+str(loadstart)
    print "load end :"+str(loadend)
    ##########should be slotified user
    if request.method == 'POST': # someone is editing site configuration
        pass
    else:            
        startlst = StartSign2.objects.order_by('-date_edited')
        start = startlst[loadstart:loadend]
        
        lstjson = []
        lstprjname = []
        lstlocation = []
        lstdes = []
        lstlink = []
        
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

                #~ road_layers = n.roadjson4_set.all().order_by('-date_edited') 
                #~ road_proj = project_meter2degree(layer = road_layers,num = number)
                #~ inter_layers = n.interiorjson4_set.all().order_by('-date_edited')    
                #~ inter_proj = project_meter2degree(layer = inter_layers,num = number)
                lstjson.append(simplejson.loads(ori_proj))

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


