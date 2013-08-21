from django.contrib import admin
from lrs import models
from lrs.util import autoregister

class AgentProfileAdmin(admin.ModelAdmin):
    model = models.AgentProfile
    readonly_fields = ('profileId','updated','etag')

autoregister('lrs')