# -*- coding: utf-8 -*-

from django.contrib import admin
from authopenid.models import UserAssociation, Association, Nonce


class UserAssociationAdmin(admin.ModelAdmin):
    """User association admin class"""
    pass
    
class AssociationAdmin(admin.ModelAdmin):
    """User association admin class"""
    pass
    
class NonceAdmin(admin.ModelAdmin):
    """User association admin class"""
    pass
    
admin.site.register(UserAssociation, UserAssociationAdmin)
admin.site.register(Association, AssociationAdmin)
admin.site.register(Nonce, NonceAdmin)