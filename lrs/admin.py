from django.contrib import admin
from lrs import models

class Result_ExtensionsAdmin(admin.StackedInline):
    model = models.result_extensions

class ResultAdmin(admin.ModelAdmin):
    inlines = [
        Result_ExtensionsAdmin,
    ]

class Agent_Names_Admin(admin.TabularInline):
    model = models.agent_name
    extra = 0

class Agent_Mbox_Admin(admin.TabularInline):
    model = models.agent_mbox
    extra = 0
    
class Agent_Mbox_Sha1sum_Admin(admin.TabularInline):
    model = models.agent_mbox_sha1sum
    extra = 0

class Agent_Openid_Admin(admin.TabularInline):
    model = models.agent_openid
    extra = 0

class Agent_Account_Admin(admin.TabularInline):
    model = models.agent_account
    extra = 0

class AgentAdmin(admin.ModelAdmin):
    inlines = [
        Agent_Names_Admin,
        Agent_Mbox_Admin,
        Agent_Mbox_Sha1sum_Admin,
        Agent_Openid_Admin,
        Agent_Account_Admin
    ]

class Person_GivenName_Admin(admin.TabularInline):
    model = models.person_givenName
    extra = 0

class Person_FamilyName_Admin(admin.TabularInline):
    model = models.person_familyName
    extra = 0

class Person_FirstName_Admin(admin.TabularInline):
    model = models.person_firstName
    extra = 0

class Person_LastName_Admin(admin.TabularInline):
    model = models.person_lastName
    extra = 0

class PersonAdmin(AgentAdmin):
    inlines = [
        Agent_Names_Admin,
        Agent_Mbox_Admin,
        Agent_Mbox_Sha1sum_Admin,
        Agent_Openid_Admin,
        Agent_Account_Admin,
        Person_GivenName_Admin,
        Person_FamilyName_Admin,
        Person_FirstName_Admin,
        Person_LastName_Admin
    ]

class ActorProfileAdmin(admin.ModelAdmin):
    model = models.actor_profile
    readonly_fields = ('profileId','updated','etag')

admin.site.register(models.result, ResultAdmin)
admin.site.register(models.result_extensions)
admin.site.register(models.score)
admin.site.register(models.activity_state)
admin.site.register(models.statement_object)
admin.site.register(models.agent, AgentAdmin)
admin.site.register(models.agent_name)
admin.site.register(models.agent_mbox)
admin.site.register(models.agent_mbox_sha1sum)
admin.site.register(models.agent_openid)
admin.site.register(models.agent_account)
admin.site.register(models.person, PersonAdmin)
admin.site.register(models.person_givenName)
admin.site.register(models.person_familyName)
admin.site.register(models.person_firstName)
admin.site.register(models.person_lastName)
admin.site.register(models.group)
admin.site.register(models.actor_profile, ActorProfileAdmin)
admin.site.register(models.activity)
admin.site.register(models.activity_definition)
admin.site.register(models.activity_extentions)
admin.site.register(models.context)
admin.site.register(models.context_extentions)
admin.site.register(models.statement)
