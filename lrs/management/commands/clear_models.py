import os
from django.conf import settings
from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.db.models import get_app, get_models

class Command(BaseCommand):

	help = 'Clears all data in the apps (does not clear users), clears cache and deletes any media files'
	def handle(self, *args, **options):
		apps = []
		apps.append(get_app('lrs'))
		apps.append(get_app('oauth_provider'))
		apps.append(get_app('oauth2'))

		# Clear app(db) data
		for app in apps:
			for model in get_models(app):
				model.objects.all().delete()
				self.stdout.write("Deleted all %s objects from - %s\n" % (model.__name__, app.__name__.split('.')[0]))

		# Clear cache data
		cache.clear()

		# Clear media folders
		for subdir, dirs, files in os.walk(settings.MEDIA_ROOT):
			for dr in dirs:
				for sd, ds, fs in os.walk(os.path.join(settings.MEDIA_ROOT, dr)):
					for f in fs:
						os.remove(os.path.join(sd, f))

		self.stdout.write("Successfully cleared all data from the apps\n")