from django.contrib import admin
from lrs import models

class Result_ExtensionsAdmin(admin.StackedInline):
    model = models.extensions

class ResultAdmin(admin.ModelAdmin):
    inlines = [
        Result_ExtensionsAdmin,
    ]

class AgentProfileAdmin(admin.ModelAdmin):
    model = models.agent_profile
    readonly_fields = ('profileId','updated','etag')


admin.site.register(models.LanguageMap)
admin.site.register(models.Verb)
admin.site.register(models.extensions)
admin.site.register(models.result, ResultAdmin)
admin.site.register(models.score)
admin.site.register(models.agent)
admin.site.register(models.group)
admin.site.register(models.agent_profile, AgentProfileAdmin)
admin.site.register(models.activity)
admin.site.register(models.activity_definition)
admin.site.register(models.ContextActivity)
admin.site.register(models.context)
admin.site.register(models.activity_state)
admin.site.register(models.activity_profile)
admin.site.register(models.SubStatement)
admin.site.register(models.statement)
