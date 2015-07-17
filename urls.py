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

]
interurls2 = [url(r'^$', 'reblock.views.compute'),
             url(r'^(?P<slot_user>[-\w\d]+)_(?P<project_name>[-\w\d]+)_(?P<location>[-\w\d]+)_(?P<project_id>[0-9]+)/', include(interurls3)),
]

interurls4 = [url(r'^$', 'reblock.views.recent'),

]


urlpatterns = patterns('',

    # home
    (r'^$', include(interurls4)),
    (r'^reblock/$', include(interurls4)),
    (r'^reblock/upload/$', 'reblock.views.upload'),
    (r'^reblock/review/$', 'reblock.views.review'),
    (r'^reblock/browse_empty/$', 'reblock.views.upload'), #browse warning
    (r'^reblock/compute/', include(interurls2)),

    #register
    (r'^reblock/register/$', 'reblock.views.register'),
    (r'^reblock/registration_complete/$', 'reblock.views.register'),
    (r'^reblock/registration_failed/$', 'reblock.views.register'),
    (r'^reblock/username_exists/$', 'reblock.views.register'),
    (r'^reblock/forgot_password/$', 'reblock.views.forgot_password'),
    (r'^set_new_password/$', 'reblock.views.set_new_password'),
        
    #profile
    (r'^reblock/profile/$', 'reblock.views.profile'),

    #reload page
    (r'^reblock/reload/$', 'reblock.views.reload'),
    (r'^reblock/reload_step/$', 'reblock.views.reload_step'),
    (r'^reblock/check_step/$', 'reblock.views.check_step'),
    (r'^reblock/recent_index/$', 'reblock.views.recent_index'),
    (r'^reblock/profile_index/$', 'reblock.views.profile_index'),
    (r'^reblock/download', 'reblock.views.download'),

    
    # Login / logout.
    (r'^login/$', login, {'template_name': 'registration/login.html'}),
    (r'^logout/$', 'django.contrib.auth.views.logout' ),

    # Serve static content.
    (r'^static/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': 'static'}),

    # admin
    (r'^admin/', include(admin.site.urls)),
    # admin documentation
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    


)
