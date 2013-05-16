from django.contrib import admin
from lrs.models import Consumer, Token, Nonce

# lou w - removed any references to Resource

class ConsumerAdmin(admin.ModelAdmin):
	pass

class TokenAdmin(admin.ModelAdmin):
	pass

class NonceAdmin(admin.ModelAdmin):
	pass
	
admin.site.register(Consumer, ConsumerAdmin)
admin.site.register(Token, TokenAdmin)
admin.site.register(Nonce, NonceAdmin)