from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.db.models import get_app, get_models
from lrs import models

class Command(BaseCommand):

	help = 'Clears all data in the LRS app (does not clear users)'

	def handle(self, *args, **options):
		app = get_app('lrs')
		for model in get_models(app):
			model.objects.all().delete()

		cache.clear()

		self.stdout.write("Successfully cleared all data from the LRS\n")

