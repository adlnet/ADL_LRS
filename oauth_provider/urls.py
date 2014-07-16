from oauth_provider.compat import url, patterns, include

from views import request_token, user_authorization, access_token

# LRS CHANGE - ADDED SPEC COMPLIANT ENDPOINTS
urlpatterns = patterns('',
    url(r'^initiate',    request_token,      name='oauth_request_token'),
    url(r'^authorize',        user_authorization, name='oauth_user_authorization'),
    url(r'^token',     access_token,       name='oauth_access_token'),
)
# urlpatterns = patterns('',
#     url(r'^request_token/$',    request_token,      name='oauth_request_token'),
#     url(r'^authorize/$',        user_authorization, name='oauth_user_authorization'),
#     url(r'^access_token/$',     access_token,       name='oauth_access_token'),
# )