import json
from lrs import models
from django.core.exceptions import FieldError

class Actor():
    IFPs = ['account','mbox','openid','mbox_sha1sum']
    
    def __init__(self, initial=None):
        self.initial = initial
        self.obj = self.__parse(initial)
        if self.obj: 
            self.__validate()
            if self.ifps:
                qry = 'agent_%s__%s' % (self.ifps[0], self.ifps[0])
                args = {qry:self.obj[self.ifps[0]]}
                try:
                    self.agent = models.agent.objects.get(**args)
                except(models.agent.DoesNotExist, FieldError):
                    self.agent = models.agent()
            self.__populate()
    
    def __parse(self,initial):
        if initial:
            try:
                return json.loads(initial)
            except Exception as e:
                raise Exception("Error parsing the Actor object. Expecting json. Received: %s" % initial)
        return {}
    
    def __validate(self):
        # Inverse Functional Properties
        ifps = [k for k,v in self.obj.items() if k in Actor.IFPs]
        if not ifps:
            raise Exception("Actor object validation issue. Actor object did not contain an Inverse Functional Property. Acceptable properties are: %s" % ifp)
        self.ifps = ifps
    
    def __populate(self):
        for ifp in self.ifps:
            try:
                # get agent_
                fun = 'agent_%s_set' % ifp
                the_set = getattr(self.agent, fun)
                val = the_set.values_list(ifp, flat=True)
                if not val or ifps[ifp] not in val: # is the value list empty or doesn't have the ifp value
                    the_set.create(**json.dumps({ifp:ifps[ifp]}))
            # get agent_account__account__accountName?
            except Exception:
                pass
    
    def __unicode__(self):
        return json.dumps(self.agent)
    
    def __str__(self):
        return json.dumps(self.agent)
