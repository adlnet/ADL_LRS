from django.conf.urls import patterns, include, url

urlpatterns = patterns('lrs.views',
    url(r'^$', 'home'),
    url(r'^statements/more/(?P<more_id>.{32})$', 'statements_more'),
    url(r'^statements', 'statements'),
    url(r'^activities/state', 'activity_state'),
    url(r'^activities/profile', 'activity_profile'),
    url(r'^activities', 'activities'),
    url(r'^agents/profile', 'agent_profile'),
    url(r'^agents', 'agents'),
    url(r'^actexample/$', 'actexample'),
    url(r'^actexample2/$', 'actexample2'),
    url(r'^actexample3/$', 'actexample3'),
    url(r'^actexample4/$', 'actexample4'),
    url(r'^register/$', 'register'),
    url(r'^regclient/$', 'reg_client'),    
    url(r'^OAuth/', include('oauth_provider.urls')),
    # just urls for some user interface... not part of xapi
    url(r'^me/statements/', 'my_statements'),
    url(r'^me/apps/', 'my_app_status'),
    url(r'^me/tokens/', 'delete_token'),
    url(r'^me/', 'me'),
    url(r'^about', 'about')
)
urlpatterns += patterns('',
  url(r'^accounts/login/$', 'django.contrib.auth.views.login', name="login"),
  url(r'^accounts/logout/$', 'lrs.views.logout_view', name="logout"),
)
