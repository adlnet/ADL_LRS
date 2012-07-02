import hashlib

IF_MATCH = "HTTP_IF_MATCH"
IF_NONE_MATCH = "HTTP_IF_NONE_MATCH"

def create_tag(resource):
    return hashlib.sha1(resource).hexdigest()

def get_etag_info(request, required=True):
	etag = {}
	etag[IF_MATCH] = request.META.get(IF_MATCH, None)
	etag[IF_NONE_MATCH] = request.META.get(IF_NONE_MATCH, None)
	if required and not etag[IF_MATCH] and not etag[IF_NONE_MATCH]:
		raise MissingEtagInfo("If-Match and If-None-Match headers were missing. One of these headers is required for this request.")
	return etag

def check_preconditions(request, contents):
	print 'checking preconditions'
	try:
		request_etag = request['ETAG']
	except KeyError:
		return
	if request_etag[IF_NONE_MATCH]:
		print 'in if none match'
		if request_etag[IF_NONE_MATCH] == "*" and contents:
			raise EtagPreconditionFail("Resource detected")
		elif contents:
			if contents.etag in request_etag[IF_NONE_MATCH]:
				raise EtagPreconditionFail("Resource detected")
	if request_etag[IF_MATCH]:
		print 'in if match'
		if request_etag[IF_MATCH] != "*":
			if contents.etag in request_etag[IF_MATCH]:
				return
			raise EtagPreconditionFail("No resources matched your etag precondition: %s" % request_etag[IF_MATCH])

class MissingEtagInfo(Exception):
    def __init__(self, msg):
        self.message = msg
    def __str__(self):
        return repr(self.message)

class EtagPreconditionFail(Exception):
	def __init__(self, msg):
		self.message = msg
	def __str__(self):
		return repr(self.message)