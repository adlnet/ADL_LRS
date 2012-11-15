from django.db import models


class TokenManager(models.Manager):
    def create_token(self, consumer, token_type, timestamp, resource, 
            user=None, callback=None, callback_confirmed=False):
        """Shortcut to create a token with random key/secret."""
        token, created = self.get_or_create(consumer=consumer, 
                                            token_type=token_type, 
                                            timestamp=timestamp,
                                            resource=resource,
                                            user=user,
                                            callback=callback,
                                            callback_confirmed=callback_confirmed)
        if created:
            token.generate_random_codes()
        return token
