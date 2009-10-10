# -*- coding: utf-8 -*-

from django.conf import settings

SREG_FIELDS = [
    'nickname', 'email', 'fullname', 'dob', 'gender',
    'postcode', 'country', 'language', 'timezone']


# This dict contains mapping of SREG fields to AX uris
# http://www.axschema.org/types/
AX_URIS = {
    'nickname': 'http://axschema.org/namePerson/friendly',
    'email': 'http://axschema.org/contact/email',
    'fullname': 'http://axschema.org/namePerson',
    'dob': 'http://axschema.org/birthDate',
    'gender': 'http://axschema.org/person/gender',
    'postcode': 'http://axschema.org/contact/postalCode/home',
    'country': 'http://axschema.org/contact/country/home',
    'language': 'http://axschema.org/pref/language',
    'timezone': 'http://axschema.org/pref/timezone',
}

DEFAULT_DETAILS_FIELDS = (
    ('email', True),
    ('gender', False),
    ('nickname', True),
)

REQUIRED_FIELDS = [field for field, req in getattr( \
    settings, 'OPENID_DETAILS_FIELDS', DEFAULT_DETAILS_FIELDS) if req is True]

OPTIONAL_FIELDS = [field for field, req in getattr( \
    settings, 'OPENID_DETAILS_FIELDS', DEFAULT_DETAILS_FIELDS) if req is False]

DETAILS_ALIASES = getattr(settings,
    'DETAILS_ALIASES', {'nickname': 'username'})
