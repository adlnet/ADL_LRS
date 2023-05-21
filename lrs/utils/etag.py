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


def check_modification_conditions(request, record, created, required=True):
    if not required:
        return

    record_already_exists = not created
    etag_headers = request['headers'].get('ETAG')
    
    if etag_headers is None:
        raise MissingEtagInfo("Could not determine etag headers for this request.")

    header_if_match = etag_headers.get(IF_MATCH)
    header_if_none_match = etag_headers.get(IF_NONE_MATCH)

    has_if_match = header_if_match is not None
    has_if_none_match = header_if_none_match is not None

    missing_if_match = not has_if_match
    missing_if_none_match = not has_if_none_match

    if missing_if_match and missing_if_none_match:
        raise MissingEtagInfo("If-Match and If-None-Match headers were missing. One of these headers is required for this request.")
    
    # If there are both, if none match takes precendence 
    if has_if_none_match:
        # Only check if the content already exists. if it did not
        # already exist it should pass.
        if record_already_exists:
            if etag_headers[IF_NONE_MATCH] == "*":
                raise EtagPreconditionFail("Resource detected")
            else:
                if f'"{record.etag}"' in etag_headers[IF_NONE_MATCH]:
                    raise EtagPreconditionFail("Resource detected")
    
    if has_if_match:
        if created:
            record.delete()
            raise EtagPreconditionFail("Resource does not exist")
        else:
            if etag_headers[IF_MATCH] != "*":    
                if f'"{record.etag}"' not in etag_headers[IF_MATCH]:
                    raise EtagPreconditionFail("No resources matched your etag precondition")
            
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
