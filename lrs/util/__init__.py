from django.contrib.auth.models import User
from lrs.models import Consumer

def get_user_from_auth(auth):
    if not auth:
        return None
    if type(auth) ==  User:
        return auth #it is a User already
    else:
        # it's a group.. gotta find out which of the 2 members is the client
        try:
            key = auth.member.all()[0].agent_account.name
        except:
            key = auth.member.all()[1].agent_account.name
        user = Consumer.objects.get(key__exact=key).user
    return user