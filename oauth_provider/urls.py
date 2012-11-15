from django.conf.urls.defaults import *

from oauth_provider.views import request_token, user_authorization, access_token

urlpatterns = patterns('',
    url(r'^initiate/$',    request_token,      name='oauth_request_token'),
    url(r'^authorize/$',        user_authorization, name='oauth_user_authorization'),
    url(r'^token/$',     access_token,       name='oauth_access_token'),
)
