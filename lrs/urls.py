from django.conf.urls import patterns, include, url

urlpatterns = patterns('lrs.views',
    url(r'^$', 'home'), # just used to test
    url(r'^statements/$', 'statements'),
    url(r'^activities/state/$', 'activity_state'),
    url(r'^activities/profile/$', 'activity_profile'),
    url(r'^activities/$', 'activities'),
    url(r'^actors/profile/$', 'actor_profile'),
    url(r'^actors/$', 'actors'),
    url(r'^tcexample/$', 'tcexample'),
    url(r'^tcexample2/$', 'tcexample2'),
    url(r'^tcexample3/$', 'tcexample3'),
    url(r'^tcexample4/$', 'tcexample4'),
)
