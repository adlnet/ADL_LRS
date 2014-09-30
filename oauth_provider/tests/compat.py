# -*- coding: utf-8 -*-
from django.test import TestCase


class Issue45ErrorLoadingOauthStoreModule(TestCase):
    def test_store_import(self):
        from oauth_provider.store import store
        self.assertIsNotNone(store)

    def test_import_user_from_compat(self):
        from oauth_provider.compat import get_user_model
        from oauth_provider.compat import AUTH_USER_MODEL

        self.assertIsNotNone(get_user_model())
        self.assertIsNotNone(AUTH_USER_MODEL)