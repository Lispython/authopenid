# -*- coding: utf-8 -*-

from django.conf.urls.defaults import *
from lib.j2lib import direct_to_template

urlpatterns = patterns('authopenid.views',
    url(r'^login/$', 'login', name='oid_login'),
    url(r'^logout/$', 'logout', name='oid_logout'),
    url(r'^login/complete/$', 'login_complete', name='oid_complete_signin'),
    url(r'^registration/$', 'registration', name='oid_registration'),
    url(r'^associate/$', 'associate', name='oid_associate'),
    url(r'^associate/complete/$', 'associate_complete', name = 'oid_associate_complete'), 
    url(r'^dissociate/$', 'dissociate', name='oid_dissociate'),
    url(r'^yadis.xrdf$', 'xrdf', name='yadis_xrdf')
)
