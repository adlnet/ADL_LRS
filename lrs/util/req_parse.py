import json
from lrs.util import etag

import pprint

def parse(request):
    r_dict = {}
    r_dict.update(request.GET.dict())
    r_dict['user'] = request.user
    r_dict['method'] = request.method

    # is this the IE cors POST thing?
    if request.GET and 'method' in r_dict:
        r_dict.update(request.POST.dict())
        if 'content' in r_dict: # body is in 'content' for the IE cors POST
            r_dict['body'] = json.loads(r_dict.pop('content').replace("'", "\""))  
    else:
        r_dict = parse_body(r_dict, request)
    
    r_dict = get_headers(request.META, r_dict)
    if request.raw_post_data and request.raw_post_data != '':
        r_dict['raw_post_data'] = request.raw_post_data    
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
                body = request.body
                jsn = body.replace("'", "\"")
                try:
                    r['body'] = json.loads(jsn)
                except:
                    pass
    return r

def get_headers(headers, r):
    # updated 
    if 'HTTP_UPDATED' in headers:
        r['updated'] = headers['HTTP_UPDATED']
    else:
        r['updated'] = headers.get('updated', None)

    r['CONTENT_TYPE'] = headers.get('CONTENT_TYPE', '')

    r['ETAG'] = etag.get_etag_info(headers, required=False)
    if 'HTTP_AUTHORIZATION' in headers:
        r['Authorization'] = headers['HTTP_AUTHORIZATION']
    if 'Authorization' in headers:
        r['Authorization'] = headers['Authorization']
    return r