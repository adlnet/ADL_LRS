from django.conf.urls import patterns, include, url
from django.views.generic import RedirectView

urlpatterns = patterns('lrs.views',
    url(r'^$', RedirectView.as_view(url='/')),
    url(r'^statements/more/(?P<more_id>.{32})$', 'statements_more'),
    url(r'^statements/more', 'statements_more_placeholder'),
    url(r'^statements', 'statements'),
    url(r'^activities/state', 'activity_state'),
    url(r'^activities/profile', 'activity_profile'),
    url(r'^activities', 'activities'),
    url(r'^agents/profile', 'agent_profile'),
    url(r'^agents', 'agents'),
    url(r'^about', 'about'),
    url(r'^OAuth/', include('oauth_provider.urls', namespace='oauth')),
)