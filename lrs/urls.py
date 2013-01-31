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
    url(r'^tcexample/$', 'tcexample'),
    url(r'^tcexample2/$', 'tcexample2'),
    url(r'^tcexample3/$', 'tcexample3'),
    url(r'^tcexample4/$', 'tcexample4'),
    url(r'^register/$', 'register'),
    url(r'^regclient/$', 'reg_client'),
    url(r'^regsuccess/(?P<user_id>\d+)$', 'reg_success'),    
    url(r'^OAuth/', include('oauth_provider.urls')),
    # just urls for some user interface... not part of xapi
    url(r'^me/statements/', 'my_statements'),
    url(r'^me/apps/', 'my_app_status'),
    url(r'^me/log/(?P<log_id>\d+)$', 'my_log'),
    url(r'^me/', 'me'),
)
urlpatterns += patterns('',
  url(r'^accounts/login/$', 'django.contrib.auth.views.login', name="login"),
  url(r'^accounts/logout/$', 'lrs.views.logout_view', name="logout"),
)
