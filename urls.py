# -*- coding: utf-8 -*-

from django.conf.urls.defaults import *

urlpatterns = patterns('authopenid.views',
    url(r'^login/$', 'signin', name='user_signin'),
    url(r'^logout/$', 'signout', name='user_signout'),
    url(r'^login/complete/$', 'complete', name='user_complete_signin'),
    url(r'^openid_registration/$', 'registration', name='user_openid_registration'),
    url(r'^yadis.xrdf$', 'xrdf', name='yadis_xrdf'),
)