from django.contrib import admin

# lou w - removed any references to Resource and registering Consumer, Nonce, and Token since that is done
# in lrs/admin.py

class ConsumerAdmin(admin.ModelAdmin):
	pass

class TokenAdmin(admin.ModelAdmin):
	pass

class NonceAdmin(admin.ModelAdmin):
	pass
