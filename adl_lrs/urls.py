from django.conf import settings
from django.conf.urls import patterns, include, url

# Uncomment the next two lines to enable the admin (imports admin module in each app):
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('adl_lrs.views',
    # for anyone trying to hit the xapi endpoints
    url(r'^XAPI/', include('lrs.urls')),
    url(r'^xapi/', include('lrs.urls')),
    url(r'^xAPI/', include('lrs.urls')),

    # start of non xapi endpoints
    # comment the next line to disable the admin:
    url(r'^admin/', include(admin.site.urls)),
    url(r'^actexample1/$', 'actexample1'),
    url(r'^actexample2/$', 'actexample2'),
    url(r'^oauth2/', include('oauth2_provider.provider.oauth2.urls', namespace='oauth2')),    
    url(r'^$', 'home'),
    url(r'^hooks/(?P<hook_id>.{36})$', 'hook'),
    url(r'^hooks', 'hooks'),
    url(r'^register', 'register'),
    url(r'^regclient2', 'reg_client2'),    
    url(r'^regclient', 'reg_client'),
    url(r'^me/hooks', 'my_hooks'),
    url(r'^me/statements', 'my_statements'),
    url(r'^me/download/statements', 'my_download_statements'),
    url(r'^me/activities/states', 'my_activity_states'),
    url(r'^me/activities/state', 'my_activity_state'),
    url(r'^me/apps', 'my_app_status'),
    url(r'^me/tokens2', 'delete_token2'),
    url(r'^me/tokens', 'delete_token'),
    url(r'^me/clients', 'delete_client'),
    url(r'^me', 'me'),
    url(r'^statementvalidator', 'stmt_validator'),
)

# Login and logout patterns
urlpatterns += patterns('',
  url(r'^accounts/login/$', 'django.contrib.auth.views.login', name="login"),
  url(r'^accounts/logout/$', 'adl_lrs.views.logout_view', name="logout"),
)

# Allows admins to view attachments in admin console
if settings.DEBUG:
  urlpatterns += patterns('adl_lrs.views',
      url(r'^media/attachment_payloads/(?P<path>.*)$', 'admin_attachments'),
 )