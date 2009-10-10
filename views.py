# -*- coding: utf-8 -*-

import urllib
import logging

from django import forms
from django.conf import settings
from django.utils.http import urlquote
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.utils.encoding import smart_unicode
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.template import RequestContext, Context, Template


from openid.extensions import ax
from openid.extensions import sreg
from openid.consumer.discover import DiscoveryFailure
from openid.consumer.consumer import Consumer, SUCCESS, CANCEL, FAILURE, SETUP_NEEDED

from models import *
from decorators import not_authenticated
from openid_store import DjangoOpenIDStore
from authopenid import settings as app_settings
from forms import OpenidSigninForm, OpenidRegisterForm
from utils import get_url_host, from_openid_response, clean_next, discover_extensions, get_name

from lib.j2lib import render_to_response
from lib.j2lib.decorators import render_to


try:
    from openid.yadis import xri
except ImportError:
    from yadis import xri

@not_authenticated
def signin(request):
    form = OpenidSigninForm()
    if request.method == 'POST':
        form = OpenidSigninForm(request.POST)
    else:
        form = OpenidSigninForm()
        
    redirect_to = request.POST.get('next', None) or getattr(settings, 'LOGIN_REDIRECT_URL', '/')
    if form.is_valid():
        openid_url = form.cleaned_data['openid_url']
        use_ax, use_sreg = discover_extensions(openid_url)
        user = None
        try:
            user = UserAssociation.objects.get(openid_url=openid_url).user
        except UserAssociation.DoesNotExist, e:
            pass
        return_to = "%s%s?%s" % (
                        get_url_host(request),
                        reverse('user_complete_signin'),
                        urllib.urlencode({'next': urlquote(redirect_to)})
                )
        trust_root = getattr(settings, 'OPENID_TRUST_ROOT', get_url_host(request) + '/')
        consumer = Consumer(request.session, DjangoOpenIDStore())
        try:
            auth_request = consumer.begin(openid_url)
            if not user:
                if use_sreg:
                    sreg_request = sreg.SRegRequest(
                                        optional = app_settings.OPTIONAL_FIELDS,
                                        required = app_settings.REQUIRED_FIELDS,
                                        )
                    auth_request.addExtension(sreg_request)
                    
                if use_ax:
                    ax_request = ax.FetchRequest()
                    for detail, req in app_settings.DEFAULT_DETAILS_FIELDS:
                        ax_request.add(ax.AttrInfo(app_settings.AX_URIS[detail], required=req))
                    auth_request.addExtension(ax_request)
            
            url = auth_request.redirectURL(trust_root, return_to)
            return HttpResponseRedirect(url)
        except DiscoveryFailure:
            error = _('Could not find OpenID server')
            form.errors['openid_url'] = error
    
    return render_to_response('authopenid/signin.html',
        {
            'form': form,
            'next': request.GET.get('next', '')
         },
        request
    )


@not_authenticated
def complete(request):
    redirect_to = request.GET.get('next', None) or getattr(settings, 'LOGIN_REDIRECT_URL', '/')
    consumer = Consumer(request.session, DjangoOpenIDStore())
    args = dict(request.GET.items())
    openid_response = consumer.complete(args, request.build_absolute_uri(reverse('user_complete_signin')))
    if openid_response.status == SUCCESS:
        request.session['openid'] = from_openid_response(openid_response)
        user = authenticate(openid_url=openid_response.identity_url)
        if user:
            login(request, user)
            logging.debug(u'Авторизирован как %s', user)
            return HttpResponseRedirect(redirect_to)
        else:
            return HttpResponseRedirect(u"%s?%s" % (reverse('user_openid_registration'), \
                                                    urllib.urlencode({'next': urlquote(redirect_to)})))
    elif openid_response.status == CANCEL:
        return failure(request, _(u'Вы отменили авторизации у своего OpenID провадера'))
    elif openid_response.status == FAILURE:
        return failure(request, openid_response.message)
    elif openid_response.status == SETUP_NEEDED:
        return failure(request, _('Setup needed'))
    else:
        assert False, "Bad openid status: %s" % openid_response.status

    return render_to_response('authopenid/complete.html',
        {
            'next': request.GET.get('next', '')
         },
        request
    )
    
@not_authenticated
def registration(request):
    openid = request.session.get('openid', None)
    next = request.GET.get('next', '')
    if not openid or openid is None:
        return HttpResponseRedirect(u"%s?%s" % (reverse('user_signin'), urllib.urlencode({'next': urlquote(next)})))
    pinitial = openid.sreg
    logging.debug(openid.sreg)
    logging.debug(openid.ax_resp)
    if openid.ax_resp:
        for k, v in openid.ax_resp.items():
            if not pinitial.get(k):
                pinitial[k] = v
    logging.debug(u"Окончательные данные \n %s" % pinitial)
    initial = {}
    for k, v in pinitial.items():
        initial[get_name(k)] = v
    if request.method == 'POST':
        form = OpenidRegisterForm(request.POST)
    else:
        form = OpenidRegisterForm(initial)
        
    if form.is_valid():
        user = User.objects.create_user(form.cleaned_data['username'], form.cleaned_data['email'])
        user.backend = "authopenid.backends.OpenIDBackend"
        if user is not None:
            uassoc = UserAssociation(openid_url=str(openid), user_id=user.id)
            uassoc.save(send_email=False)
            login(request, user)
            return HttpResponseRedirect(urlquote(next))
    return render_to_response('authopenid/registration.html',
        {
            'form': form,
            'next': next
         },
        request
    )

    
def failure(request, message, **kwargs):
    return render_to_response('authopenid/failure.html',
        {
            'message':message,
         },
        request
    )

@login_required
def signout(request):
    next = request.GET.get('next', '/')
    try:
        del request.session['openid']
    except KeyError:
        pass
    next = clean_next(next)
    logout(request)
    return HttpResponseRedirect(next)
    
    
def xrdf(request, template_name='authopenid/yadis.xrdf'):
    url_host = get_url_host(request)
    return_to = [
        "%s%s" % (url_host, reverse('user_complete_signin'))
    ]
    return render_to_response(template_name, { 
        'return_to': return_to 
        }, request)