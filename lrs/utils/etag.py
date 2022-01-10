import hashlib

from ..exceptions import BadRequest, Conflict, PreconditionFail

IF_MATCH = "HTTP_IF_MATCH"
IF_NONE_MATCH = "HTTP_IF_NONE_MATCH"


def create_tag(resource):
    return hashlib.sha1(resource.encode("utf-8")).hexdigest()


def get_etag_info(headers):
    etag = {}
    etag[IF_MATCH] = headers.get(IF_MATCH, None)
    if not etag[IF_MATCH]:
        etag[IF_MATCH] = headers.get('If_Match', None)
    if not etag[IF_MATCH]:
        etag[IF_MATCH] = headers.get('If-Match', None)

    etag[IF_NONE_MATCH] = headers.get(IF_NONE_MATCH, None)
    if not etag[IF_NONE_MATCH]:
        etag[IF_NONE_MATCH] = headers.get('If_None_Match', None)
    if not etag[IF_NONE_MATCH]:
        etag[IF_NONE_MATCH] = headers.get('If-None-Match', None)
    return etag


def check_preconditions(request, contents, created, required=True):
    if required:
        exists = False
        if not created:
            exists = True

        try:
            request_etag = request['headers']['ETAG']
            if not request_etag[IF_MATCH] and not request_etag[IF_NONE_MATCH]:
                if exists:
                    raise MissingEtagInfoExists(
                        "If-Match and If-None-Match headers were missing. One of these headers is required for this request.")
                raise MissingEtagInfo(
                    "If-Match and If-None-Match headers were missing. One of these headers is required for this request.")
        except KeyError:
            if exists:
                raise MissingEtagInfoExists(
                    "If-Match and If-None-Match headers were missing. One of these headers is required for this request.")
            raise MissingEtagInfo(
                "If-Match and If-None-Match headers were missing. One of these headers is required for this request.")
        else:
            # If there are both, if none match takes precendence 
            if request_etag[IF_NONE_MATCH]:
                # only check if the content already exists. if it did not
                # already exist it should pass
                if exists:
                    if request_etag[IF_NONE_MATCH] == "*":
                        raise EtagPreconditionFail("Resource detected")
                    else:
                        if '"%s"' % contents.etag in request_etag[IF_NONE_MATCH]:
                            raise EtagPreconditionFail("Resource detected")
            else:
                if not exists:
                    contents.delete()
                    raise EtagPreconditionFail(
                        "Resource does not exist")
                else:
                    if request_etag[IF_MATCH] != "*":    
                        if '"%s"' % contents.etag not in request_etag[IF_MATCH]:
                            raise EtagPreconditionFail(
                                "No resources matched your etag precondition")
            


class MissingEtagInfo(BadRequest):

    def __init__(self, msg):
        self.message = msg

    def __str__(self):
        return repr(self)

class MissingEtagInfoExists(Conflict):

    def __init__(self, msg):
        self.message = msg

    def __str__(self):
        return repr(self)

class EtagPreconditionFail(PreconditionFail):

    def __init__(self, msg):
        self.message = msg

    def __str__(self):
        return repr(self)
