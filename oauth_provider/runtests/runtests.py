#!/usr/bin/env python
# -*- coding: utf-8 -*-

# https://github.com/swistakm/django-rest-framework/blob/master/rest_framework/runtests/runtests.py
import os
import sys

# fix sys path so we don't need to setup PYTHONPATH
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
os.environ['DJANGO_SETTINGS_MODULE'] = 'oauth_provider.runtests.settings'

from django.conf import settings
from django.test.utils import get_runner
from south.management.commands import patch_for_test_db_setup

def usage():
    return """
    Usage: python runtests.py [UnitTestClass].[method]

    You can pass the Class name of the `UnitTestClass` you want to test.

    Append a method name if you only want to test a specific method of that class.
    """


def main():
    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=2)

    if len(sys.argv) == 2:
        test_case = '.' + sys.argv[1]
    elif len(sys.argv) == 1:
        test_case = ''
    else:
        print(usage())
        sys.exit(1)

    patch_for_test_db_setup()
    failures = test_runner.run_tests(['tests' + test_case])

    sys.exit(failures)

if __name__ == '__main__':
    main()
