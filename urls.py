from localcode.views import *
from django.conf.urls.defaults import patterns, include, url
import reblock #, islands
from django.contrib import admin
from django.contrib.auth.views import login, logout
admin.autodiscover()


interurls = [url(r'^$', 'reblock.views.intermediate'),
             url(r'^(?P<index>[0-9]+)/$', 'reblock.views.steps'),
]

#user sluted url


interurls3 = [url(r'^$', 'reblock.views.final_slut'),
             url(r'^(?P<step_index>[0-9]+)/$', 'reblock.views.steps_slut'),
]
interurls2 = [url(r'^$', 'reblock.views.compute'),
             url(r'^(?P<slot_user>[-\w\d]+)_(?P<project_name>[-\w\d]+)_(?P<location>[-\w\d]+)_(?P<project_id>[0-9]+)/', include(interurls3)),
]



urlpatterns = patterns('',

    # home
    (r'^$', 'localcode.views.home'),
    #(home'^about/$', 'localcode.views.about'),
    #(r'^tools/$', 'localcode.views.tools'),

    # webfinches
    (r'^reblock/$', 'reblock.views.index'),
    #(r'^webfinches/login/create_account/$', 'webfinches.views.create_account'),
    (r'^reblock/upload/$', 'reblock.views.upload'),
    (r'^reblock/review/$', 'reblock.views.review'),
    (r'^reblock/browse/$', 'reblock.views.browse'),
    (r'^reblock/browse_empty/$', 'reblock.views.browse_empty'), #browse warning
    (r'^reblock/configure/$', 'reblock.views.configure'),
    (r'^reblock/get_sites/$', 'reblock.views.get_sites'),
    
    (r'^reblock/compute/', include(interurls2)),
    
    #intermediate
    #url(r'^reblock/intermediate/', include(interurls)),
    
    #url(r'^(?P<slug>[-\w\d]+),(?P<id>\d+)/$', view=myviews.article, name='article'),

    #register
    (r'^reblock/register/$', 'reblock.views.register'),
    (r'^registration/registration_complete/$', 'reblock.views.registration_complete'),
    #(r'^webfinches/user/$', 'webfinches.views.user'),

    
    # Login / logout.
    (r'^login/$', login, {'template_name': 'registration/login.html'}),
    (r'^logout/$', 'django.contrib.auth.views.logout' ),

    # Web portal.
    #(r'^portal/', include('portal.urls')),

    # Serve static content.
    (r'^static/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': 'static'}),

    # webfinches api
    #(r'^webfinches/api/upload/$' 'webfinches.views.ajaxUpload'),
    #(r'^webfinches/api/info/$' 'webfinches.views.layerInfo'),

    # admin
    (r'^admin/', include(admin.site.urls)),
    # admin documentation
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    


)
