import oauth2 as oauth

from oauth_provider.store import InvalidConsumerError, InvalidTokenError, Store
from oauth_provider.models import Nonce, Token, Consumer, Resource, VERIFIER_SIZE


class ModelStore(Store):
    """
    Store implementation using the Django models defined in `piston.models`.
    """
    def get_consumer(self, request, oauth_request, consumer_key):
        try:
            return Consumer.objects.get(key=consumer_key)
        except Consumer.DoesNotExist:
            raise InvalidConsumerError()

    def get_consumer_for_request_token(self, request, oauth_request, request_token):
        return request_token.consumer

    def get_consumer_for_access_token(self, request, oauth_request, access_token):
        return access_token.consumer

    def create_request_token(self, request, oauth_request, consumer, callback):
        try:
            scope = oauth_request.get_parameter('scope')
        except oauth.Error:
            scope = 'all'
        try:
            resource = Resource.objects.get(name=scope)
        except Resource.DoesNotExist:
            raise oauth.Error('Resource %s does not exist.' % oauth.escape(scope))
        
        token = Token.objects.create_token(
            token_type=Token.REQUEST,
            consumer=Consumer.objects.get(key=oauth_request['oauth_consumer_key']),
            timestamp=oauth_request['oauth_timestamp'],
            resource=resource,
        )
        token.set_callback(callback)
        token.save()

        return token

    def get_request_token(self, request, oauth_request, request_token_key):
        try:
            return Token.objects.get(key=request_token_key, token_type=Token.REQUEST)
        except Token.DoesNotExist:
            raise InvalidTokenError()

    def authorize_request_token(self, request, oauth_request, request_token):
        request_token.is_approved = True
        request_token.user = request.user
        request_token.verifier = oauth.generate_verifier(VERIFIER_SIZE)
        request_token.save()
        return request_token

    def create_access_token(self, request, oauth_request, consumer, request_token):
        try:
            scope = oauth_request.get_parameter('scope')
        except oauth.Error:
            scope = 'all'
        try:
            resource = Resource.objects.get(name=scope)
        except Resource.DoesNotExist:
            raise oauth.Error('Resource %s does not exist.' % oauth.escape(scope))

        access_token = Token.objects.create_token(
            token_type=Token.ACCESS,
            timestamp=oauth_request['oauth_timestamp'],
            consumer=Consumer.objects.get(key=consumer.key),
            user=request_token.user,
            resource=resource,
        )
        request_token.delete()
        return access_token

    def get_access_token(self, request, oauth_request, consumer, access_token_key):
        try:
            return Token.objects.get(key=access_token_key, token_type=Token.ACCESS)
        except Token.DoesNotExist:
            raise InvalidTokenError()

    def get_user_for_access_token(self, request, oauth_request, access_token):
        return access_token.user

    def get_user_for_consumer(self, request, oauth_request, consumer):
        return consumer.user

    def check_nonce(self, request, oauth_request, nonce):
        nonce, created = Nonce.objects.get_or_create(
            consumer_key=oauth_request['oauth_consumer_key'],
            token_key=oauth_request.get('oauth_token', ''),
            key=nonce
        )
        return created
