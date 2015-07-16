from celery import Celery
from reblock.models import *
from django.core.mail import send_mail
from django.core.mail import EmailMultiAlternatives
from reblock.views import *
import topology.my_graph as mg
import topology.my_graph_helpers as mgh

from reblock.forms import *

app = Celery('tasks', broker='amqp://guest@localhost//')


"""
rewrite topology, using linestring list as input, save data to the database
"""
@app.task
def run_topology(lst, name=None, user = None, scale_factor=1, data=None, indices=None):
    upload = UploadEvent.objects.filter(user=user).order_by('-date')[0]
    start = StartSign2(name=name, upload = upload, author = user)
    start.save()

    
    proj_id = data["num"]
    srs = data["srs"]
    d_id =data["num"]
    data_save = DataSave5(prjname=data["name"], location = data["location"], author = user,description = data["description"],  d_id = d_id, start = start)
    data_save.save()

    
    prev_message = 'Your calculation is now in progress! We will notify you again once it is completed!'
    email = EmailMultiAlternatives('Open Reblock notification. Calculation started!',prev_message,'openreblock@gmail.com', [user.email])
    email.send()
    
    blocklist = new_import(lst,name,scale = scale_factor, indices=indices)#make the graph based on input geometry
    num = BloockNUM2(name=name, number = len(blocklist), start = start,author = user)
    num.save()
    step = StepStart2(name=name, start = start, author = user)
    step.save()
    
    for i,g in enumerate(blocklist):
        
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
    #message = 'Your reblock is ready! Check it out here:'+' '+'http://127.0.0.1:8000/reblock/compute/'+str(user)+'_' +str(data["name"])+'_' +str(data["location"])+'_'+str(proj_id)+'/'+' '+'You can always find your past reblocks on your profile page'+' '+'http://127.0.0.1:8000/reblock/profile'+' '+'Thanks!'
    message = 'Your reblock is ready! Check it out here:'+' '+'http://openreblock.berkeley.edu/reblock/compute/'+str(user)+'_' +str(data["name"])+'_' +str(data["location"])+'_'+str(proj_id)+'/'+' '+'You can always find your past reblocks on your profile page'+' '+'http://openreblock.berkeley.edu/reblock/profile'+' '+'Thanks!'
    email = EmailMultiAlternatives('Open Reblock notification. Calculation done!',message,'openreblock@gmail.com', [user.email])
    email.send()
