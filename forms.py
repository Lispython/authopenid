# -*- coding: utf-8 -*-

import re
import datetime

from django import forms
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.utils.translation import ugettext as _
from django.conf import settings

try:
    from openid.yadis import xri
except ImportError:
    from yadis import xri
    
from authopenid.models import UserAssociation

    
class OpenidSigninForm(forms.Form):
    """
        Форма для ввода OpenID идентификатора
    """
    openid_url = forms.CharField(max_length=255, widget=forms.widgets.TextInput(attrs={'class': 'required openid'}))
            
    def clean_openid_url(self):
        """
            Проверка введённого OpenID идентификатора
        """
        if 'openid_url' in self.cleaned_data:
            openid_url = self.cleaned_data['openid_url']
            if xri.identifierScheme(openid_url) == 'XRI' and getattr(
                settings, 'OPENID_DISALLOW_INAMES', False
                ):
                raise forms.ValidationError(_('i-names are not supported'))
            return self.cleaned_data['openid_url']


attrs_dict = { 'class': 'required login' }
username_re = re.compile(r'^[\w]+$', re.U)

class OpenidRegisterForm(forms.Form):
    """ openid signin form """
    username = forms.CharField(label=_(u'User name'), max_length=30, widget=forms.widgets.TextInput(attrs=attrs_dict))
    email = forms.EmailField(label=_(u'Email address'), widget=forms.TextInput(attrs=dict(attrs_dict, maxlength=200)))
    website = forms.URLField(label=_(u'Ваш вебсайт'), required=False, max_length=255, widget=forms.TextInput(attrs={'size' : 35}))
    birthday = forms.DateField(label=_(u'Ваш день рождения'), required=False,  help_text=u'Ведите дату в формате: ГГГГ-ММ-ДД', widget=forms.TextInput(attrs={'size' : 35}))
    about = forms.CharField(label=_(u'Немного о себе'), required=False, widget=forms.Textarea(attrs={'cols' : 60}))

    def clean_email(self):
        if 'email' in self.cleaned_data:
            try:
                user = User.objects.get(email = self.cleaned_data['email'])
            except User.DoesNotExist:
                return self.cleaned_data['email']
            except User.MultipleObjectsReturned:
                raise forms.ValidationError(u'Такие пользователи уже зарегистрированы')
            raise forms.ValidationError("Такой электронный адрес уже зарегистрирован в нашей базу. Попробуйте другой.")
        else:
            return self.cleaned_data['email']
            
    
    def clean_username(self):
        """ test if username is valid and exist in database """
        if 'username' in self.cleaned_data:
            if not username_re.search(self.cleaned_data['username']):
                raise forms.ValidationError(_(u"Можно использовать цыфробуквы и знаки подчёркивания"))
            try:
                user = User.objects.get(
                        username__exact = self.cleaned_data['username']
                )
            except User.DoesNotExist:
                return self.cleaned_data['username']
            except User.MultipleObjectsReturned:
                raise forms.ValidationError(u'Уже есть несколько пользователь с таким именем, используйте другие.')
            self.user = user
            raise forms.ValidationError(_(u"Такой пользователь уже зарегистрирован, используёте другое имя."))

                
                
class AssociateOpenID(forms.Form):
    """ new openid association form """
    openid_url = forms.CharField(max_length=255, 
            widget=forms.widgets.TextInput(attrs={'class': 'required openid'}))

    def __init__(self, user, *args, **kwargs):
        super(AssociateOpenID, self).__init__(*args, **kwargs)
        self.user = user
            
    def clean_openid_url(self):
        """ test if openid is accepted """
        if 'openid_url' in self.cleaned_data:
            openid_url = self.cleaned_data['openid_url']
            if xri.identifierScheme(openid_url) == 'XRI' and getattr(
                settings, 'OPENID_DISALLOW_INAMES', False
                ):
                raise forms.ValidationError(_('i-names are not supported'))
                
            try:
                rel = UserAssociation.objects.get(openid_url__exact=openid_url)
            except UserAssociation.DoesNotExist:
                return self.cleaned_data['openid_url']
            
            if rel.user != self.user:
                raise forms.ValidationError(_("This openid is already \
                    registered in our database by another account. Please choose another."))
                    
            raise forms.ValidationError(_("You already associated this openid to your account."))
            
class OpenidDissociateForm(OpenidSigninForm):
    """ form used to dissociate an openid. """
    openid_url = forms.CharField(max_length=255, widget=forms.widgets.HiddenInput())