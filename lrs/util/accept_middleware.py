from string import lower

def webkit_workaround(bestq, result):
    """The next part is a workaround, to avoid the problem, webkit browsers
    generate, by putting application/xml as the first item in theire 
    accept headers
    
    The algorithm changes the order of the best quality fields, if xml appears
    to be the first entry of best quality and eigther an xhtml or html emtry is,
    found with also best quality, to xml beeing the last entry of best quality.
    
    If only an xhtml entry is found in bestq, but the request contains an html
    entry with lower rating, it rearranges the html entry to be directly
    in front of xml.
    """
    if result[0][0] == "application/xml":
        bestresult = []
        length = 0
        hashtml = False
        hasxhtml = False
        idxhtml = None
        
        i = 0
        for mediatype in result:
            if mediatype[2] == bestq:
                bestresult.append(mediatype)
                length = length + 1
                if not hasxhtml and lower(mediatype[0]) == "application/xhtml+xml":
                    hasxhtml = True
                if not hashtml and lower(mediatype[0]) == "text/html":
                    hashtml = True
            if lower(mediatype[0]) == "text/html":
                idxhtml = i
            i = i+1
        
        if (hashtml or hasxhtml) and length > 1:
                
            newresult = []
            newresult.extend(bestresult[1:])
            
            if not hashtml and idxhtml:
                htmltype = result.pop(idxhtml)
                htmltype = (htmltype[0], htmltype[1], bestq)
                newresult.append(htmltype)
            
            newresult.append(bestresult[0])
            newresult.extend(result[length:])
            
            result = newresult
    return result

def parse_accept_header(accept):
    """Parse the Accept header *accept*, returning a list with pairs of
    (media_type, q_value), ordered by q values.
    """
    bestq = 0.0
    result = []
    for media_range in accept.split(","):
        parts = media_range.split(";")
        media_type = parts.pop(0)
        media_params = []
        q = 1.0
        for part in parts:
            (key, value) = part.lstrip().split("=", 1)
            if key == "q":
                q = float(value)
            else:
                media_params.append((key, value))
        
        if q > bestq:
            bestq = q
        result.append((media_type, tuple(media_params), q))
    result.sort(lambda x, y: -cmp(x[2], y[2]))
    
    result = webkit_workaround(bestq, result)
    
    return result

class AcceptMiddleware(object):
    def process_request(self, request):
        accept = parse_accept_header(request.META.get("HTTP_ACCEPT", ""))
        request.accept = accept
        request.accepted_types = map(lambda (t, p, q): t, accept)
        