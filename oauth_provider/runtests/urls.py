from django.http import HttpResponse
from oauth_provider.compat import url, patterns, include
from oauth_provider.decorators import oauth_required
from oauth_provider.views import protected_resource_example

@oauth_required("some")
def resource_some_scope_view(request):
    return HttpResponse()


@oauth_required
def resource_None_scope_view(request):
    return HttpResponse()


urlpatterns = patterns('',
    url(r'^oauth/', include('oauth_provider.urls')),
    url(r'^oauth/photo/$', protected_resource_example, name='oauth_example'),
    url(r'^oauth/some/$', resource_some_scope_view, name='oauth_resource_some_scope'),
    url(r'^oauth/none/$', resource_None_scope_view, name='oauth_resource_None_scope'),
)
