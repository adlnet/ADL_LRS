from django.http import HttpResponseBadRequest
from lrs.util import convert_to_dict

class TCAPIversionHeaderMiddleware(object):
    def process_request(self, request):
        try:
            version = request.META['X-Experience-API-Version']
        except:
            try:
                version = request.META['HTTP_X_EXPERIENCE_API_VERSION']
            except:
                version = request.META.get('X_Experience_API_Version', None)
                if not version:
                    import re
                    import urllib
                    bdy = urllib.unquote_plus(request.body)
                    v = re.search('X\WExperience\WAPI\WVersion=(?P<num>[\d\.]*)\&?', bdy)
                    if v:
                        version = v.group('num')
        if version:
            if version == "0.95":
                return None
            else:
                return HttpResponseBadRequest("X-Experience-API-Version is not supported")
        else:
            return HttpResponseBadRequest("X-Experience-API-Version header missing")


    def process_response(self, request, response):
        response['X-Experience-API-Version'] = "0.95"
        return response
