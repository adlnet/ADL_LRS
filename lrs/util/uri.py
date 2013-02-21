import re

'''
scheme    = $2
authority = $4
path      = $5
query     = $7
fragment  = $9
'''
SCHEME = 2
EMAIL = 5
uri_re = re.compile('^(([^:/?#]+):)?(//([^/?#]*))?([^?#]*)(\?([^#]*))?(#(.*))?')

def validate_uri(s):
	return uri_re.match(s).group(SCHEME) != None

def validate_email(s):
	res = uri_re.match(s)
	return res.group(SCHEME) != None and res.group(EMAIL) != None