from django.http import HttpResponse

class AllowOriginMiddleware(object):
	def process_request(self, request):
		if request.method == 'OPTIONS':
			return HttpResponse()

	def process_response(self, request, response):
		protocol = 'https' if request.is_secure() else 'http'
		port = None
		if 'SERVER_PORT' in request.META:
			port = request.META['SERVER_PORT']
			response['Access-Control-Allow-Origin'] = "%s://%s:%s" % (protocol, request.META['SERVER_NAME'], port)
		else:
			response['Access-Control-Allow-Origin'] = "%s://%s" % (protocol, request.META['SERVER_NAME'])
		response['Access-Control-Allow-Methods'] = 'HEAD, POST, GET, OPTIONS, DELETE, PUT'
		response['Access-Control-Allow-Headers'] = 'Content-Type,Content-Length,Authorization,If-Match,If-None-Match,X-Experience-API-Version, Accept-Language'
		response['Access-Control-Expose-Headers'] = 'ETag,Last-Modified,Cache-Control,Content-Type,Content-Length,WWW-Authenticate,X-Experience-API-Version, Accept-Language'
		return response