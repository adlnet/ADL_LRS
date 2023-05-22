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

    # There are additional checks for PUT
    was_put_request = request['method'] == "PUT"

    if was_put_request and record_already_exists and missing_if_match and missing_if_none_match:
        error_message = f"A document matching your query already exists, but the request did not include ETag headers. " \
            + f"If you would like to override the document, provide the following header:: " \
            + f"If-Match: \"{record['etag']}\""
        
        raise Conflict(error_message)
    
    # Check against the If-None-Match condition.
    #
    # We should only perform this check if the request has provided a header
    # here and if the record itself already exists.  
    # 
    # If the record doesn't exist, then there's no match and this check is satisfied etc.
    if has_if_none_match and record_already_exists:

        # Only check if the content already exists. if it did not
        # already exist it should pass.
        wildcard_provided = etag_headers[IF_NONE_MATCH] == "*"
        if wildcard_provided:
            raise EtagPreconditionFail("Resource detected")
        
        else:
            if f'"{record.etag}"' in etag_headers[IF_NONE_MATCH]:
                raise EtagPreconditionFail("Resource detected")
    
    # Check against the If-Match condition.
    #
    # It's unlikely that this will be checked along with the If-None-Match condition,
    # but we should still honor that weird use case.
    if has_if_match:

        # We only created a record if the provided query didn't match anything 
        if created:
            record.delete()
            raise EtagPreconditionFail("Resource does not exist")

        wildcard_provided = etag_headers[IF_MATCH] == "*"
        matched_inclusively = f'"{record.etag}"' in etag_headers[IF_MATCH]

        etag_header_matches_record = matched_inclusively or wildcard_provided

        if not etag_header_matches_record:    
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
