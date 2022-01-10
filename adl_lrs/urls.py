from django.conf.urls import include, url
from django.contrib.auth import views as auth_views

from . import views

# Uncomment the next two lines to enable the admin (imports admin module
# in each app):
from django.contrib import admin
admin.autodiscover()

urlpatterns = [
    # xapi endpoints
    url(r'^XAPI/', include(('lrs.urls', 'lrs'), namespace='lrs')),
    url(r'^xapi/', include(('lrs.urls', 'lrs'), namespace='lrs')),
    url(r'^xAPI/', include(('lrs.urls', 'lrs'), namespace='lrs')),

    # home endpoint
    url(r'^$', views.home, name="home"),

    # admin endpoint
    url(r'^admin/', admin.site.urls),

    # login and logout endpoints
    url(r'^accounts/login/$', auth_views.LoginView.as_view(), name="login"),
    url(r'^accounts/logout/$', auth_views.LogoutView.as_view(), name="logout"),

    # non xapi endpoints
    url(r'^hooks/(?P<hook_id>.{36})$', views.hook, name='hook'),
    url(r'^hooks$', views.hooks, name='hooks'),

    url(r'^me/activities/states$', views.my_activity_states,
        name='my_activity_states'),
    url(r'^me/activities/state$', views.my_activity_state, name='my_activity_state'),
    url(r'^me/apps$', views.my_app_status, name='my_app_status'),
    url(r'^me/download/statements$', views.my_download_statements,
        name='my_download_statements'),
    url(r'^me/hooks$', views.my_hooks, name='my_hooks'), 
    url(r'^me/statements$', views.my_statements, name='my_statements'),
    url(r'^me/tokens$', views.delete_token, name='delete_token'),
    url(r'^me$', views.me, name='me'),

    url(r'^regclient$', views.regclient, name='regclient'),
    url(r'^register$', views.register, name='register'),

    url(r'^reset/password_reset/$', auth_views.PasswordResetView.as_view(), name='reset_password_reset'),
    url(r'^reset/password_reset/done/$', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    url(r'^reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    url(r'^reset/done/$', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),

    url(r'^statementvalidator$', views.stmt_validator, name='stmt_validator'),
]
