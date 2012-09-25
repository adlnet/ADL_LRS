from django.http import HttpResponse


class AllowOriginMiddleware(object):
    def process_request(self, request):
        # if request.method == 'OPTIONS':
        #     resp = HttpResponse()
        #     resp['Access-Control-Allow-Origin'] = '*'
        #     resp['Access-Control-Allow-Methods'] = 'POST, GET, OPTIONS, DELETE, PUT'
        #     resp['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        #     return 
        if request.method == 'OPTIONS':
            return HttpResponse()

    def process_response(self, request, response):
        #origin = request.META.get('HTTP_ORIGIN')
        #if origin:
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'HEAD, POST, GET, OPTIONS, DELETE, PUT'
        response['Access-Control-Allow-Headers'] = 'Content-Type,Content-Length,Authorization,If-Matches,If-None-Matches,X-Experience-API-Version'
        response['Access-Control-Expose-Headers'] = 'ETag,Last-Modified,Cache-Control,Content-Type,Content-Length,WWW-Authenticate,X-Experience-API-Version'
        return response