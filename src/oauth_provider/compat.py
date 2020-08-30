# -*- coding: utf-8 -*-

from django.conf.urls import url, include  # noqa
from django.contrib.auth import get_user_model  # noqa
from django.conf import settings
from django.utils.crypto import get_random_string  # noqa
from django.utils.timezone import now  # noqa
from django.http import HttpResponse


AUTH_USER_MODEL = settings.AUTH_USER_MODEL


class UnsafeRedirect(HttpResponse):

    def __init__(self, target_url, *args, **kwargs):
        super(UnsafeRedirect, self).__init__(*args, status=302, **kwargs)
        self["Location"] = target_url
