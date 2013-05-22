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

admin.site.register(models.SystemAction)
admin.site.register(models.Verb)
admin.site.register(models.ResultExtensions)
admin.site.register(models.result, ResultAdmin)
admin.site.register(models.score)
admin.site.register(models.statement_object)
admin.site.register(models.agent)
admin.site.register(models.agent_account)
admin.site.register(models.agent_profile, AgentProfileAdmin)
admin.site.register(models.activity)
admin.site.register(models.name_lang)
admin.site.register(models.desc_lang)
admin.site.register(models.ActivityDefinitionExtensions)
admin.site.register(models.activity_definition)
admin.site.register(models.activity_def_correctresponsespattern)
admin.site.register(models.correctresponsespattern_answer)
admin.site.register(models.ActivityDefinitionChoiceDesc)
admin.site.register(models.activity_definition_choice)
admin.site.register(models.ActivityDefinitionScaleDesc)
admin.site.register(models.ActivityDefinitionSourceDesc)
admin.site.register(models.activity_definition_source)
admin.site.register(models.ActivityDefinitionTargetDesc)
admin.site.register(models.activity_definition_target)
admin.site.register(models.ActivityDefinitionStepDesc)
admin.site.register(models.activity_definition_step)
admin.site.register(models.StatementRef)
admin.site.register(models.ContextExtensions)
admin.site.register(models.ContextActivity)
admin.site.register(models.context)
admin.site.register(models.activity_state)
admin.site.register(models.activity_profile)
admin.site.register(models.SubStatement)
admin.site.register(models.StatementAttachmentDisplay)
admin.site.register(models.StatementAttachmentDesc)
admin.site.register(models.StatementAttachment)
admin.site.register(models.statement)
