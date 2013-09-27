from django.contrib import admin
from vendor.xapi.lrs import models
from vendor.xapi.lrs.util import autoregister

class AgentProfileAdmin(admin.ModelAdmin):
    model = models.AgentProfile
    readonly_fields = ('profileId','updated','etag')

autoregister('lrs')