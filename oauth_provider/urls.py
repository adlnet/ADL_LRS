from django.conf.urls.defaults import *

from views import request_token, user_authorization, access_token, oauth_home, protected_resource_example

urlpatterns = patterns('',
	url(r'^$', oauth_home, name='oauth_home'),
    url(r'^request_token/$',    request_token,      name='oauth_request_token'),
    url(r'^authorize/$',        user_authorization, name='oauth_user_authorization'),
    url(r'^access_token/$',     access_token,       name='oauth_access_token'),
    url(r'^photo/$', protected_resource_example, name='oauth_protected_resource_example')
)
