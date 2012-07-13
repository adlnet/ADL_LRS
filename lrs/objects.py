import json
import types
import urllib
import datetime
from lrs import models
from lrs.util import etag
from django.core.exceptions import FieldError,ValidationError
from django.core.files.base import ContentFile
from django.core.validators import URLValidator
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

    def delete_profile(self, profileId):
        try:
            prof = self.get_profile(profileId)
            prof.delete()
        except models.actor_profile.DoesNotExist:
            pass #we don't want it anyway
        except IDNotFoundError:
            pass


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

class IDNotFoundError(Exception):
    def __init__(self, msg):
        self.message = msg
    def __str__(self):
        return repr(self.message)
        
class Activity():

    #activity definition required fields
    ADRFs = ['name', 'description', 'type', 'interactionType']

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

    def __save_actvity_to_db(self, act_id, objType):
        #Save activity to DB
        act = models.activity(activity_id=act_id, objectType=objType)
        act.save()
        return act

    def __save_activity_definition_to_db(self, act, name, desc, act_def_type, intType):
        #Save activity definition to DB
        act_def = models.activity_definition(name=name,description=desc, activity_definition_type=act_def_type,
                  interactionType=intType, activity=act)
        act_def.save()
        return act_def    

    #Once JSON is verified, populate the activity objects
    def __populate(self, the_object):
        #Must include activity_id - set object's activity_id
        try:
            activity_id = the_object['id']
        except KeyError:
            raise Exception("No id provided, must provide 'id' field")
        
        #Verify the given activity_id exists
        validator = URLValidator(verify_exists=True)
        try:
            validator(activity_id)
        except ValidationError, e:
            raise e

        #Set objectType to nothing
        objectType = None

        #ObjectType should always be Activity when present
        if 'objectType' in the_object.keys():
            objectType = 'Activity'

        #Instantiate activity definition
        activity_definition = {}

        #See if activity has definition included
        if 'definition' in the_object.keys():
            activity_definition = the_object['definition']
            self.__populate_definition(activity_definition, activity_id, objectType)
        else:
            self.activity = self.__save_actvity_to_db(activity_id, objectType)    

    def __populate_definition(self, act_def, act_id, objType):
            #Needed for cmi.interaction args
            interactionType_args = {}
            interactionFlag = ""

            #Check if all activity definition required fields are present - delete existing activity model
            #if error with required activity definition fields
            for k in Activity.ADRFs:
                if k not in act_def.keys() and k != 'extensions':
                    raise Exception("Activity definition error with key: %s" % k)

            #Check definition type
            if act_def['type'] not in Activity.ADTs:
                raise Exception("Activity definition type not valid")

            #If the type is cmi.interaction, have to check interactionType
            if act_def['type'] == 'cmi.interaction':

                scormInteractionTypes = ['true-false', 'multiple-choice', 'fill-in', 'long-fill-in',
                                         'matching', 'performance', 'sequencing', 'likert', 'numeric',
                                         'other']
            
                #Check if valid SCORM interactionType
                if act_def['interactionType'] not in scormInteractionTypes:
                    raise Exception("Activity definition interactionType not valid")

                #Must have correctResponsesPattern if they have a valid interactionType
                try:
                    act_def['correctResponsesPattern']  
                except KeyError:    
                    raise Exception("Activity definition missing correctResponsesPattern")    

                #Multiple choice and sequencing must have choices
                if act_def['interactionType'] == 'multiple-choice' or \
                    act_def['interactionType'] == 'sequencing':
                        try:
                            act_def['choices']
                        except KeyError:
                            raise Exception("Activity definition missing choices")
                        interactionFlag = 'choices' 

                #Matching must have both source and target
                if act_def['interactionType'] == 'matching':
                    try:
                        act_def['source']
                        act_def['target']
                    except KeyError:
                        raise Exception("Activity definition missing source/target for matching")
                    interactionFlag = 'source'

                #Performance must have steps
                if act_def['interactionType'] == 'performance':
                    try:
                        act_def['steps']
                    except KeyError:
                        raise Exception("Activity definition missing steps for performance")    
                    interactionFlag = 'steps'

                #Likert must have scale
                if act_def['interactionType'] == 'likert':
                    try:
                        act_def['scale']
                    except KeyError:
                        raise Exception("Activity definition missing scale for likert")
                    interactionFlag = 'scale'

                #Set correctResponsesPatten arg after setting the arg flag
                interactionType_args['crp'] = act_def['correctResponsesPattern']

            #Save activity to DB
            self.activity = self.__save_actvity_to_db(act_id, objType)

            #Save activity definition to DB
            self.activity_definition = self.__save_activity_definition_to_db(self.activity, act_def['name'],
                        act_def['description'], act_def['type'], act_def['interactionType'])
    
            #If there are args then save individually
            if interactionType_args:
                crp = models.activity_def_correctresponsespattern(activity_definition=self.activity_definition)
                crp.save()
                self.correctResponsesPattern = crp
                
                self.answers = []
                for i in act_def['correctResponsesPattern']:
                    answer = models.correctresponsespattern_answer(answer=i, correctresponsespattern=self.correctResponsesPattern)
                    answer.save()
                    self.answers.append(answer)
    
                if interactionFlag == 'choices' or interactionFlag == 'sequencing':
                    self.choices = []
                    for c in act_def['choices']:
                        #Save description as string, not a dictionary
                        desc = json.dumps(c['description'])
                        choice = models.activity_definition_choice(choice_id=c['id'], description=desc,
                            activity_definition=self.activity_definition)
                        choice.save() 
                        self.choices.append(choice)
                
                elif interactionFlag == 'scale':
                    self.scale_choices = []
                    for s in act_def['scale']:
                        #Save description as string, not a dictionary
                        desc = json.dumps(s['description'])
                        scale = models.activity_definition_scale(scale_id=s['id'], description=desc,
                            activity_definition=self.activity_definition)        
                        scale.save()
                        self.scale_choices.append(scale)

                elif interactionFlag == 'steps':
                    self.steps = []
                    for s in act_def['steps']:
                        #Save description as string, not a dictionary
                        desc = json.dumps(s['description'])
                        step = models.activity_definition_step(step_id=s['id'], description=desc,
                            activity_definition=self.activity_definition)
                        step.save()
                        self.steps.append(step)

                elif interactionFlag == 'source':
                    self.source_choices = []
                    self.target_choices = []
                    for s in act_def['source']:
                        #Save description as string, not a dictionary
                        desc = json.dumps(s['description'])
                        source = models.activity_definition_source(source_id=s['id'], description=desc,
                            activity_definition=self.activity_definition)
                        source.save()
                        self.source_choices.append(source)
                    for t in act_def['target']:
                        #Save description as string, not a dictionary
                        desc = json.dumps(t['description'])
                        target = models.activity_definition_target(target_id=t['id'], description=desc,
                            activity_definition=self.activity_definition)
                        target.save()
                        self.target_choices.append(target)        

            #Instantiate activity definition extensons
            self.activity_definition_extensions = []

            #See if activity definition has extensions
            if 'extensions' in act_def.keys():
                for k, v in act_def['extensions'].items():
                    act_def_ext = models.activity_extentions(key=k, value=v,
                        activity_definition=self.activity_definition)
                    act_def_ext.save()
                    self.activity_definition_extensions.append(act_def_ext)    

