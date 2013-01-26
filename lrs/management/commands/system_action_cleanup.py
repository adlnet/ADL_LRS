from django.core.management.base import NoArgsCommand, CommandError
from lrs.models import SystemAction
from django.conf import settings
from django.utils.timezone import utc
from datetime import date, timedelta, datetime
import pytz

def convert_to_utc(timestr):
    # Strip off TZ info
    timestr = timestr[:timestr.rfind('+')]
    
    # Convert to date_object (directive for parsing TZ out is buggy, which is why we do it this way)
    date_object = datetime.strptime(timestr, '%Y-%m-%dT%H:%M:%S.%f')
    
    # Localize TZ to UTC since everything is being stored in DB as UTC
    date_object = pytz.timezone("UTC").localize(date_object)
    return date_object

class Command(NoArgsCommand):
    args = 'None'
    help = 'Performs removal of old system actions.'

    def handle_noargs(self, *args, **options):
        # delete SystemActions older than 7 days
        cutoff_time = convert_to_utc(str((datetime.utcnow() - timedelta(seconds=7)).replace(tzinfo=utc).isoformat()))
        # cutoff_time = convert_to_utc(str((datetime.utcnow() - timedelta(days=7)).replace(tzinfo=utc).isoformat()))
        system_actions = SystemAction.objects.filter(timestamp__lt=cutoff_time)
        system_actions.delete()
        self.stdout.write('Successfully deleted stale SystemActions\n')
        return