import json
import types
import urllib
import urllib2
import datetime
import urlparse
from StringIO import StringIO
from lrs import models
from lrs.util import etag
from lxml import etree
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
            etag.check_preconditions(request_dict,p, required=True)
            p.profile.delete()
        p.content_type = request_dict['CONTENT_TYPE']
        p.etag = etag.create_tag(profile.read())
        if request_dict['updated']:
            p.updated = request_dict['updated']
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
        if since:
            try:
                profs = self.agent.actor_profile_set.filter(updated__gte=since)
            except ValidationError:
                since_i = int(float(since))
                since_dt = datetime.datetime.fromtimestamp(since_i)
                profs = self.agent.actor_profile_set.filter(update__gte=since_dt)
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


class ActivityState():
    def __init__(self, request_dict):
        self.req_dict = request_dict
        self.actor = request_dict['actor']
        try:
            self.activity = models.activity.objects.get(activity_id=request_dict['activityId'])
        except models.activity.DoesNotExist:
            raise IDNotFoundError("Error with Activity State. The activity id (%s) did not match any activities on record: %s" % (request_dict['activityId']))
        self.registrationId = request_dict.get('registrationId', None)
        self.stateId = request_dict.get('stateId', None)
        self.updated = request_dict.get('updated', None)
        self.content_type = request_dict.get('CONTENT_TYPE', None)
        self.state = request_dict.get('state', None)
        self.etag = request_dict.get('ETAG', None)
        self.since = request_dict.get('since', None)

    def __get_actor(self, create=False):
        actor = Actor(self.actor, create=create).agent
        if not actor:
            raise IDNotFoundError("Error with Activity State. The actor partial (%s) did not match any actors on record" % actor) 
        return actor

    @transaction.commit_on_success
    def put(self):
        actor = self.__get_actor(create=True)
        try:
            state = ContentFile(self.state.read())
        except:
            try:
                state = ContentFile(self.state)
            except:
                state = ContentFile(str(self.state))

        if self.registrationId:
            p,created = models.activity_state.objects.get_or_create(state_id=self.stateId,actor=actor,activity=self.activity,registration_id=self.registrationId)
        else:
            p,created = models.activity_state.objects.get_or_create(state_id=self.stateId,actor=actor,activity=self.activity)
        if not created:
            etag.check_preconditions(self.req_dict,p)
            p.state.delete() # remove old state file
        p.content_type = self.content_type
        p.etag = etag.create_tag(state.read())
        if self.updated:
            p.updated = self.updated
        state.seek(0)
        if created:
            p.save()

        fn = "%s_%s_%s" % (p.actor_id,p.activity_id, self.req_dict.get('filename', p.id))
        p.state.save(fn, state)

    def get(self):
        actor = self.__get_actor()
        try:
            if self.registrationId:
                return models.activity_state.objects.get(state_id=self.stateId, actor=actor, activity=self.activity, registration_id=self.registrationId)
            return models.activity_state.objects.get(state_id=self.stateId, actor=actor, activity=self.activity)
        except models.activity_state.DoesNotExist:
            raise IDNotFoundError('There is no activity state associated with the id: %s' % self.stateId)

    def get_set(self,**kwargs):
        actor = self.__get_actor()
        if self.registrationId:
            state_set = models.activity_state.objects.filter(actor=actor, activity=self.activity, registration_id=self.registrationId)
        else:
            state_set = models.activity_state.objects.filter(actor=actor, activity=self.activity)
        return state_set

    def get_ids(self):
        try:
            state_set = self.get_set()
        except models.activity_state.DoesNotExist:
            return []
        if self.since:
            state_set = state_set.filter(updated__gte=self.since)
        return state_set.values_list('state_id', flat=True)

    def delete(self):
        try:
            if not self.stateId:
                state = self.get_set()
                for s in state:
                    s.delete() # bulk delete skips the custom delete function
            else:
                state = self.get()
                state.delete()
        except models.activity_state.DoesNotExist:
            pass
        except IDNotFoundError:
            pass
        

class Activity():

    #Activity definition required fields
    ADRFs = ['name', 'description', 'type', 'interactionType']

    #Activity definition types
    ADTs = ['course', 'module', 'meeting', 'media', 'performance', 'simulation', 'assessment',
            'interaction', 'cmi.interaction', 'question', 'objective', 'link']

    #URL Validator
    validator = URLValidator(verify_exists=True)

    #XMLschema for Activity IDs
    req = urllib2.Request('http://projecttincan.com/tincan.xsd')
    resp = urllib2.urlopen(req)
    XML = resp.read()
    XMLschema_doc = etree.parse(StringIO(XML))
    XMLschema = etree.XMLSchema(XMLschema_doc)

    #Use single transaction for all the work done in function
    @transaction.commit_on_success
    def __init__(self, initial=None, test=True):
        self.initial = initial
        self.obj = self._parse(initial)
        self._populate(self.obj, test)

    #Make sure initial data being received is JSON
    def _parse(self,initial):
        if initial:
            try:
                return json.loads(initial)
            except Exception as e:
                raise Exception("Error parsing the Activity object. Expecting json. Received: %s" % initial) 
        return {}

    def _validateID(self,act_id):
        validXML = False
        resolves = True

        #Retrieve XML doc since function is only called when not a link. ID should either not resolve or 
        #only conform to the TC schema - if it fails that means the URL didn't resolve at all
        try:    
            act_resp = urllib2.urlopen(act_id)
        except Exception, e:
            resolves = False
        else:
            act_XML = act_resp.read()

        #Validate that it is good XML with the schema - if it fails it means the URL resolved but didn't conform to the schema
        if resolves:
            try:
                act_xmlschema_doc = etree.parse(StringIO(act_XML))    
                validXML = Activity.XMLschema.validate(act_xmlschema_doc)
            except Exception, e:
                raise e        

        #Parse XML, create dictionary with the values from the XML doc
        if validXML:
            return self._parseXML(act_xmlschema_doc)
        else:
            return {}

    def _parseXML(self, xmldoc):
        #Create namespace and get the root
        ns = {'tc':'http://projecttincan.com/tincan.xsd'}
        root = xmldoc.getroot()
        act_def = {}

        #Parse the name (required)
        if root.xpath('//tc:activities/tc:activity/tc:name/text()', namespaces=ns)[0]:
            act_def['name'] = root.xpath('//tc:activities/tc:activity/tc:name/text()', namespaces=ns)[0]
        else:
            raise(Exception, "XML is missing name")
            
        #Parse the description (required)    
        if root.xpath('//tc:activities/tc:activity/tc:description/text()', namespaces=ns)[0]:
            act_def['description'] = root.xpath('//tc:activities/tc:activity/tc:description/text()', namespaces=ns)[0]
        else:
            raise(Exception, "XML is missing description")
            
        #Parse the interactionType (required)
        if root.xpath('//tc:activities/tc:activity/tc:interactionType/text()', namespaces=ns)[0]:
            act_def['interactionType'] = root.xpath('//tc:activities/tc:activity/tc:interactionType/text()', namespaces=ns)[0]
        else:
            raise(Exception, "XML is missing interactionType")

        #Parse the type (required)
        if root.xpath('//tc:activities/tc:activity/@type', namespaces=ns)[0]:
            act_def['type'] = root.xpath('//tc:activities/tc:activity/@type', namespaces=ns)[0]
        else:
            raise(Exception, "XML is missing type")

        #Parse extensions if any
        if root.xpath('//tc:activities/tc:activity/tc:extensions', namespaces=ns) is not None:
            extensions = {}
            extensionTags = root.xpath('//tc:activities/tc:activity/tc:extensions/tc:extension', namespaces=ns)
            
            for tag in extensionTags:
                extensions[tag.get('key')] = tag.text

            act_def['extensions'] = extensions

        #Parse correctResponsesPattern if any
        if root.xpath('//tc:activities/tc:activity/tc:correctResponsesPattern', namespaces=ns) is not None:
            crList = []
            correctResponseTags = root.xpath('//tc:activities/tc:activity/tc:correctResponsesPattern/tc:correctResponsePattern', namespaces=ns)
                
            for cr in correctResponseTags:    
                crList.append(cr.text)

            act_def['correctResponsesPattern'] = crList

        return act_def

    #Save activity to DB
    def _save_actvity_to_db(self, act_id, objType):
        act = models.activity(activity_id=act_id, objectType=objType)
        act.save()
        return act

    #Save activity definition to DB
    def _save_activity_definition_to_db(self, act, name, desc, act_def_type, intType):
        act_def = models.activity_definition(name=name,description=desc, activity_definition_type=act_def_type,
                  interactionType=intType, activity=act)
        act_def.save()
        return act_def    

    #Once JSON is verified, populate the activity objects
    def _populate(self, the_object, test):
        valid_schema = False
        xml_data = {}

        #Must include activity_id - set object's activity_id
        try:
            activity_id = the_object['id']
        except KeyError:
            raise Exception("No id provided, must provide 'id' field")

        #Check if activity ID already exists
        IDList = models.activity.objects.values_list('activity_id', flat=True)

        if activity_id in IDList:
            raise(Exception, "Activity ID is already in use, please use a different naming technique")

        #Set objectType to nothing
        objectType = None

        #ObjectType should always be Activity when present
        if 'objectType' in the_object.keys():
            objectType = 'Activity'

        #Try to grab XML from ID if no other JSON is provided - since it won't have a definition it's not a link
        #therefore it can be allowed to not resolve and will just return an empty dictionary
        if not 'definition' in the_object.keys():
            xml_data = self._validateID(activity_id)

            #If the ID validated against the XML schema then proceed with populating the definition with the info
            #from the XML - else just save the activity (someone sent in an ID that doesn't resolve and an objectType
            #with no other data)                
            if xml_data:
                self._populate_definition(xml_data, activity_id, objectType)
            else:    
                self.activity = self._save_actvity_to_db(activity_id, objectType)
        #Definition is provided
        else:
            activity_definition = the_object['definition']
         
            #Verify the given activity_id resolves if it is a link (has to resolve if link) 
            if activity_definition['type'] == 'link':
                try:
                    Activity.validator(activity_id)
                except ValidationError, e:
                    raise e
            #Type is not a link - it can be allowed to not resolve and will just return an empty dictionary    
            else:
                #If activity is not a link, the ID either must not resolve or validate against metadata schema
                xml_data = self._validateID(activity_id)
            
            #If the returned data is not empty, it overrides any JSON data sent in
            if xml_data:
                activity_definition = xml_data

            #If the URL did not resolve and is not type link, it will use the JSON data provided
            self._populate_definition(activity_definition, activity_id, objectType)
        


    #Populate definition either from JSON or validated XML
    def _populate_definition(self, act_def, act_id, objType):
            #Needed for cmi.interaction args
            interactionFlag = ""

            #Check if all activity definition required fields are present - deletes existing activity model
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

            #Save activity to DB
            self.activity = self._save_actvity_to_db(act_id, objType)

            #Save activity definition to DB
            self.activity_definition = self._save_activity_definition_to_db(self.activity, act_def['name'],
                        act_def['description'], act_def['type'], act_def['interactionType'])
    
            #If there is a correctResponsesPattern then save the pattern
            if 'correctResponsesPattern' in act_def.keys():
                crp = models.activity_def_correctresponsespattern(activity_definition=self.activity_definition)
                crp.save()
                self.correctResponsesPattern = crp
                
                #For each answer in the pattern save it
                self.answers = []
                for i in act_def['correctResponsesPattern']:
                    answer = models.correctresponsespattern_answer(answer=i, correctresponsespattern=self.correctResponsesPattern)
                    answer.save()
                    self.answers.append(answer)
    
                #Depending on which type of interaction, save the unique fields accordingly
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

            #See if activity definition has extensions
            if 'extensions' in act_def.keys(): 
                self.activity_definition_extensions = []

                for k, v in act_def['extensions'].items():
                    act_def_ext = models.activity_extentions(key=k, value=v,
                        activity_definition=self.activity_definition)
                    act_def_ext.save()
                    self.activity_definition_extensions.append(act_def_ext)    

