from celery.task.control import discard_all

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Clears all queued celery tasks.'

    def handle(self, *args, **options):
        discarded = discard_all()
        self.stdout.write("Discarded %s celery tasks" % discarded)
