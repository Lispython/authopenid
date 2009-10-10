# -*- coding: utf-8 -*-


from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse

from models import UserAssociation
from utils.mimeparse import best_match


__all__ = ["OpenIDMiddleware"]

class OpenIDMiddleware(object):
    """
    Populate request.openid. This comes either from cookie or from
    session, depending on the presence of OPENID_USE_SESSIONS.
    """
    def process_request(self, request):
        request.openid = request.session.get('openid', None)
        request.openids = request.session.get('openids', [])
        
        rels = UserAssociation.objects.filter(user__id=request.user.id)
        request.associated_openids = [rel.openid_url for rel in rels]
    
    def process_response(self, request, response):
        if response.status_code != 200 or len(response.content) < 200:
            return response
        path = request.get_full_path()
        if path == "/" and request.META.has_key('HTTP_ACCEPT') and \
                best_match(['text/html', 'application/xrds+xml'], 
                    request.META['HTTP_ACCEPT']) == 'application/xrds+xml':
            return HttpResponseRedirect(reverse('yadis_xrdf'))
        return response