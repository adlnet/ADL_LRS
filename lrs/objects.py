import json
import types
import urllib
import datetime
from lrs import models
from lrs.util import etag
from django.core.exceptions import FieldError,ValidationError
from django.core.files.base import ContentFile
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
                #but if i'm here, then it was a get request that asked for the agent
                #and we can't change the data.. no saving the merged agent or removing the others
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
    
    @default_on_exception("")
    def get_objectType(self):
        return self.agent.objectType

    @default_on_exception([])
    def get_name(self):
        return self.agent.agent_name_set.values_list('name',flat=True).order_by('-date_added')

    @default_on_exception([])
    def get_mbox(self):
        return self.agent.agent_mbox_set.values_list('mbox',flat=True).order_by('-date_added')

    @default_on_exception([])
    def get_mbox_sha1sum(self):
        return self.agent.agent_mbox_sha1sum_set.values_list('mbox_sha1sum',flat=True).order_by('-date_added')

    @default_on_exception([])
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

    def put_profile(self, request_dict):
        try:
            profile = ContentFile(request_dict['profile'].read())
        except:
            try:
                profile = ContentFile(request_dict['profile'])
            except:
                profile = ContentFile(str(request_dict['profile']))

        p,created = models.actor_profile.objects.get_or_create(profileId=request_dict['profileId'],actor=self.agent)
        if not created:
            etag.check_preconditions(request_dict,p)
        p.content_type = request_dict['CONTENT_TYPE']
        p.etag = etag.create_tag(profile.read())
        if request_dict['updated']:
            p.stored = request_dict['updated']
        profile.seek(0)
        if created:
            p.save()

        fn = "%s_%s" % (p.actor_id,request_dict.get('filename', p.id))
        p.profile.save(fn, profile)
    
    def get_profile(self, profileId):
        try:
            return self.agent.actor_profile_set.get(profileId=profileId)
        except models.actor_profile.DoesNotExist:
            raise IDNotFoundError('There is no profile associated with the id: %s' % profileId)

    def get_profile_ids(self, since=None):
        ids = []
        if since: #filter(stored__gte = since)
            try:
                profs = self.agent.actor_profile_set.filter(stored__gte=since)
            except ValidationError:
                since_i = int(float(since))
                since_dt = datetime.datetime.fromtimestamp(since_i)
                profs = self.agent.actor_profile_set.filter(stored__gte=since_dt)
            ids = [p.profileId for p in profs]
        else:
            ids = self.agent.actor_profile_set.values_list('profileId', flat=True)
        return ids

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

class Activity():
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

    #Once JSON is verified, populate the activity objects
    def __populate(self, the_object):
        #Must include activity_id, default objectType is Activity - set object's activity_id and objectType
        try:
            self.activity_id = the_object['activity_id']
        except KeyError:
            raise Exception("No activity_id provided, must provide activity_id")
        try:
            self.objectType = the_object['objectType']
        except KeyError:
            self.objectType = 'Activity'
        
        #Save activity to DB
        the_act = models.activity(activity_id=self.activity_id, objectType=self.objectType)
        the_act.save()

        '''
        ot = models.activity.objects.get(activity_id=self.activity_id).objectType
        ai = models.activity.objects.get(activity_id=self.activity_id).activity_id
        aid = models.activity.objects.get(activity_id=self.activity_id).id
        print 'act_objType ' + str(ot)
        print 'act_act_id ' + str(ai)
        print 'act_id ' + str(aid)
        '''

        #See if activity has definition included
        try:   
            the_act_def = the_object['definition']
        except KeyError:
            the_act_def = None        
        
        #If definition is included, populate the activity definition
        if the_act_def:
            self.__populate_definition(the_act, the_act_def, the_object)


    def __populate_definition(self, act, definition, the_object):
            #Initialize object's activity definition
            self.activity_definition = {}

            #Name, description, type, and interactionType are all required - extensions optional
            try:
                self.activity_definition['name'] = definition['name']
            except KeyError:
                raise Exception("No activity definition name provided, must provide name")
            try:
                self.activity_definition['description'] = definition['description']
            except KeyError:
                raise Exception("No activity definition description provided, must provide description")
            try:
                self.activity_definition['type'] = definition['type']
            except KeyError:
                raise Exception("No activity definition type provided, must provide type")
            try:
                self.activity_definition['interactionType'] = definition['interactionType']
            except KeyError:
                raise Exception("No activity definition interactionType provided, must provide interactionType")    
            try:
                self.activity_definition['extensions'] = definition['extensions']
            except KeyError:
                self.activity_definition['extensions'] = None

            #Save activity definition to DB
            the_act_def = models.activity_definition(name=self.activity_definition['name'],
                description=self.activity_definition['description'], activity_definition_type=self.activity_definition['type'],
                interactionType=self.activity_definition['interactionType'], activity=act)
            the_act_def.save()

            '''
            adn = models.activity_definition.objects.get(activity=act).name
            print 'act_def_name ' + str(adn) 
            add = models.activity_definition.objects.get(activity=act).description
            print 'act_def_desc ' + str(add)
            adt = models.activity_definition.objects.get(activity=act).activity_definition_type
            print 'act_def_type ' + str(adt)
            adi = models.activity_definition.objects.get(activity=act).interactionType
            print 'act_def_intType ' + str(adi)
            adid = models.activity_definition.objects.get(activity=act).activity
            print 'act_def_act_id ' + str(adid)        
            '''

            # If there are extensions, save each one to the DB
            if self.activity_definition['extensions']:
                for k, v in self.activity_definition['extensions'].items():
                    the_act_def_ext = models.activity_extentions(key=k, value=v,
                        activity_definition=the_act_def)
                    the_act_def_ext.save()
            '''
            ade = models.activity_extentions.objects.values_list().filter(activity_definition=the_act_def)
            print 'ade ' + str(ade)
            '''
            
class MultipleActorError(Exception):
    def __init__(self, msg):
        self.message = msg
    def __str__(self):
        return repr(self.message)

class IDNotFoundError(Exception):
    def __init__(self, msg):
        self.message = msg
    def __str__(self):
        return repr(self.message)