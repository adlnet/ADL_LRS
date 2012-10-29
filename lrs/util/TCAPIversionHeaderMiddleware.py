from django.http import HttpResponseBadRequest
import pdb

class TCAPIversionHeaderMiddleware(object):
    def process_request(self, request):
        if 'X-Experience-APIVersion' in request.META:
            if request.META['X-Experience-API-Version'] == "0.95":
                return None
            else:
                return HttpResponseBadRequest("X-Experience-API-Version is not supported")
        elif 'X_Experience_API_Version' in request.META:
            if request.META['X_Experience_API_Version'] == "0.95":
                return None
            else:
                return HttpResponseBadRequest("X-Experience-API-Version is not supported")
        else:
            return HttpResponseBadRequest("X-Experience-API-Version header missing")


    def process_response(self, request, response):

        response['X-Experience-API-Version'] = "0.95"
        return response
