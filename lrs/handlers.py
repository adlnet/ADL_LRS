import logging
from datetime import datetime
from django.utils.timezone import utc

class DBLogHandler(logging.Handler):
	def __init__(self):
		logging.Handler.__init__(self)

	def emit(self, record):
		try:
			from models import UserSystemAction
			time = datetime.utcnow().replace(tzinfo=utc).isoformat()
			log_action = UserSystemAction(level=record.levelname, action=record.msg,timestamp=time)
			log_action.save()
		except Exception, e:
			raise e
		return