import hashlib

from ..exceptions import Conflict, PreconditionFail

IF_MATCH = "HTTP_IF_MATCH"
IF_NONE_MATCH = "HTTP_IF_NONE_MATCH"

def create_tag(resource):
    return hashlib.sha1(resource).hexdigest()

def get_etag_info(headers, required=True):
    etag = {}
    etag[IF_MATCH] = headers.get(IF_MATCH, None) 
    if not etag[IF_MATCH]:
        etag[IF_MATCH] = headers.get('If_Match', None)
    if not etag[IF_MATCH] and 'If-Match' in headers:
        etag[IF_MATCH] = headers['If-Match']

    etag[IF_NONE_MATCH] = headers.get(IF_NONE_MATCH, None)
    if not etag[IF_NONE_MATCH]:
        etag[IF_NONE_MATCH] = headers.get('If_None_Match', None)
    if not etag[IF_NONE_MATCH] and 'If-None-Match' in headers:
        etag[IF_NONE_MATCH] = headers['If-None-Match']

    if required and not etag[IF_MATCH] and not etag[IF_NONE_MATCH]:
        raise MissingEtagInfo("If-Match and If-None-Match headers were missing. One of these headers is required for this request.")
    return etag

def check_preconditions(request, contents, required=False):
    try:
        request_etag = request['headers']['ETAG']
        if not request_etag[IF_MATCH] and not request_etag[IF_NONE_MATCH]:
            request_etag = None
    except KeyError:
        request_etag = None

    if not request_etag and not required:
        return
    elif not request_etag and required:
        raise MissingEtagInfo("If-Match and If-None-Match headers were missing. One of these headers is required for this request.")

    if request_etag[IF_NONE_MATCH]:
        if request_etag[IF_NONE_MATCH] == "*" and contents:
            raise EtagPreconditionFail("Resource detected")
        elif contents:
            if contents.etag in request_etag[IF_NONE_MATCH]:
                raise EtagPreconditionFail("Resource detected")
    elif request_etag[IF_MATCH]:
        if request_etag[IF_MATCH] != "*":
            if contents.etag in request_etag[IF_MATCH]:
                return
            raise EtagPreconditionFail("No resources matched your etag precondition: %s" % request_etag[IF_MATCH])
    else:
        raise MissingEtagInfo("If-Match and If-None-Match headers were missing. One of these headers is required for this request.")

class MissingEtagInfo(Conflict):
    def __init__(self, msg):
        self.message = msg
    def __str__(self):
        return repr(self.message)

class EtagPreconditionFail(PreconditionFail):
    def __init__(self, msg):
        self.message = msg
    def __str__(self):
        return repr(self.message)