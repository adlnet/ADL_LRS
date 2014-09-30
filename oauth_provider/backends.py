# -*- coding: utf-8 -*-
import django.core.validators
from compat import get_user_model

User = get_user_model()


class XAuthAuthenticationBackend(object):
    """Custom Authentication Backend. Supports both username and email as
     identification
    """
    supports_anonymous_user = False

    def authenticate(self, x_auth_username=None, x_auth_password=None,
                     x_auth_mode=None):
        """Authenticates a user through the combination
        email/username with password. Returns signed ``User`` instance

        x_auth_username -- a string containing the username or e-mail of
            the user that is trying to authenticate.

        x_auth_password -- string containing the password for the user.
        """
        if x_auth_mode != 'client_auth':
            return None
        try:
            django.core.validators.validate_email(x_auth_username)
            try:
                user = User.objects.get(email__iexact=x_auth_username)
            except User.DoesNotExist:
                return None
        except django.core.validators.ValidationError:
            try:
                user = User.objects.get(username__iexact=x_auth_username)
            except User.DoesNotExist:
                return None

        if user.check_password(x_auth_password):
            return user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None