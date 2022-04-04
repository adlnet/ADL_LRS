from django.conf import settings

def recaptcha_config(request):
    # return the value you want as a dictionnary. you may add multiple values in there.
    return {
        'use_recaptcha': settings.USE_GOOGLE_RECAPTCHA,
        'google_recaptcha_site_key': settings.GOOGLE_RECAPTCHA_SITE_KEY
    }