# -*- coding: utf-8 -*-
import django

from django.conf.urls import patterns, url, include



# in Django>=1.5 CustomUser models can be specified
if django.VERSION >= (1, 5):
    from django.contrib.auth import get_user_model
    from django.conf import settings
    AUTH_USER_MODEL = settings.AUTH_USER_MODEL
else:
    from django.contrib.auth.models import User
    get_user_model = lambda: User
    AUTH_USER_MODEL = "auth.User"

try:
    from django.utils.crypto import get_random_string
except ImportError:
    import random
    # fallback for older versions of django (<=1.3). You shouldn't use them
    get_random_string = lambda length: ''.join([random.choice('abcdefghijklmnopqrstuvwxyz'
                                    'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789') for i in range(length)])

try:
    from django.utils.timezone import now
except ImportError:
    import datetime
    try:
        # this is fallback for old versions of django
        import pytz
        from functools import partial
        now = partial(datetime.datetime.now, tz=pytz.UTC)
    except ImportError:
        # if there is no pytz and this is old version of django, probably
        # no one cares for timezones
        now = datetime.datetime.now


if django.VERSION >= (1, 4):
    from django.http import HttpResponse

    class UnsafeRedirect(HttpResponse):
        def __init__(self, url, *args, **kwargs):
            super(UnsafeRedirect, self).__init__(*args, status=302, **kwargs)
            self["Location"] = url
else:
    from django.http import HttpResponseRedirect as UnsafeRedirect