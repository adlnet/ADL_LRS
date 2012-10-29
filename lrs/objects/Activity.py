import json
import urllib2
import datetime
from StringIO import StringIO
from lrs import models, exceptions
from lxml import etree
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import transaction
import pdb

class Activity():

    # Activity definition required fields
    ADRFs = ['name', 'description', 'type']

    # Activity definition types
    # ADTs = ['course', 'module', 'meeting', 'media', 'performance', 'simulation', 'assessment',
    #         'interaction', 'cmi.interaction', 'question', 'objective', 'link']

    # URL Validator
    validator = URLValidator(verify_exists=True)

    # XMLschema for Activity IDs
    req = urllib2.Request('http://tincanapi.com/wp-content/assets/tincan.xsd')
    resp = urllib2.urlopen(req)
    XML = resp.read()
    XMLschema_doc = etree.parse(StringIO(XML))
    XMLschema = etree.XMLSchema(XMLschema_doc)

    # Use single transaction for all the work done in function
    @transaction.commit_on_success
    def __init__(self, initial=None, activity_id=None, get=False, auth=None):
        #Get activity object
        if get and activity_id is not None:
            self.activity_id = activity_id
            #Check to see if activity exists
            try:
                self.activity = models.activity.objects.get(activity_id=self.activity_id)            
            except models.activity.DoesNotExist:
                raise exceptions.IDNotFoundError('There is no activity associated with the id: %s' % self.activity_id)
        else:
            # pdb.set_trace()
            self.auth = auth
            self.initial = initial
            self.obj = self._parse(initial)
            self._populate(self.obj)

    # Make sure initial data being received is JSON
    def _parse(self,initial):
        if initial:
            try:
                return json.loads(initial)
            except Exception as e:
                raise exceptions.ParamError("Error parsing the Activity object. Expecting json. Received: %s which is %s" % (initial, type(initial))) 
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
                #TODO: should put any warning here? validXML will still be false if there is an exception
                raise exceptions.ParamError("The activity id resolved to invalid activity description")
                #pass        

        #Parse XML, create dictionary with the values from the XML doc
        if validXML:
            return self._parseXML(act_xmlschema_doc)
        else:
            return {}

    # TODO: Thought xml was taken out? Need to update parsing of it then for name and desc?
    def _parseXML(self, xmldoc):
        #Create namespace and get the root
        ns = {'tc':'http://projecttincan.com/tincan.xsd'}
        root = xmldoc.getroot()
        act_def = {}

        #Parse the name (required)
        if len(root.xpath('//tc:activities/tc:activity/tc:name', namespaces=ns)) > 0:
            act_def['name'] = {}

            for element in root.xpath('//tc:activities/tc:activity/tc:name', namespaces=ns):
                lang = element.get('lang')
                act_def['name'][lang] = element.text
        else:
            raise exceptions.ParamError("XML is missing name")
            
        #Parse the description (required)    
        if len(root.xpath('//tc:activities/tc:activity/tc:description', namespaces=ns)) > 0:
            act_def['description'] = {}
            
            for element in root.xpath('//tc:activities/tc:activity/tc:description', namespaces=ns):
                lang = element.get('lang')
                act_def['description'][lang] = element.text

            # lang = root.xpath('//tc:activities/tc:activity/tc:description/@lang', namespaces=ns)[0]
            # act_def['description'][lang] = root.xpath('//tc:activities/tc:activity/tc:description/text()', namespaces=ns)[0]
        else:
            raise exceptions.ParamError("XML is missing description")
            
        #Parse the interactionType (required)
        if root.xpath('//tc:activities/tc:activity/tc:interactionType/text()', namespaces=ns)[0]:
            act_def['interactionType'] = root.xpath('//tc:activities/tc:activity/tc:interactionType/text()', namespaces=ns)[0]
        else:
            raise exceptions.ParamError("XML is missing interactionType")

        #Parse the type (required)
        if root.xpath('//tc:activities/tc:activity/@type', namespaces=ns)[0]:
            act_def['type'] = root.xpath('//tc:activities/tc:activity/@type', namespaces=ns)[0]
        else:
            raise exceptions.ParamError("XML is missing type")

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
    def _save_actvity_to_db(self, act_id, objType, act_def=None):
        if act_def:
            if self.auth is not None:
                act = models.activity(activity_id=act_id, objectType=objType, activity_definition=act_def, authoritative=self.auth)
            else:
                act = models.activity(activity_id=act_id, objectType=objType, activity_definition=act_def)
        else:
            if self.auth is not None:
                act = models.activity(activity_id=act_id, objectType=objType, authoritative=self.auth)
            else:
                act = models.activity(activity_id=act_id, objectType=objType)

        act.save()
        return act

    #Save activity definition to DB
    def _save_activity_definition_to_db(self,act_def_type, intType):
        act_def = models.activity_definition(activity_definition_type=act_def_type,
                  interactionType=intType)
        act_def.save()
        return act_def    

    def get_full_activity_json(self):
        ret = self.activity.object_return()
        return ret

    # Called when need to check if existing activity definition has the same name/desc as the incoming one
    def _check_names_and_descriptions(self, new_name_key, new_name_value, new_desc_key, new_desc_value,
                                    existing_name=None, existing_desc=None):
        name_diff = False
        desc_diff = False

        # Check both name and description against existing values
        if existing_name:
            if not new_name_key == existing_name.key or not new_name_value == existing_name.value:
                name_diff = True

        if existing_desc:
            if not new_desc_key == existing_desc.key or not new_desc_value == existing_desc.value:
                desc_diff = True
        return (name_diff, desc_diff)

    def _check_activity_definition_value(self, new_name_value, existing_name_value):
        return new_name_value == existing_name_value

    def _update_activity_name_and_description(self, new_activity, existing_activity):
        # Try grabbing the activity definition (these aren't required)
        existing_act_def = None        
        try:
            existing_act_def = models.activity_definition.objects.get(activity=existing_activity)
        except models.activity_definition.DoesNotExist:
            pass

        # If there is an existing activity definition and the names or descriptions are different,
        # update it with new name and/or description info
        if existing_act_def:
            # Get list of existing name lang maps
            existing_name_lang_map_set = existing_act_def.name.all()

            # Make lists of keys and values from existing name lang maps
            existing_name_key_set = existing_name_lang_map_set.values_list('key', flat=True)

            # Get list of existing desc lang maps
            existing_desc_lang_map_set = existing_act_def.description.all()

            # Make lists of keys and values from existing desc lang maps
            existing_desc_key_set = existing_desc_lang_map_set.values_list('key', flat=True)

            # Loop through all language maps in name
            try:
                the_definition = new_activity['definition']
            except KeyError:
                raise exceptions.ParamError("Activity missing definition")
            try:
                the_names = the_definition['name']
            except KeyError:
                raise exceptions.ParamError("Activity definition has no name attribute")
            for new_name_lang_map in the_names.items():
                # If there is already an entry in the same language
                if new_name_lang_map[0] in existing_name_key_set:
                    name_same = True                    
                    # Retrieve existing language map with same key (all in the existing act_def)
                    existing_lang_map = existing_act_def.name.get(key=new_name_lang_map[0])
                    name_same = self._check_activity_definition_value(new_name_lang_map[1], existing_lang_map.value)
                    # If names are different, update the language map with the new name
                    if not name_same:
                        models.LanguageMap.objects.filter(id=existing_lang_map.id).update(value=new_name_lang_map[1])
                # Else it's a new lang map and needs added
                else:
                    lang_map = self._save_lang_map(new_name_lang_map)
                    existing_act_def.name.add(lang_map)
                    existing_act_def.save()                    

            # Loop through all language maps in description
            try:
                the_descriptions = the_definition['description']
            except KeyError:
                raise exceptions.ParamError("Activity definition has no description attribute")
            for new_desc_lang_map in the_descriptions.items():
                # If there is already an entry in the same language
                if new_desc_lang_map[0] in existing_desc_key_set:
                    desc_same = False
                    # Retrieve existing language map with same key (all in the existing act_def)
                    existing_lang_map = existing_act_def.description.get(key=new_desc_lang_map[0])
                    desc_same = self._check_activity_definition_value(new_desc_lang_map[1], existing_lang_map.value)
                    # If desc are different, update the langage map with the new desc
                    if not desc_same:
                        models.LanguageMap.objects.filter(id=existing_lang_map.id).update(value=new_desc_lang_map[1])
                else:
                    lang_map = self._save_lang_map(new_desc_lang_map)
                    existing_act_def.description.add(lang_map)
                    existing_act_def.save()                    

    #Once JSON is verified, populate the activity objects
    def _populate(self, the_object):
        valid_schema = False
        xml_data = {}
        
        #Must include activity_id - set object's activity_id
        try:
            activity_id = the_object['id']
        except KeyError:
            raise exceptions.ParamError("No id provided, must provide 'id' field")
        # Check if activity ID already exists
        id_list = models.activity.objects.values_list('activity_id', flat=True)
        if activity_id in id_list:
            # Grab pre-existing activity
            existing_activity = models.activity.objects.get(activity_id=activity_id)

            # If authority is required to update the activity
            if existing_activity.authoritative is not None:
                # Request has correct authority
                if existing_activity.authoritative == self.auth:
                    # Update name and desc if needed
                    self._update_activity_name_and_description(the_object, existing_activity)
            
                    # Set activity to existing one
                    self.activity = existing_activity
                # Someone with wrong auth trying to update activity
                else:
                    raise exceptions.Forbidden("This ActivityID already exists, and you do not have" + 
                        " the correct authority to create or update it.") 
            # No auth required to update activity
            else:
                # Update name and desc if needed
                self._update_activity_name_and_description(the_object, existing_activity)
        
                # Set activity to existing one
                self.activity = existing_activity                

        # Activity ID doesn't exist, create a new one
        else:
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
                try:
                    if activity_definition['type'] == 'link':
                        try:
                            Activity.validator(activity_id)
                        except ValidationError, e:
                            raise exceptions.ParamError(str(e))
                    else:
                        #Type is not a link - it can be allowed to not resolve and will just return an empty dictionary    
                        #If activity is not a link, the ID either must not resolve or validate against metadata schema
                        xml_data = self._validateID(activity_id)
                except KeyError:
                    raise exceptions.ParamError("Activity definition type is missing or malformed")
                
                #If the returned data is not empty, it overrides any JSON data sent in
                if xml_data:
                    activity_definition = xml_data

                #If the URL did not resolve and is not type link, it will use the JSON data provided
                self._populate_definition(activity_definition, activity_id, objectType)
        
    # Save language map object for activity definition name or description
    def _save_lang_map(self, lang_map):
        k = lang_map[0]
        v = lang_map[1]

        language_map = models.LanguageMap(key = k, value = v)
        
        language_map.save()        
        return language_map

    #Populate definition either from JSON or validated XML
    def _populate_definition(self, act_def, act_id, objType):
        #Needed for cmi.interaction args
        interactionFlag = ""

        #Check if all activity definition required fields are present - deletes existing activity model
        #if error with required activity definition fields
        for k in Activity.ADRFs:
            if k not in act_def.keys() and k != 'extensions':
                raise exceptions.ParamError("Activity definition error with key: %s" % k)

        #Check definition type
        # if act_def['type'] not in Activity.ADTs:
        #     raise Exception("Activity definition type not valid")


        #If the type is cmi.interaction, have to check interactionType
        if act_def['type'] == 'cmi.interaction':

            scormInteractionTypes = ['true-false', 'choice', 'fill-in', 'long-fill-in',
                                     'matching', 'performance', 'sequencing', 'likert', 'numeric',
                                     'other']
        
            #Check if valid SCORM interactionType
            if act_def['interactionType'] not in scormInteractionTypes:
                raise exceptions.ParamError("Activity definition interactionType not valid")

            #Must have correctResponsesPattern if they have a valid interactionType
            try:
                act_def['correctResponsesPattern']  
            except KeyError:    
                raise exceptions.ParamError("Activity definition missing correctResponsesPattern")    

            #Multiple choice and sequencing must have choices
            if act_def['interactionType'] == 'choice' or \
                act_def['interactionType'] == 'sequencing':
                    try:
                        act_def['choices']
                    except KeyError:
                        raise exceptions.ParamError("Activity definition missing choices")
                    interactionFlag = 'choices' 

            #Matching must have both source and target
            if act_def['interactionType'] == 'matching':
                try:
                    act_def['source']
                    act_def['target']
                except KeyError:
                    raise exceptions.ParamError("Activity definition missing source/target for matching")
                interactionFlag = 'source'

            #Performance must have steps
            if act_def['interactionType'] == 'performance':
                try:
                    act_def['steps']
                except KeyError:
                    raise exceptions.ParamError("Activity definition missing steps for performance")    
                interactionFlag = 'steps'

            #Likert must have scale
            if act_def['interactionType'] == 'likert':
                try:
                    act_def['scale']
                except KeyError:
                    raise exceptions.ParamError("Activity definition missing scale for likert")
                interactionFlag = 'scale'

        self.activity_definition = self._save_activity_definition_to_db(act_def['type'], act_def.get('interactionType', None))

        # Save activity definition name and description
        for name_lang_map in act_def['name'].items():
            if isinstance(name_lang_map, tuple):
                lang_map = self._save_lang_map(name_lang_map)
                self.activity_definition.name.add(lang_map)
                self.activity_definition.save()
            else:
                raise exceptions.ParamError("Activity with id %s has a name that is not a language map" % act_id)

        for desc_lang_map in act_def['description'].items():
            if isinstance(desc_lang_map, tuple):
                lang_map = self._save_lang_map(desc_lang_map)
                self.activity_definition.description.add(lang_map)
                self.activity_definition.save()
            else:
                raise exceptions.ParamError("Activity with id %s has a description that is not a language map" % act_id)

        self.activity = self._save_actvity_to_db(act_id, objType, self.activity_definition)

        #If there is a correctResponsesPattern then save the pattern
        if 'correctResponsesPattern' in act_def.keys():
            self._populate_correctResponsesPattern(act_def, interactionFlag)

        #See if activity definition has extensions
        if 'extensions' in act_def.keys():
            self._populate_extensions(act_def) 

    def _populate_correctResponsesPattern(self, act_def, interactionFlag):
        # crp = models.activity_def_correctresponsespattern(activity_definition=self.activity_definition)
        crp = models.activity_def_correctresponsespattern()
        crp.save()
        self.activity_definition.correctresponsespattern = crp
        self.activity_definition.save()
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
                choice = models.activity_definition_choice(choice_id=c['id'], activity_definition=self.activity_definition)
                choice.save()
                #Save description as string, not a dictionary
                for desc_lang_map in c['description'].items():
                    if isinstance(desc_lang_map, tuple):
                        lang_map = self._save_lang_map(desc_lang_map)
                        choice.description.add(lang_map)
                        choice.save()
                    else:
                        raise exceptions.ParamError("Choice description must be a language map")

                self.choices.append(choice)
        
        elif interactionFlag == 'scale':
            self.scale_choices = []
            for s in act_def['scale']:
                scale = models.activity_definition_scale(scale_id=s['id'], activity_definition=self.activity_definition)        
                scale.save()
                # Save description as string, not a dictionary
                for desc_lang_map in s['description'].items():
                    if isinstance(desc_lang_map, tuple):
                        lang_map = self._save_lang_map(desc_lang_map)
                        scale.description.add(lang_map)
                        scale.save()
                    else:
                        raise exceptions.ParamError("Scale description must be a language map")                        

                self.scale_choices.append(scale)

        elif interactionFlag == 'steps':
            self.steps = []
            for s in act_def['steps']:
                step = models.activity_definition_step(step_id=s['id'], activity_definition=self.activity_definition)
                step.save()
                #Save description as string, not a dictionary
                for desc_lang_map in s['description'].items():
                    if isinstance(desc_lang_map, tuple):
                        lang_map = self._save_lang_map(desc_lang_map)
                        step.description.add(lang_map)
                        step.save()
                    else:
                        raise exceptions.ParamError("Step description must be a language map")                        

                self.steps.append(step)

        elif interactionFlag == 'source':
            self.source_choices = []
            self.target_choices = []
            for s in act_def['source']:
                source = models.activity_definition_source(source_id=s['id'], activity_definition=self.activity_definition)
                source.save()                        
                #Save description as string, not a dictionary
                for desc_lang_map in s['description'].items():
                    if isinstance(desc_lang_map, tuple):
                        lang_map = self._save_lang_map(desc_lang_map)
                        source.description.add(lang_map)
                        source.save()
                    else:
                        raise exceptions.ParamError("Source description must be a language map")                        
                self.source_choices.append(source)
            
            for t in act_def['target']:
                target = models.activity_definition_target(target_id=t['id'], activity_definition=self.activity_definition)
                target.save()
                #Save description as string, not a dictionary
                for desc_lang_map in t['description'].items():
                    if isinstance(desc_lang_map, tuple):
                        lang_map = self._save_lang_map(desc_lang_map)
                        target.description.add(lang_map)
                        target.save()
                    else:
                        raise exceptions.ParamError("Target description must be a language map")                        

                self.target_choices.append(target)        


    def _populate_extensions(self, act_def):
        self.activity_definition_extensions = []

        for k, v in act_def['extensions'].items():
            act_def_ext = models.activity_extensions(key=k, value=v,
                activity_definition=self.activity_definition)
            act_def_ext.save()
            self.activity_definition_extensions.append(act_def_ext)    
