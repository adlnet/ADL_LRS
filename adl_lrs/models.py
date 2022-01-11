import uuid

from django.db import models
from django.contrib.auth.models import User
# from django.contrib.postgres.fields import JSONField
from django.db.models import JSONField
from django.utils import timezone


class Hook(models.Model):
    hook_id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, db_index=True, editable=False)
    name = models.CharField(max_length=50, blank=False)
    config = JSONField(blank=False)
    filters = JSONField(blank=False)
    user = models.ForeignKey(User, null=False, on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = (("name", "user"))

    def save(self, *args, **kwargs):
        if 'endpoint' not in self.config:
            raise ValueError('Hook does not contain an endpoint')

        if 'content_type' not in self.config:
            self.config['content_type'] = 'json'
        else:
            if self.config['content_type'] != 'form' and self.config['content_type'] != 'json':
                self.config['content_type'] = 'json'

        if self.filters == {}:
            raise ValueError('Hook does not have any filters')
        super(Hook, self).save(*args, **kwargs)

    def to_dict(self):
        return {'id': self.hook_id, 'name': self.name, 'config': self.config, 'filters': self.filters,
                'created_at': self.created_at.isoformat(), 'updated_at': self.updated_at.isoformat()}
