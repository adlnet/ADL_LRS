import json
import urllib2
import datetime
from StringIO import StringIO
from lrs import models
from lxml import etree
from django.core import serializers
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import transaction


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
    def __init__(self, initial=None, activity_id=None, get=False):
        #Get activity object
        if get and activity_id is not None:
            self.activity_id = activity_id
        else:
            self.initial = initial
            self.obj = self._parse(initial)
            self._populate(self.obj)

    #Make sure initial data being received is JSON
    def _parse(self,initial):
        if initial:
            try:
                return json.loads(initial)
            except Exception as e:
                raise Exception("Error parsing the Activity object. Expecting json. Received: %s which is %s" % (initial, type(initial))) 
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

    def get_full_activity_json(self):
        json_serializer = serializers.get_serializer("json")()
        #Check to see if activity exists
        try:
            act = models.activity.objects.get(activity_id=self.activity_id)            
        except models.activity.DoesNotExist:
            raise IDNotFoundError('There is no activity associated with the id: %s' % self.activity_id)

        #Set activity to return
        ret = act.objReturn()

        #Check if definition exists
        try:
            act_def = models.activity_definition.objects.get(activity=act)
        except Exception, e:
            #No definition so return activity
            return ret

        #Return activity definition will be set if there is one
        ret['definition'] = act_def.objReturn() 

        #Check for extensions
        try:
            extList = models.activity_extentions.objects.filter(activity_definition=act_def)
        except Exception, e:
            #Extensions are optional so pass if there aren't any
            pass

        #If there were extenstions add them to return activity
        if extList:
            ret['extensions'] = {}    
            for ext in extList:
                ret['extensions'][ext.objReturn()[0]] = ext.objReturn()[1]

        if not ret['definition']['type'] == 'cmi.interaction':
            return ret
        else:
            #Must have correct responses pattern and answers
            act_crp = models.activity_def_correctresponsespattern.objects.get(activity_definition=act_def)
            ansList = models.correctresponsespattern_answer.objects.filter(correctresponsespattern=act_crp)
        
            alist = []
            for answer in ansList:
                alist.append(answer.objReturn())
            ret['correctResponsesPattern'] = alist

            if ret['definition']['interactionType'] == 'multiple-choice' or ret['definition']['interactionType'] == 'sequencing':
                chList = models.activity_definition_choice.objects.filter(activity_definition=act_def)
            
                clist = []
                for choice in chList:
                    clist.append(choice.objReturn())
                ret['choices'] = clist

            if ret['definition']['interactionType'] == 'likert':
                scList = models.activity_definition_scale.objects.filter(activity_definition=act_def)
            
                slist = []
                for scale in scList:
                    slist.append(scale.objReturn())
                ret['scale'] = slist

            if ret['definition']['interactionType'] == 'performance':
                stepList = models.activity_definition_step.objects.filter(activity_definition=act_def)

                stlist = []
                for step in stepList:
                    stlist.append(step.objReturn())
                ret['steps'] = stlist

            if ret['definition']['interactionType'] == 'matching':
                sourceList = models.activity_definition_source.objects.filter(activity_definition=act_def)

                solist = []
                for source in sourceList:
                    solist.append(source.objReturn())    
                ret['source'] = solist

                tarList = models.activity_definition_target.objects.filter(activity_definition=act_def)

                tlist = []
                for target in tarList:
                    tlist.append(target.objReturn())    
                ret['target'] = tlist

        return ret


    #Once JSON is verified, populate the activity objects
    def _populate(self, the_object):
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
                self._populate_correctResponsesPattern(act_def, interactionFlag)

            #See if activity definition has extensions
            if 'extensions' in act_def.keys():
                self._populate_extensions(act_def) 


    def _populate_correctResponsesPattern(self, act_def, interactionFlag):
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


    def _populate_extensions(self, act_def):
                self.activity_definition_extensions = []

                for k, v in act_def['extensions'].items():
                    act_def_ext = models.activity_extentions(key=k, value=v,
                        activity_definition=self.activity_definition)
                    act_def_ext.save()
                    self.activity_definition_extensions.append(act_def_ext)    



class IDNotFoundError(Exception):
    def __init__(self, msg):
        self.message = msg
    def __str__(self):
        return repr(self.message)