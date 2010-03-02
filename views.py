# -*- coding: utf-8 -*-

import urllib
import logging

from django.conf import settings
from django.utils.http import urlquote
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required
from django.contrib import auth as cauth
from django.contrib import messages
from django.contrib.auth import REDIRECT_FIELD_NAME

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

 
def ask_openid(request, openid_url, callback_url, redirect_to, user = None):
    """Функция формирования запроса к серверу в соответствии со спецификацией
    """
    use_ax, use_sreg = discover_extensions(openid_url)
    return_to = "%s%s?%s" % (
                    get_url_host(request),
                    callback_url,
                    urllib.urlencode({REDIRECT_FIELD_NAME: urlquote(redirect_to)})
            )
    trust_root = getattr(settings, 'OPENID_TRUST_ROOT', get_url_host(request) + '/')
    consumer = Consumer(request.session, DjangoOpenIDStore())
    try:
        auth_request = consumer.begin(openid_url)
    except DiscoveryFailure, e:
        return failure(request, e)
    if not user:
        if use_sreg:
            logging.debug(u'Сервер использует sreg')
            sreg_request = sreg.SRegRequest(
                optional = app_settings.OPTIONAL_FIELDS,
                required = app_settings.REQUIRED_FIELDS,
                )
            auth_request.addExtension(sreg_request)

        if use_ax:
            logging.debug(u'Сервер использует ax')
            ax_request = ax.FetchRequest()
            for detail, req in app_settings.DEFAULT_DETAILS_FIELDS:
                ax_request.add(ax.AttrInfo(app_settings.AX_URIS[detail], required=req))
            auth_request.addExtension(ax_request)
    url = auth_request.redirectURL(trust_root, return_to)
    logging.debug(u"Переадресуем по адресу: %s" % url)
    return HttpResponseRedirect(url)

def default_on_failure(request, message):
    """Дефолтный вид для неудачных запросов"""
    return render_to_response('authopenid/failure.html',
        {
            'message': message,
            'form': OpenidSigninForm()
         },
        request
    )

def default_on_success(request, openid_response, message):
    """Дефолтный вид лля удачных запросов"""
    request.session['openid'] = from_openid_response(openid_response)
    return render_to_response('authopenid/success.html',
        {
            'message': message,
         },
        request
    )

    

@not_authenticated
def login(request):
    form = OpenidSigninForm()
    if request.method == 'POST':
        form = OpenidSigninForm(request.POST)
    else:
        form = OpenidSigninForm()
        
    redirect_to = request.POST.get(REDIRECT_FIELD_NAME, None) or getattr(settings, 'LOGIN_REDIRECT_URL', '/')
    if form.is_valid():
        openid_url = form.cleaned_data['openid_url']
        user = None
        try:
            user = UserAssociation.objects.get(openid_url=openid_url).user
        except UserAssociation.DoesNotExist, e:
            logging.debug(u'Пользователя с идентификатором %s не зарегистрировано' % openid_url)
            user = None
        return ask_openid(request, openid_url, reverse('oid_complete_signin'), redirect_to, user)
            
    return render_to_response('authopenid/signin.html',
        {
            'form': form,
            'next': request.GET.get(REDIRECT_FIELD_NAME, '')
         },
        request
    )



def complete(request, on_success = None, on_failure = default_on_failure, return_to = None, **kwargs ):
    """Обработка openid_response от провадера
    """
    redirect_to = request.GET.get(REDIRECT_FIELD_NAME, None) or getattr(settings, 'LOGIN_REDIRECT_URL', '/')
    consumer = Consumer(request.session, DjangoOpenIDStore())
    args = dict(request.GET.items())
    openid_response = consumer.complete(args, request.build_absolute_uri(return_to))
    if openid_response.status == SUCCESS:
        return on_success(request, openid_response, redirect_to)
    elif openid_response.status == CANCEL:
        return on_failure(request, _(u'Вы отменили авторизации у своего OpenID провадера'))
    elif openid_response.status == FAILURE:
        return on_failure(request, openid_response.message)
    elif openid_response.status == SETUP_NEEDED:
        return on_failure(request, _('Setup needed'))
    else:
        assert False, _("Bad openid status: %s") % openid_response.status

    return render_to_response('authopenid/complete.html',
        {
            REDIRECT_FIELD_NAME: redirect_to
         },
        request
    )



def login_success(request, openid_response, redirect_to):
    """
    Обработка успешного ответа для логина по openid
    """
    request.session['openid'] = from_openid_response(openid_response)
    user = cauth.authenticate(openid_url=openid_response.identity_url)
    if user:
        cauth.login(request, user)
        logging.debug(u'Авторизирован как %s', user)
        return HttpResponseRedirect(redirect_to)
    else:
        logging.debug(u"Незарегистрирован %s" % request.session.get('openid'))
        return HttpResponseRedirect(u"%s?%s" % (reverse('oid_registration'), \
                                                urllib.urlencode({REDIRECT_FIELD_NAME: urlquote(redirect_to)})))


@not_authenticated
def login_complete(request):
    """Callback для логина
    """
    return complete(request, login_success, default_on_failure, return_to = reverse('oid_complete_signin'))


@not_authenticated
def registration(request):
    openid = request.session.get('openid', None)
    next = request.GET.get(REDIRECT_FIELD_NAME, '')
    if not openid or openid is None:
        return HttpResponseRedirect(u"%s?%s" % (reverse('oid_login'), urllib.urlencode({REDIRECT_FIELD_NAME: urlquote(next)})))
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
            cauth.login(request, user)
            return HttpResponseRedirect(urlquote(next))
    return render_to_response('authopenid/registration.html',
        {
            'form': form,
            REDIRECT_FIELD_NAME: next
         },
        request
    )

    

@login_required
def logout(request):
    next = request.GET.get(REDIRECT_FIELD_NAME, '/')
    try:
        del request.session['openid']
    except KeyError:
        pass
    next = clean_next(next)
    cauth.logout(request)
    return HttpResponseRedirect(next)


@login_required
def associate(request):
    """Функция вида для ввода нового openid для ассоциации
    """
    redirect_to = request.GET.get(REDIRECT_FIELD_NAME, None) or getattr(settings, 'LOGIN_REDIRECT_URL', '/')
    form = OpenidSigninForm()
    if request.method == 'POST':
        form = OpenidSigninForm(request.POST)
        if form.is_valid():
            try:
                openid_url=form.cleaned_data['openid_url']
                if UserAssociation.objects.filter(openid_url = openid_url):
                    return default_on_failure(request, _('Openid идетификатор %s уже зарегистрирован в системе') % openid_url)
            except UserAssociation.DoesNotExist, e:
                logging.debug(u'Пользователя с идентификатором %s не зарегистрировано' % openid_url)
            return ask_openid(request, form.cleaned_data['openid_url'],  reverse('oid_associate_complete'), redirect_to, request.user)
    else:
        form = OpenidSigninForm()
        
    return render_to_response('authopenid/associate.html', {
        'form': form,
        REDIRECT_FIELD_NAME: redirect_to
        }, request)


def associate_success(request, openid_response,  redirect_to):
    openids =  request.session.get('openids', [])
    openid = from_openid_response(openid_response)
    openids.append(openid)
    request.session['openids'] = openids
    uassoc = UserAssociation(openid_url=str(openid), user_id=request.user.id)
    uassoc.save(send_email=False)
    messages.info(request, _('Openid идентификатор успешно добавлен'))
    return HttpResponseRedirect(urllib.urlencode(urlquote(redirect_to)))



@login_required
def associate_complete(request):
    return complete(request, associate_success, return_to = reverse('oid_associate_complete'))


@login_required
def dissociate(request):
    """Диссоциация openid идентификатора
    
    Arguments:
    - `request`:
    """
    redirect_to = request.GET.get(REDIRECT_FIELD_NAME, None) or request.path or getattr(settings, 'LOGIN_REDIRECT_URL', '/')
    openid_url =  request.GET.get('openid_url', None)
    if not openid_url:
        messages.warning(request, _(u'Вы не указали openid идентификатор.'))
        return HttpResponseRedirect(redirect_to)
    rels =  UserAssociation.objects.filter(user__id = request.user.id)
    associated_openids =  [rel.openid_url for rel in rels]
    if len(associated_openids) ==  1 and  request.user.has_usable_password():
        messages.warning(request, _(u"У вас должен быть установлен пароль"))
        return HttpResponseRedirect(redirect_to)
    UserAssociation.objects.get(openid_url__exact=openid_url).delete()
    if openid_url == request.session.get('openid_url'):
        del request.session['openid_url']
    messages.info(request, _(u"Идентификатор удален"))
    return HttpResponseRedirect(redirect_to)


@render_to('authopenid/yadis.xrdf')    
def xrdf(request):
    url_host = get_url_host(request)
    return_to = [
        "%s%s" % (url_host, reverse('oid_complete_signin'))
    ]
    return { 
        'return_to': return_to 
        }
