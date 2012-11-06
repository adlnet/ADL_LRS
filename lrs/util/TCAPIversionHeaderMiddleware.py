from django.http import HttpResponseBadRequest

class TCAPIversionHeaderMiddleware(object):
    def process_request(self, request):
        try:
            version = request.META['X-Experience-APIVersion']
        except:
            try:
                version = request.META['HTTP_X_EXPERIENCE_API_VERSION']
            except:
                version = request.META.get('X_Experience_API_Version', None)
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
