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

def compare(request_etag, contents):
	content_hash = create_tag(contents)
	if request_etag[IF_NONE_MATCH]:
		if request_etag[IF_NONE_MATCH] == "*" and not contents:
			return True
		else:
			for etag in request_etag[IF_NONE_MATCH]:
				if etag == content_hash:
					raise EtagPreconditionFail("Resource detected")
		return True
	if request_etag[IF_MATCH] == "*":
		return True
	else:
		for etag in request_etag[IF_MATCH]:
			if etag == content_hash:
				return True
		raise EtagPreconditionFail("")

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