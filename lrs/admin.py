from django.apps import apps
from django.conf import settings
from django.contrib import admin
from django.contrib.admin.sites import AlreadyRegistered

# Registers all models for admin
for appname in settings.ADMIN_REGISTER_APPS:
	myapp = apps.get_app_config(appname)
	for model in myapp.get_models():
		try:
			admin.site.register(model)
		except AlreadyRegistered:
			pass