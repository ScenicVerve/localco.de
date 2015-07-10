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

interurls4 = [url(r'^$', 'reblock.views.recent'),
             url(r'^(?P<slot_user>[-\w\d]+)_(?P<project_name>[-\w\d]+)_(?P<location>[-\w\d]+)_(?P<project_id>[0-9]+)/$', 'reblock.views.final_whole'),
]


urlpatterns = patterns('',

    # home
    #(r'^$', 'localcode.views.home'),
    (r'^$', include(interurls4)),
    #(home'^about/$', 'localcode.views.about'),
    #(r'^tools/$', 'localcode.views.tools'),

    # webfinches
    #(r'^reblock/$', 'reblock.views.index'),
    (r'^reblock/$', include(interurls4)),
    #(r'^webfinches/login/create_account/$', 'webfinches.views.create_account'),
    (r'^reblock/upload/$', 'reblock.views.upload'),
    (r'^reblock/review/$', 'reblock.views.review'),

    #(r'^reblock/browse/$', 'reblock.views.browse'),
    (r'^reblock/browse_empty/$', 'reblock.views.upload'), #browse warning
    #(r'^reblock/configure/$', 'reblock.views.configure'),
    #(r'^reblock/get_sites/$', 'reblock.views.get_sites'),
    (r'^reblock/compute/', include(interurls2)),

    #intermediate
    #url(r'^reblock/intermediate/', include(interurls)),
    
    #url(r'^(?P<slug>[-\w\d]+),(?P<id>\d+)/$', view=myviews.article, name='article'),

    #register

    (r'^reblock/register/$', 'reblock.views.register'),
    (r'^reblock/registration_complete/$', 'reblock.views.register'),
    (r'^reblock/username_exists/$', 'reblock.views.register'),
    (r'^reblock/forgot_password/$', 'reblock.views.forgot_password'),
    (r'^set_new_password/$', 'reblock.views.set_new_password'),
    
    #(r'^password_change/$', 'django.contrib.auth.views.password_change'),
    
    #(r'^reblock/password_change/done/$', 'django.contrib.auth.views.password_change_done'),
    #(r'^retrieve_password/$', 'reblock.views.retrieve_password'),
    #(r'^webfinches/user/$', 'webfinches.views.user'),
    
    #profile
    (r'^reblock/profile/$', 'reblock.views.profile'),

    #reload page
    (r'^reblock/reload/$', 'reblock.views.reload'),

    
    
    
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
