from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.db.models import get_app, get_models

class Command(BaseCommand):

	help = 'Clears all data in the apps (does not clear users)'
	# TODO - FIX OAUTH2
	def handle(self, *args, **options):
		apps = []
		apps.append(get_app('lrs'))
		apps.append(get_app('oauth_provider'))
		# apps.append(get_app('oauth2_provider.provider.oauth2'))

		for app in apps:
			for model in get_models(app):
				model.objects.all().delete()

		cache.clear()
		self.stdout.write("Successfully cleared all data from the apps\n")