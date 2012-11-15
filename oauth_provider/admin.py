from django.contrib import admin

from oauth_provider.models import Resource, Consumer, Token

class ResourceAdmin(admin.ModelAdmin):
	pass
	
class ConsumerAdmin(admin.ModelAdmin):
	raw_id_fields = ['user',]

class TokenAdmin(admin.ModelAdmin):
	raw_id_fields = ['user', 'consumer', 'resource']
	

admin.site.register(Resource, ResourceAdmin)
admin.site.register(Consumer, ConsumerAdmin)
admin.site.register(Token, TokenAdmin)