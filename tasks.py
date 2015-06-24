from celery import Celery
from reblock.models import *
from django.core.mail import send_mail
from django.core.mail import EmailMultiAlternatives
from reblock.views import *
#, run_once
import topology.my_graph as mg
import topology.my_graph_helpers as mgh

app = Celery('tasks', broker='amqp://guest@localhost//')

"""
rewrite topology, using linestring list as input
"""
'''
@app.task
def run_topology(lst, name=None):

    blocklist = new_import(lst,name)
    
    g = blocklist[0]

    ep_geojson = g.myedges_geoJSON()
    myjs = json.loads(ep_geojson)
    print myjs
    #map_roads = run_once(blocklist)
    return myjs
'''

@app.task
def run_topology(lst, name=None, user = None, scale_factor=1, srs=None):

    blocklist = new_import(lst,name,scale = 1)#make the graph based on input geometry
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
        
        test_layers = IntermediateJSON3.objects.filter(author=user).order_by('-date_edited')

        print test_layers.all()

    email = EmailMultiAlternatives('test','test','eleannapan@gmail.com', ['eleannapan@gmail.com'])
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