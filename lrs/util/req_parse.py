import json
from lrs.util import etag
from django.http import MultiPartParser
import ast
import StringIO
import pdb
import pprint
from django.core.urlresolvers import reverse
import lrs.views

def parse(request):
    r_dict = {}
    
    # Build headers from request in request dict
    r_dict = get_headers(request.META, r_dict)
    # pdb.set_trace()
    # Traditional authorization should be passed in headers
    if 'Authorization' in r_dict:
        # OAuth will always be dict, not http auth. Set required fields for oauth module and lrs_auth for authentication
        # module
        auth_params = r_dict['Authorization']
        if auth_params[:6] == 'OAuth ':
            r_dict['Authorization'] = str(r_dict['Authorization'])
            r_dict['absolute_uri'] = request.build_absolute_uri()
            r_dict['query_string'] = request.META.get('QUERY_STRING', '')
            r_dict['server_name'] = request.META.get('SERVER_NAME', '')
            r_dict['lrs_auth'] = 'oauth'
        else:
            r_dict['lrs_auth'] = 'http'
    elif 'Authorization' in request.body or 'HTTP_AUTHORIZATION' in request.body:
        # Authorization could be passed into body if cross origin request
        r_dict['lrs_auth'] = 'http'
    else:
        r_dict['lrs_auth'] = 'none'

    if request.method == 'POST' and 'method' in request.GET:
        bdy = ast.literal_eval(request.body)
        r_dict.update(bdy)
        if 'content' in r_dict: # body is in 'content' for the IE cors POST
            r_dict['body'] = r_dict.pop('content')
    else:
        r_dict = parse_body(r_dict, request)

    r_dict.update(request.GET.dict())

    if 'method' not in r_dict:
        r_dict['method'] = request.method
    return r_dict

def parse_body(r, request):
    if request.method == 'POST' or request.method == 'PUT':
        if 'multipart/form-data' in request.META['CONTENT_TYPE']:
            r.update(request.POST.dict())
            parser = MultiPartParser(request.META, StringIO.StringIO(request.raw_post_data),request.upload_handlers)
            post, files = parser.parse()
            r['files'] = files
        else:
            if request.body:
                # profile uses the request body
                r['raw_body'] = request.body
                try:
                    r['body'] = json.loads(request.body)
                except Exception, e:
                    r['body'] = ast.literal_eval(request.body)
            else:
                raise Exception("No body in request")
    return r

def get_headers(headers, r):
    if 'HTTP_UPDATED' in headers:
        r['updated'] = headers['HTTP_UPDATED']
    else:
        r['updated'] = headers.get('updated', None)

    r['CONTENT_TYPE'] = headers.get('CONTENT_TYPE', '')

    r['ETAG'] = etag.get_etag_info(headers, r, required=False)
    if 'HTTP_AUTHORIZATION' in headers:
        r['Authorization'] = headers['HTTP_AUTHORIZATION']
    if 'Authorization' in headers:
        r['Authorization'] = headers['Authorization']
    if 'Accept_Language' in headers:
        r['language'] = headers['Accept_Language']    
    return r
