import json
from lrs.util import etag
from django.http import MultiPartParser
import ast
import StringIO

import pprint

def parse(request):

    r_dict = {}
    r_dict['user'] = request.user

    if request.method == 'POST' and 'method' in request.GET:
        bdy = ast.literal_eval(request.body)
        r_dict.update(bdy)
        if 'content' in r_dict: # body is in 'content' for the IE cors POST
            r_dict['body'] = r_dict.pop('content')
    else:
        r_dict = parse_body(r_dict, request)

    r_dict = get_headers(request.META, r_dict)
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
                r['body'] = request.body
                # try:
                #     r['body'] = ast.literal_eval(request.body)
                # except:
                #     r['body'] = json.loads(request.body)
            if request.raw_post_data:
                r['raw_post_data'] = request.raw_post_data
                # try:
                #     r['raw_post_data'] = ast.literal_eval(request.raw_post_data)
                # except:
                #     r['raw_post_data'] = json.loads(request.raw_post_data)
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