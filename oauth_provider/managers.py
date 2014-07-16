from django.db import models

# LRS CHANGE - ADDED IS_APPROVED FOR ACCESS_TOKENS BEING CREATED (SHOULD HAVE SAME VALUE AS REQUEST_TOKEN
# WHICH AT THIS POINT WILL BE TRUE)
class TokenManager(models.Manager):
    def create_token(self, consumer, token_type, timestamp, scope,
            is_approved=False, user=None, callback=None, callback_confirmed=False):
        """Shortcut to create a token with random key/secret."""
        token, created = self.get_or_create(consumer=consumer, 
                                            token_type=token_type, 
                                            timestamp=timestamp,
                                            scope=scope,
                                            is_approved=is_approved,
                                            user=user,
                                            callback=callback,
                                            callback_confirmed=callback_confirmed)
        if created:
            token.generate_random_codes()
        return token