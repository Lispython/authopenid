# -*- coding: utf8 -*-

from django.contrib.auth.models import User

from authopenid.models import UserAssociation

class OpenIDBackend(object):
    def authenticate(self, openid_url=None):
        if openid_url:
            try:
                user  = UserAssociation.objects.get(openid_url=openid_url).user
                return user
            except UserAssociation.DoesNotExist:
                return None
        else:
            return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
