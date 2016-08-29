from django.utils import timezone
from datetime import timedelta

class XAPIConsistentThrough(object):

    def process_request(self, request):
        return None

    def process_response(self, request, response):
        time = timezone.now() - timedelta(seconds=3)
        response['X-Experience-API-Consistent-Through'] = time.isoformat()
        return response