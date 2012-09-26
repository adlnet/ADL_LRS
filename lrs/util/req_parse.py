from lrs.util import etag

def parse(request):
    if request.GET and 'method' in request.GET:
        return parse_cors_post(request)
    r_dict = {}
    r_dict['method'] = request.method
    if request.GET:
        r_dict.update(request.GET.dict())
    if request.method == 'POST' or request.method == 'PUT':
        if 'multipart/form-data' in request.META['CONTENT_TYPE']:
            r_dict.update(request.POST.dict())
            parser = MultiPartParser(request.META, StringIO.StringIO(request.raw_post_data),request.upload_handlers)
            post, files = parser.parse()
            r_dict['files'] = files
        else:
            if request.body:
                body = request.body
                jsn = body.replace("'", "\"")
                r_dict['body'] = json.loads(jsn)
    r_dict = get_headers(request.META, r_dict)
    if request.raw_post_data and request.raw_post_data != '':
        r_dict['raw_post_data'] = request.raw_post_data    
    return r_dict{}

def get_headers(headers, r):
    # updated 
    if 'HTTP_UPDATED' in headers:
        r['updated'] = headers['HTTP_UPDATED']
    else:
        r['updated'] = headers.get('update', None)

    r['CONTENT_TYPE'] = headers.get('CONTENT_TYPE', '')

    r['ETAG'] = etag.get_etag_info(headers, required=False)
    return r