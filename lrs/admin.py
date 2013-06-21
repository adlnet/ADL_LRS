from django.contrib import admin
from lrs import models
from lrs.util import autoregister

class Result_ExtensionsAdmin(admin.StackedInline):
    model = models.Extensions

class ResultAdmin(admin.ModelAdmin):
    inlines = [
        Result_ExtensionsAdmin,
    ]

class AgentProfileAdmin(admin.ModelAdmin):
    model = models.AgentProfile
    readonly_fields = ('profileId','updated','etag')

autoregister('lrs')