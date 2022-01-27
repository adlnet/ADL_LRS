from django.contrib import admin

# from models import Scope, Consumer, Token
from .models import Consumer, Token

# LRS CHANGE - REMOVED SCOPE REFERENCES
# class ScopeAdmin(admin.ModelAdmin):
#     pass


class ConsumerAdmin(admin.ModelAdmin):
    raw_id_fields = ['user']


class TokenAdmin(admin.ModelAdmin):
    raw_id_fields = ['user', 'consumer']

# LRS CHANGE - THESE GET REGISTERED IN LRS APP
# admin.site.register(Scope, ScopeAdmin)
# admin.site.register(Consumer, ConsumerAdmin)
# admin.site.register(Token, TokenAdmin)
