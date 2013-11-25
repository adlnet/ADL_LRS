import re
from django.http import HttpResponseBadRequest
                    
class XAPIVersionHeader(object):
    def process_request(self, request):
        try:
            version = request.META['X-Experience-API-Version']
        except:
            try:
                version = request.META['HTTP_X_EXPERIENCE_API_VERSION']
            except:
                version = request.META.get('X_Experience_API_Version', None)
                if not version:
                    import urllib
                    bdy = urllib.unquote_plus(request.body)
                    v = re.search('X\WExperience\WAPI\WVersion=(?P<num>[\d\.]*)\&?', bdy)
                    if v:
                        version = v.group('num')
        if version:
            regex = re.compile("^1\.0(\.\d+)?$")
            if regex.match(version):
                return None
            else:
                return HttpResponseBadRequest("X-Experience-API-Version is not supported")
        else:
            return HttpResponseBadRequest("X-Experience-API-Version header missing")


    def process_response(self, request, response):
        response['X-Experience-API-Version'] = "1.0.1"
        return response
