from django.core.management.base import NoArgsCommand, CommandError
from lrs.models import SystemAction
from lrs.util import convert_to_utc
from django.conf import settings
from django.utils.timezone import utc
from datetime import date, timedelta, datetime


class Command(NoArgsCommand):
    args = 'None'
    help = 'Performs removal of old system actions.'

    def handle_noargs(self, *args, **options):
        # delete SystemActions older than DAYS_TO_LOG_DELETE days
        cutoff_time = convert_to_utc(str((datetime.utcnow() - timedelta(days=settings.DAYS_TO_LOG_DELETE)).replace(tzinfo=utc).isoformat()))

        system_actions = SystemAction.objects.filter(timestamp__lt=cutoff_time)
        system_actions.delete()
        self.stdout.write('Successfully deleted stale SystemActions\n')
        return