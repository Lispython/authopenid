# -*- coding: utf-8 -*-

import os
import random
import sys
import time
try:
    from hashlib import md5 as _md5
except ImportError:
    import md5
    _md5 = md5.new

from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.utils.translation import ugettext as _
from django.template.loader import render_to_string


__all__ = ['Nonce', 'Association', 'UserAssociation']

class Nonce(models.Model):
    server_url = models.CharField(max_length=255)
    timestamp = models.IntegerField()
    salt = models.CharField(max_length=40)
    
    def __unicode__(self):
        return _("Nonce: %s" % self.id)
    
    class Meta:
        db_table = 'Nonce'
        verbose_name = _('Nonce')
        verbose_name_plural = _('Nonces')
        

class Association(models.Model):
    server_url = models.TextField(max_length=2047)
    handle = models.CharField(max_length=255)
    secret = models.TextField(max_length=255) # Stored base64 encoded
    issued = models.IntegerField()
    lifetime = models.IntegerField()
    assoc_type = models.TextField(max_length=64)
    
    def __unicode__(self):
        return _("Association: %(url)s, %(handle)s" % {'url': self.server_url, 'handle':self.handle})
    class Meta:
        db_table = 'Association'
        verbose_name = _('Association')
        verbose_name_plural = _('Associations')

class UserAssociation(models.Model):
    openid_url = models.CharField(primary_key=True, blank=False, max_length=255)
    user = models.ForeignKey(User)
    
    def __unicode__(self):
        return _("Openid %(url)s with user %(user)s" % {'url': self.openid_url, 'user': self.user})
        
    def save(self, send_email=False):
        super(UserAssociation, self).save()
        if send_email:
            from django.core.mail import send_mail
            current_site = Site.objects.get_current()
            subject = render_to_string('authopenid/associate_email_subject.txt',
                                       { 'site': current_site,
                                         'user': self.user})
            message = render_to_string('authopenid/associate_email.txt',
                                       { 'site': current_site,
                                         'user': self.user,
                                         'openid': self.openid_url
                                        })

            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [self.user.email])
    
    class Meta:
        db_table = 'user_association'
        verbose_name = _('User association')
        verbose_name_plural = _('User associations')
        
