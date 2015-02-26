from django.conf import settings
from django.conf.urls import patterns, include, url
from django.views.generic import RedirectView

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
	url(r'^$', RedirectView.as_view(url='/xAPI/')),
    url(r'^XAPI/', include('lrs.urls')),
    url(r'^xapi/', include('lrs.urls')),
    url(r'^xAPI/', include('lrs.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
)

urlpatterns += patterns('',
  url(r'^accounts/login/$', 'django.contrib.auth.views.login', name="login"),
  url(r'^accounts/logout/$', 'lrs.views.logout_view', name="logout"),
)

if settings.DEBUG:
  urlpatterns += patterns('',
      url(r'^media/attachment_payloads/(?P<path>.*)$', 'lrs.views.admin_attachments'),
 )