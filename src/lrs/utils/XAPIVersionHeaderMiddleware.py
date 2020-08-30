import re
import urllib
from django.conf import settings
from django.http import HttpResponse


class XAPIVersionHeader(object):

    def process_request(self, request):
        try:
            version = request.META['X-Experience-API-Version']
        except:
            try:
                version = request.META['HTTP_X_EXPERIENCE_API_VERSION']
            except:
                version = request.META.get('X_Experience_API_Version', None)

        if 'CONTENT_TYPE' in request.META:
            content_type = request.META['CONTENT_TYPE']
        elif 'Content-Type' in request.META:
            content_type = request.META['Content-Type']
        else:
            content_type = None

        if content_type and content_type.startswith("application/x-www-form-urlencoded"):
            bdy_parts = urllib.unquote_plus(request.body).split('&')
            for part in bdy_parts:
                v = re.search(
                    'X[-_]Experience[-_]API[-_]Version=(?P<num>.*)', part)
                if v:
                    version = v.group('num')
                    break

        if version:
            if version == '1.0' or (version.startswith('1.0') and \
                version in settings.XAPI_VERSIONS):
                return None
            else:
                resp = HttpResponse("X-Experience-API-Version is not supported", status=400)
                resp['X-Experience-API-Version'] = settings.XAPI_VERSION
                return resp
        else:
            resp = HttpResponse("X-Experience-API-Version header missing", status=400)
            resp['X-Experience-API-Version'] = settings.XAPI_VERSION
            return resp


    def process_response(self, request, response):
        response['X-Experience-API-Version'] = settings.XAPI_VERSION
        return response
