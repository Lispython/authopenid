# -*- coding: utf-8 -*-


def authopenid(request):
    """
    Returns context variables required by apps that use django-authopenid.
    """
    if hasattr(request, 'openid'):
        openid = request.openid
    else:
        openid = None
        
    if hasattr(request, 'openids'):
        openids = request.openids
    else:
        openids = []
        
    if hasattr(request, 'associated_openids'):
        associated_openids = request.associated_openids
    else:
        associated_openids = []
        
    return {
        "openid": openid,
        "openids": openids,
        "associated_openids": associated_openids,
        "signin_with_openid": (openid is not None),
        "has_openids": (len(associated_openids) > 0)
    }