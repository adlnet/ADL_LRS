from django.conf.urls import include, url
from django.contrib.auth import views as auth_views

from . import views

# Uncomment the next two lines to enable the admin (imports admin module in each app):
from django.contrib import admin
admin.autodiscover()

urlpatterns = [
    # xapi endpoints
    url(r'^XAPI/', include('lrs.urls', namespace='lrs')),
    url(r'^xapi/', include('lrs.urls', namespace='lrs')),
    url(r'^xAPI/', include('lrs.urls', namespace='lrs')),

    # admin endpoint
    url(r'^admin/', admin.site.urls),

    # login and logout endpoints
    url(r'^accounts/login/$', auth_views.login, name="login"),
    url(r'^accounts/logout/$', views.logout_view, name="logout"),

    # start of non xapi endpoints
    url(r'^$', views.home, name="home"),
    url(r'^actexample1/$', views.actexample1, name='actexample1'),
    url(r'^actexample2/$', views.actexample2, name='actexample2'), 
    url(r'^me/activities/states', views.my_activity_states, name='my_activity_states'),
    url(r'^me/activities/state', views.my_activity_state, name='my_activity_state'),
    url(r'^me/apps', views.my_app_status, name='my_app_status'),
    url(r'^me/download/statements', views.my_download_statements, name='my_download_statements'),
    url(r'^hooks/(?P<hook_id>.{36})$', views.hook, name='hook'),
    url(r'^hooks', views.hooks, name='hooks'),
    url(r'^me/hooks', views.my_hooks, name='my_hooks'),
    url(r'^me/statements', views.my_statements, name='my_statements'),
    url(r'^me/tokens', views.delete_token, name='delete_token'),
    url(r'^me', views.me, name='me'),
    url(r'^regclient', views.regclient, name='regclient'),
    url(r'^register', views.register, name='register'),  
    url(r'^statementvalidator', views.stmt_validator, name='stmt_validator'),
]