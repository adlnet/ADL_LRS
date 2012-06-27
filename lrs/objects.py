import json
import types
from lrs import models
from django.core.exceptions import FieldError
from django.db import transaction
from functools import wraps

class default_on_exception(object):
    def __init__(self,default):
        self.default = default
    def __call__(self,f):
        @wraps(f)
        def closure(obj,*args,**kwargs):
            try:
                return f(obj,*args,**kwargs)
            except:
                return self.default
        return closure

class Actor():
    IFPs = ['account','mbox','openid','mbox_sha1sum']
    
    @transaction.commit_on_success
    def __init__(self, initial=None, create=False):
        self.initial = initial
        self.obj = self.__parse(initial)
        if self.obj:
            if create: 
                self.agent, self.ifps = self.__get_or_create_agent(self.obj)
            else:
                self.ifps = self.__validate(self.obj)
                self.agent = self.__get_agent(self.obj, self.ifps)
    
    def __parse(self,initial):
        if initial:
            try:
                return json.loads(initial)
            except Exception as e:
                raise Exception("Error parsing the Actor object. Expecting json. Received: %s" % initial)
        return {}

    def __get_or_create_agent(self,the_object):
        the_ifps = self.__validate(the_object)
        the_agent = self.__get_agent(the_object, the_ifps, modify=True)
        the_agent = self.__populate(the_agent, the_object)
        the_agent.save()
        return the_agent, the_ifps

    
    def __validate(self,the_object):
        # Inverse Functional Properties
        ifps = [k for k,v in the_object.items() if k in Actor.IFPs]
        if not ifps:
            raise Exception("Actor object validation issue. Actor object did not contain an Inverse Functional Property. Acceptable properties are: %s" % ifp)
        return ifps
    
    def __get_agent(self, the_object, the_ifps, modify=False):
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
            if modify:
                agent = models.merge_model_objects(agent_set.pop(), list(agent_set))
            else:
                #raise MultipleActorError("Found multiple actors for actor parameter: %s" % self.initial)
                #still need to merge
                agent = models.merge_model_objects(agent_set.pop(), list(agent_set), save=False, keep_old=True)
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
        
        #if the_agent.objectType == 'Group':
        #    for member in the_object['member']:
        #        a = Actor(json.dumps(member))
        #        print dir(the_agent)
        #        #the_agent.group.agent_group.get_or_create(a.agent)

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
        try:
            return self.agent.objectType
        except:
            return ""

    def get_name(self):
        try:
            return self.agent.agent_name_set.values_list('name',flat=True).order_by('-date_added')
        except:
            return []

    def get_mbox(self):
        try:
            return self.agent.agent_mbox_set.values_list('mbox',flat=True).order_by('-date_added')
        except:
            return []

    def get_mbox_sha1sum(self):
        try:
            return self.agent.agent_mbox_sha1sum_set.values_list('mbox_sha1sum',flat=True).order_by('-date_added')
        except:
            return []

    def get_openid(self):
        try:
            return self.agent.agent_openid_set.values_list('openid',flat=True).order_by('-date_added')
        except:
            return []

    def get_account(self):
        accounts = []
        for acc in self.agent.agent_account_set.all().order_by('-date_added'):
            a = {}
            a['accountName'] = acc.accountName
            if acc.accountServiceHomePage:
                a['accountServiceHomePage'] = acc.accountServiceHomePage
            accounts.append(a)
        return accounts
    @default_on_exception([])
    def get_givenName(self):
        return self.agent.person.person_givenname_set.values_list('givenName',flat=True).order_by('-date_added')
    @default_on_exception([])
    def get_familyName(self):
        return self.agent.person.person_familyname_set.values_list('familyName',flat=True).order_by('-date_added')
    @default_on_exception([])
    def get_firstName(self):
        return self.agent.person.person_firstname_set.values_list('firstName',flat=True).order_by('-date_added')
    @default_on_exception([])
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

        #if self.get_objectType == 'Group':
        #    members = self.get_member()
        #    if members:
        #        ret['member'] = [k for k in members]

        return json.dumps(ret, sort_keys=True)

class MultipleActorError(Exception):
    def __init__(self, msg):
        self.message = msg
    def __str__(self):
        return repr(self.message)

class Activity():

    #activity definition required fields
    ADRFs = ['name', 'description', 'type', 'interactiontype']

    #activity definition types
    ADTs = ['course', 'module', 'meeting', 'media', 'performance', 'simulation', 'assessment',
            'interaction', 'cmi.interaction', 'question', 'objective', 'link']

    @transaction.commit_on_success
    def __init__(self, initial=None):
        self.initial = initial
        self.obj = self.__parse(initial)
        self.__populate(self.obj)

    #Make sure initial data being received is JSON
    def __parse(self,initial):
        if initial:
            try:
                return json.loads(initial)
            except Exception as e:
                raise Exception("Error parsing the Activity object. Expecting json. Received: %s" % initial) 
        return {}

    #Lower all incoming keys
    def __to_lower(self,dic):
        if isinstance(dic, dict):
            return dict((k.lower(),v) for k,v in dic.iteritems())
        return dic

    #Once JSON is verified, populate the activity objects
    def __populate(self, the_object):
        #Lower keys to be sure they're not in a different case
        lower_object = self.__to_lower(the_object)
        
        #Must include activity_id, default objectType is Activity - set object's activity_id and objectType
        try:
            self.activity_id = lower_object['activity_id']
        except KeyError:
            raise Exception("No activity_id provided, must provide activity_id")
        try:
            self.objectType = lower_object['objecttype']
        except KeyError:
            self.objectType = 'Activity'

        #Set objectType to Activity if given different value (I think)
        self.objectType = 'Activity' if self.objectType != 'Activity' else 'Activity'   
        
        #Save activity to DB
        the_act = models.activity(activity_id=self.activity_id, objectType=self.objectType)
        the_act.save()

        #See if activity has definition included
        try:   
            self.activity_definition = self.__to_lower(lower_object['definition'])
        except KeyError:
            self.activity_definition = {}      
        
        #If definition is included, populate the activity definition
        if self.activity_definition:
            self.__populate_definition(the_act)


    def __populate_definition(self, act):
            #Check if all activity definition required fields are present
            for k in Activity.ADRFs:
                if k not in self.activity_definition.keys() and k != 'definition':
                    raise Exception("Activity definition error with key: %s" % k)

            #Check definition type
            if self.activity_definition['type'] not in Activity.ADTs:
                raise Exception("Activity definition type not valid")
            
            #Save activity definition to DB
            the_act_def = models.activity_definition(name=self.activity_definition['name'],
                description=self.activity_definition['description'], activity_definition_type=self.activity_definition['type'],
                interactionType=self.activity_definition['interactiontype'], activity=act)
            the_act_def.save()

            #See if activity definition has extensions
            try:   
                self.activity_definition_extensions = self.activity_definition['extensions']
            except KeyError:
                self.activity_definition_extensions = {}

            # If there are extensions, save each one to the DB
            if self.activity_definition_extensions:
                for k, v in self.activity_definition_extensions.items():
                    the_act_def_ext = models.activity_extentions(key=k, value=v,
                        activity_definition=the_act_def)
                    the_act_def_ext.save()

            

