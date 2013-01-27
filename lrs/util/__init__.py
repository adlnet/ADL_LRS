from django.contrib.auth.models import User

def get_user_from_auth(auth):
    if auth.email:
        return auth #it is a User already
    else:
        # it's a group.. gotta find out which of the 2 members is the client
        try:
            cname = auth.members.all()[0].agent_account.name
        except:
            cname = auth.members.all()[1].agent_account.name
        user = models.Consumer.objects.get(name__exact=cname).user
    return user