import json
import types
from lrs import models
from django.core.exceptions import FieldError
from django.db import transaction

class Actor():
    IFPs = ['account','mbox','openid','mbox_sha1sum']
    
    @transaction.commit_on_success
    def __init__(self, initial=None):
        self.initial = initial
        self.obj = self.__parse(initial)
        if self.obj: 
            self.agent, self.ifps = self.__get_or_create_agent(self.obj)
    
    def __parse(self,initial):
        if initial:
            try:
                return json.loads(initial)
            except Exception as e:
                raise Exception("Error parsing the Actor object. Expecting json. Received: %s" % initial)
        return {}

    def __get_or_create_agent(self,the_object):
        the_ifps = self.__validate(the_object)
        the_agent = self.__get_agent(the_object, the_ifps)
        the_agent = self.__populate(the_agent, the_object)
        the_agent.save()
        return the_agent, the_ifps

    
    def __validate(self,the_object):
        # Inverse Functional Properties
        ifps = [k for k,v in the_object.items() if k in Actor.IFPs]
        if not ifps:
            raise Exception("Actor object validation issue. Actor object did not contain an Inverse Functional Property. Acceptable properties are: %s" % ifp)
        return ifps
    
    def __get_agent(self, the_object, the_ifps):
        # i need to see if any of these ifps is already associated with an existing agent
        # if so then that agent is the agent for this actor object
        # if not, then i need to make a new agent and have __populate fill in the info
        agent = {}
        agents = []
        for ifp in the_ifps: 
            for val in the_object[ifp]: #ex. mbox: ['me@example.com', 'me@gmail.com']
                qry = 'agent_%s__%s' % (ifp, ifp) #ex. agent_mbox__mbox
                args = {qry:val} #ex. {'agent_mbox__mbox':'me@example.com'}
                try:
                    agent = models.agent.objects.get(**args)
                    agents.append(agent)
                except models.agent.DoesNotExist: # the get didn't return an agent... that's ok
                    pass
                except (ValueError, FieldError): # agent_n__n didn't work, try account
                    try:
                        qry = 'agent_account__accountName'
                        accountname = val['accountName']
                        agent = models.agent.objects.get(**{qry:accountname})
                        agents.append(agent)
                    except Exception as fail:
                        pass
        agent_set = set(agents)
        # if i found more than one agent,
        # i need to merge them
        if len(agent_set) > 1:
            agent = models.merge_model_objects(agent_set.pop(), list(agent_set))
        return agent

    
    def __populate(self, the_agent, the_object):
        try:
            objtype = the_object['objectType']
        except KeyError:
            objtype = 'Person'

        if not the_agent:
            if objtype == 'Agent':
                the_agent = models.agent(objectType='Agent')
            elif objtype == 'Group':
                the_agent = models.group(objectType='Group')
            else:
                the_agent = models.person(objectType='Person')
            the_agent.save()
        else:
            if not the_agent.objectType:
                the_agent.objectType = objtype
        
        if the_agent.objectType == 'Group':
            for member in the_object['member']:
                a = Actor(json.dumps(member))
                print dir(the_agent)
                #the_agent.group.agent_group.get_or_create(a.agent)

        for k, v in the_object.items():
            # skipping string values.. only dealing with arrays
            # this is because the only string value is objectType.. 
            # and i just set that
            if isinstance(v, types.StringTypes): continue
            for val in v:
                try:
                    # get agent_
                    fun = 'agent_%s_set' % k
                    the_set = getattr(the_agent, fun)
                    vals = the_set.values_list(k, flat=True) # gets me an array of values for the agent_n_set
                    if not vals or val not in vals: # is the value list empty or doesn't have the ifp value
                        the_set.create(**{k:val})
                except:
                    try: 
                        fun = 'person_%s_set' % k.lower()
                        the_set = getattr(the_agent.person, fun)
                        vals = the_set.values_list(k, flat=True) # gets me an array of values for the agent_n_set
                        if not vals or val not in vals: # is the value list empty or doesn't have the ifp value
                            the_set.create(**{k:val})
                    except:
                        to_create = {}
                        account_obj = val
                        if 'accountName' in val:
                            to_create['accountName'] = val['accountName']
                        if 'accountServiceHomePage' in val:
                            to_create['accountServiceHomePage'] = val['accountServiceHomePage']
                        vals = the_agent.agent_account_set.all()
                        the_agent.agent_account_set.get_or_create(**to_create)  
        return the_agent     
    
    def get_objectType(self):
        return self.agent.objectType

    def get_name(self):
        return self.agent.agent_name_set.values_list('name',flat=True).order_by('-date_added')

    def get_mbox(self):
        return self.agent.agent_mbox_set.values_list('mbox',flat=True).order_by('-date_added')

    def get_mbox_sha1sum(self):
        return self.agent.agent_mbox_sha1sum_set.values_list('mbox_sha1sum',flat=True).order_by('-date_added')

    def get_openid(self):
        return self.agent.agent_openid_set.values_list('openid',flat=True).order_by('-date_added')

    def get_account(self):
        accounts = []
        for acc in self.agent.agent_account_set.all().order_by('-date_added'):
            a = {}
            a['accountName'] = acc.accountName
            if acc.accountServiceHomePage:
                a['accountServiceHomePage'] = acc.accountServiceHomePage
            accounts.append(a)
        return accounts

    def get_givenName(self):
        return self.agent.person.person_givenname_set.values_list('givenName',flat=True).order_by('-date_added')

    def get_familyName(self):
        return self.agent.person.person_familyname_set.values_list('familyName',flat=True).order_by('-date_added')

    def get_firstName(self):
        return self.agent.person.person_firstname_set.values_list('firstName',flat=True).order_by('-date_added')

    def get_lastName(self):
        return self.agent.person.person_lastname_set.values_list('lastName',flat=True).order_by('-date_added')

    def get_member(self):
        return []#self.agent.agent_name_set.values_list('member',flat=True).order_by('-date_added')

    def original_actor_json(self):
        return json.dumps(self.obj)

    def full_actor_json(self):
        ret = {}
        ret['objectType'] = self.get_objectType()
        names = self.get_name()
        if names:
            ret['name'] = [k for k in names] # i don't like this.. it's done due to serialization issues. better solutions are welcomed
        mboxes = self.get_mbox()
        if mboxes:
            ret['mbox'] =[k for k in  mboxes]
        mbox_shas = self.get_mbox_sha1sum()
        if mbox_shas:
            ret['mbox_sha1sum'] = [k for k in mbox_shas]
        openids = self.get_openid()
        if openids:
            ret['openid'] = [k for k in openids]
        accounts = self.get_account()
        if accounts:
            ret['account'] = [k for k in accounts]

        if self.get_objectType == 'Person':
            givennames = self.get_givenName()
            if givennames:
                ret['givenName'] = [k for k in givennames]
            familynames = self.get_familyName()
            if familynames:
                ret['familyName'] = [k for k in familynames]
            firstnames = self.get_firstName()
            if firstnames:
                ret['firstName'] = [k for k in firstnames]
            lastnames = self.get_lastName()
            if lastnames:
                ret['lastName'] = [k for k in lastnames]

        if self.get_objectType == 'Group':
            members = self.get_member()
            if members:
                ret['member'] = [k for k in members]

        return json.dumps(ret, sort_keys=True)

