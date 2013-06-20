from django.contrib import admin
from lrs import models

class Result_ExtensionsAdmin(admin.StackedInline):
    model = models.Extensions

class AgentProfileAdmin(admin.ModelAdmin):
    model = models.AgentProfile
    readonly_fields = ('profileId','updated','etag')

admin.site.register(models.Verb)
admin.site.register(models.ResultExtensions)
admin.site.register(models.StatementObject)
admin.site.register(models.Agent)
admin.site.register(models.AgentProfile, AgentProfileAdmin)
admin.site.register(models.Activity)
admin.site.register(models.ActivityDefinitionNameLangMap)
admin.site.register(models.ActivityDefinitionDescLangMap)
admin.site.register(models.ActivityDefinitionExtensions)
admin.site.register(models.CorrectResponsesPatternAnswer)
admin.site.register(models.ActivityDefinitionChoiceDesc)
admin.site.register(models.ActivityDefinitionChoice)
admin.site.register(models.ActivityDefinitionScaleDesc)
admin.site.register(models.ActivityDefinitionSourceDesc)
admin.site.register(models.ActivityDefinitionSource)
admin.site.register(models.ActivityDefinitionTargetDesc)
admin.site.register(models.ActivityDefinitionTarget)
admin.site.register(models.ActivityDefinitionStepDesc)
admin.site.register(models.ActivityDefinitionStep)
admin.site.register(models.StatementRef)
admin.site.register(models.ContextExtensions)
admin.site.register(models.ContextActivity)
admin.site.register(models.Context)
admin.site.register(models.ActivityState)
admin.site.register(models.ActivityProfile)
admin.site.register(models.SubStatement)
admin.site.register(models.StatementAttachmentDisplay)
admin.site.register(models.StatementAttachmentDesc)
admin.site.register(models.StatementAttachment)
admin.site.register(models.Statement)
