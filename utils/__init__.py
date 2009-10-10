# -*- coding: utf-8 -*-

import time
import urllib
import logging

from django.conf import settings
from django.utils.html import escape
from openid.extensions import sreg, ax
from openid.consumer.discover import discover
from django.http import str_to_unicode, get_host

from authopenid import settings as app_settings
try: # needed for some linux distributions like debian
    from openid.yadis import xri
except ImportError:
    from yadis import xri


class OpenID(object):
    def __init__(self, openid_, issued, attrs=None, sreg_=None, ax_resp={}):
        self.openid = openid_
        self.issued = issued
        self.attrs = attrs or {}
        self.sreg = sreg_ or {}
        self.ax_resp = ax_resp or {}
        self.is_iname = (xri.identifierScheme(openid_) == 'XRI')
    
    def __repr__(self):
        return '<OpenID: %s>' % self.openid
    
    def __str__(self):
        return self.openid

DEFAULT_NEXT = getattr(settings, 'OPENID_REDIRECT_NEXT', '/')
def clean_next(next):
    if next is None:
        return DEFAULT_NEXT
    next = str_to_unicode(urllib.unquote(next), 'utf-8')
    next = next.strip()
    if next.startswith('/'):
        return next
    return DEFAULT_NEXT


def from_openid_response(openid_response):
    """ return openid object from response """
    issued = int(time.time())
    sreg_resp = sreg.SRegResponse.fromSuccessResponse(openid_response) or []
    ax_resp = ax.FetchResponse.fromSuccessResponse(openid_response)
    ax_data = {}
    if ax_resp is not None:
        ax_args = ax_resp.getExtensionArgs()
        for k, v in app_settings.AX_URIS.items():
            ax_data[k] = ax_resp.getSingle(v, None)
    return OpenID(
        openid_response.identity_url, issued, openid_response.signed_fields, 
         dict(sreg_resp), dict(ax_data)
    )
    
def get_url_host(request):
    if request.is_secure():
        protocol = 'https'
    else:
        protocol = 'http'
    host = escape(get_host(request))
    return '%s://%s' % (protocol, host)

def get_full_url(request):
    return get_url_host(request) + request.get_full_path()

def discover_extensions(openid_url):
    service = discover(openid_url)
    use_ax = False
    use_sreg = False
    for endpoint in service[1]:
        if not use_sreg:
            use_sreg = sreg.supportsSReg(endpoint)
        if not use_ax:
            use_ax = endpoint.usesExtension("http://openid.net/srv/ax/1.0")
        if use_ax and use_sreg: break
    if not use_sreg and not use_ax:
        use_sreg = True
    return use_ax, use_sreg

def get_name(name):
    return app_settings.DETAILS_ALIASES.get(name, name)