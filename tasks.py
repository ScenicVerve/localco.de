from celery import Celery
from reblock.models import *
from django.core.mail import send_mail
from django.core.mail import EmailMultiAlternatives
from reblock.views import *
from reblock.reblock_helpers import *

import topology.my_graph as mg
import topology.my_graph_helpers as mgh
from reblock.forms import *

app = Celery('tasks', broker='amqp://guest@localhost//')

@app.task
def run_topology(lst, name=None, user = None, scale_factor=1, data=None, indices=None):
    '''
    Rewrite topology, using linestring list as input, save data to the database
    Celery task: run_topology, calculates and save jsons in the database and notifies user when the calculation is done
    In: lst : list of linestrings
    Out: jsons : all parcels, roads, interior parcels
    '''
    upload = UploadEvent.objects.filter(user=user).order_by('-date')[0]
    start = StartSign2(name=name, upload = upload, author = user)
    start.save()

    proj_id = data["num"]
    srs = data["srs"]
    d_id =data["num"]
    data_save = DataSave5(prjname=data["name"], location = data["location"], author = user,description = data["description"],  d_id = d_id, start = start)
    data_save.save()

    #send an email to the user notifyin that the calculation has started and that he/she will be notified again once it is done.
    prev_message = 'Your calculation is now in progress! We will notify you again once it is completed!'
    email = EmailMultiAlternatives('Open Reblock notification. Calculation started!',prev_message,'openreblock@gmail.com', [user.email])
    email.send()

    blocklist = new_import(lst,name,scale = scale_factor, indices=indices)#make the graph based on input geometry
    num = BloockNUM2(name=name, number = len(blocklist), start = start,author = user)
    num.save()
    step = StepStart2(name=name, start = start, author = user)
    step.save()

    for i,g in enumerate(blocklist):

        #check if there are any indices
        barriers = None
        if indices != None:
            barriers = True

        #ALL THE PARCELS
        parcels = simplejson.dumps(json.loads(g.myedges_geoJSON()))
        db_json = DefineBarriers2(name=name, topo_json = parcels, author = user,block_index = i, srs = srs, number = num, barrier_index=indices, start = start)
        db_json.save()

        #THE INTERIOR PARCELS
        inGragh = mgh.graphFromMyFaces(g.interior_parcels)
        in_parcels = simplejson.dumps(json.loads(inGragh.myedges_geoJSON()))
        db_json = InteriorJSON6(name=name, topo_json = in_parcels, author = user,block_index = i, srs = srs, number = num, start = start)
        db_json.save()

        #THE ROADS GENERATED and save generating process into the database
        road = simplejson.dumps(json.loads(run_once(g,name = name,user = user,block_index = i, srs = srs, barriers=barriers)))#calculate the roads to connect interior parcels, can extract steps
        db_json = RoadJSON6(name=name, topo_json = road, author = user,block_index = i, srs = srs, number = num, start = start)
        db_json.save()


    finish = FinishSign3(name=name, start = start, author = user)
    finish.save()

    print "Calculation Done!!!"
    #send email to the user when the calculation is completed. Provide link to the redirected to the calculation and to the user's profile.
    #message = 'Your reblock is ready! Check it out here:'+' '+'http://127.0.0.1:8000/reblock/compute/'+str(user)+'_' +str(data["name"])+'_' +str(data["location"])+'_'+str(proj_id)+'/'+' '+'You can always find your past reblocks on your profile page'+' '+'http://127.0.0.1:8000/reblock/profile'+' '+'Thanks!'
    message = 'Your reblock is ready! Check it out here:'+' '+'http://beta.openreblock.org/reblock/compute/'+str(user)+'_' +str(data["name"])+'_' +str(data["location"])+'_'+str(proj_id)+'/'+' '+'You can always find your past reblocks on your profile page'+' '+'http://beta.openreblock.org/reblock/profile'+' '+'Thanks!'
    email = EmailMultiAlternatives('Open Reblock notification. Calculation done!',message,'openreblocker@gmail.com', [user.email])
    email.send()
