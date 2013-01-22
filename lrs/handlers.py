import logging
from datetime import datetime
from django.utils.timezone import utc
import pdb

class DBLogHandler(logging.Handler):
	def __init__(self):
		logging.Handler.__init__(self)

	def emit(self, record, **kwargs):
		try:
			# pdb.set_trace()
			# Import in func as work around for ciruclar dependency - try to move out of app again
			from models import SystemAction

			time = datetime.utcnow().replace(tzinfo=utc).isoformat()
			parent_action = SystemAction.objects.get(id=record.msg['parent_id'])
			
			# TODO: MORE EFFICIENT WAY OF DOING THIS
			if record.msg['user']:
				log_action = SystemAction(level=record.levelname, message=record.msg['message'], timestamp=time,
					content_object=record.msg['user'], parent_action=parent_action)
			else:
				log_action = SystemAction(level=record.levelname, message=record.msg['message'], timestamp=time,
					parent_action=parent_action)

			log_action.save()
		except Exception, e:
			raise e
		return 