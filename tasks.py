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

def run_topology(lst, name=None, user = None, scale_factor=1, data=None):

    blocklist = new_import(lst,name,scale = scale_factor)#make the graph based on input geometry
    num = BloockNUM(name=name, number = len(blocklist), author = user)
    num.save()
    proj_id = data["num"]
    srs = data["srs"]
    d_id =data["num"] 
    data_save = DataSave2(prjname=data["name"], location = data["location"], author = user,description = data["description"], number = num, d_id = d_id)
    data_save.save()
    
    for i,g in enumerate(blocklist):
        #ALL THE PARCELS
        parcels = simplejson.dumps(json.loads(g.myedges_geoJSON()))
        db_json = BlockJSON4(name=name, topo_json = parcels, author = user,block_index = i, srs = srs, number = num)
        db_json.save()

        #THE INTERIOR PARCELS
        inGragh = mgh.graphFromMyFaces(g.interior_parcels)
        in_parcels = simplejson.dumps(json.loads(inGragh.myedges_geoJSON()))
        db_json = InteriorJSON4(name=name, topo_json = in_parcels, author = user,block_index = i, srs = srs, number = num)
        db_json.save()
        
        #THE ROADS GENERATED and save generating process into the database
        road = simplejson.dumps(json.loads(run_once(g,name = name,user = user,block_index = i, srs = srs)))#calculate the roads to connect interior parcels, can extract steps
        db_json = RoadJSON4(name=name, topo_json = road, author = user,block_index = i, srs = srs, number = num)
        db_json.save()


    
    print "Calculation Done!!!"
    message = 'Your reblock is ready! Check it out here:'+' '+'http://openreblock.berkeley.edu/reblock/compute/'+str(user)+'/' +str(data["name"])+'/' +str(data["location"])+'/'+str(proj_id)+'/'+' '+'You can always find your past reblocks on your profile page. Thanks!'
    email = EmailMultiAlternatives('Open Reblock notification. Calculation done!',message,'eleannapan@gmail.com', [user.email])
    email.send()



'''
def send_mail('test','test',to = ['eleannapan@gmail.com']):
    import smtplib

            gmail_user = "user@gmail.com"
            gmail_pwd = "secret"
            FROM = 'user@gmail.com'
            TO = ['recepient@mailprovider.com'] #must be a list
            SUBJECT = "Testing sending using gmail"
            TEXT = "Testing sending mail using gmail servers"

            # Prepare actual message
            message = """\From: %s\nTo: %s\nSubject: %s\n\n%s
            """ % (FROM, ", ".join(TO), SUBJECT, TEXT)
            try:
                #server = smtplib.SMTP(SERVER) 
                server = smtplib.SMTP("smtp.gmail.com", 587) #or port 465 doesn't seem to work!
                server.ehlo()
                server.starttls()
                server.login(gmail_user, gmail_pwd)
                server.sendmail(FROM, TO, message)
                #server.quit()
                server.close()
                print 'successfully sent the mail'
            except:
                print "failed to send mail"

'''
