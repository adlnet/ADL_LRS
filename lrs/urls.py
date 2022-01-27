from django.conf.urls import include, url
from django.views.generic import RedirectView

from . import views

urlpatterns = [
    # redirect for just /xapi
    url(r'^$', RedirectView.as_view(url='/')),

    # xapi endpoints
    url(r'^statements/more/(?P<more_id>.{32})$',
        views.statements_more, name='statements_more'),
    url(r'^statements/more$', views.statements_more_placeholder,
        name='statements_more_placeholder'),
    url(r'^statements$', views.statements, name='statements'),
    url(r'^activities/state$', views.activity_state, name='activity_state'),
    url(r'^activities/profile$', views.activity_profile, name='activity_profile'),
    url(r'^activities$', views.activities, name='activities'),
    url(r'^agents/profile$', views.agent_profile, name='agent_profile'),
    url(r'^agents$', views.agents, name='agents'),
    url(r'^about$', views.about, name='about'),

    # xapi oauth endpoints
    url(r'^OAuth/', include(('oauth_provider.urls', 'oauth'), namespace='oauth')),
]
