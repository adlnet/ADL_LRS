import json
import urllib2
import datetime
from StringIO import StringIO
from lrs import models, exceptions
from lrs.util import log_message, update_parent_log_status, uri
from lxml import etree
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import transaction
import pdb
import pprint
import logging

logger = logging.getLogger('user_system_actions')

class Activity():
    # Activity definition required fields
    ADRFs = ['name', 'description', 'type']

    # URL Validator
    validator = URLValidator(verify_exists=True)

    # XMLschema for Activity IDs
    try:
        # oh i don't like this... TODO: can we make this better?
        resp = open('lrs/static/tincan.xsd', 'rb')
        XML = resp.read()
        XMLschema_doc = etree.parse(StringIO(XML))
        XMLschema = etree.XMLSchema(XMLschema_doc)
        can_validate_xml = True
    except Exception as e:
        print ">>>>>>>>>>>>> no xsd <<<<<<<<<<<<<<<<<<<<"
        print e
        can_validate_xml = False

    # Use single transaction for all the work done in function
    @transaction.commit_on_success
    def __init__(self, data, auth=None, log_dict=None, define=True):
        if auth:
            if auth.__class__.__name__ == 'group':
                self.auth = auth.name
            else:
                self.auth = auth.username
        else:
            self.auth = None
        self.log_dict = log_dict
        self.params = data
        self.define = define
        if not isinstance(data, dict):
            self.params = self.parse(data)
        self.populate(self.params)

    # Make sure initial data being received is can be transformed into a dict-should ALWAYS be
    # incoming JSON because class is only called from Statement class
    def parse(self,data):        
        try:
            params = json.loads(data)
        except Exception, e:
            err_msg = "Error parsing the Activity object. Expecting json. Received: %s which is %s" % (data, type(data))
            log_message(self.log_dict, err_msg, __name__, self.parse.__name__, True) 
            update_parent_log_status(self.log_dict, 400)               
            raise exceptions.ParamError(err_msg)
        return params


    def validateID(self,act_id):
        validXML = False
        resolves = True

        log_message(self.log_dict, "Validating Activity ID", __name__, self.validateID.__name__)

        #Retrieve XML doc since function is only called when not a link. ID should either not resolve or 
        #only conform to the TC schema - if it fails that means the URL didn't resolve at all
        try:    
            act_resp = urllib2.urlopen(act_id, timeout=10)
        except Exception, e:
            resolves = False
        else:
            act_XML = act_resp.read()

        #Validate that it is good XML with the schema - if it fails it means the URL resolved but didn't conform to the schema
        if resolves and Activity.can_validate_xml:
            try:
                act_xmlschema_doc = etree.parse(StringIO(act_XML))    
                validXML = Activity.XMLschema.validate(act_xmlschema_doc)
            except Exception, e:
                #TODO: should put any warning here? validXML will still be false if there is an exception
                self.activity.delete()
                self.activity = None
                err_msg = "The activity id resolved to invalid activity description"
                log_message(self.log_dict, err_msg, __name__, self.parse.__name__, True) 
                update_parent_log_status(self.log_dict, 400)                    
                raise exceptions.ParamError(err_msg)

        #Parse XML, create dictionary with the values from the XML doc
        if validXML:
            return self.parseXML(act_xmlschema_doc)
        else:
            return {}

    # TODO: Thought xml was taken out? Need to update parsing of it then for name and desc?
    def parseXML(self, xmldoc):
        #Create namespace and get the root
        ns = {'tc':'http://projecttincan.com/tincan.xsd'}
        root = xmldoc.getroot()
        act_def = {}

        log_message(self.log_dict, "Parsing Activity XML", __name__, self.parseXML.__name__)                     

        #Parse the name (required)
        if len(root.xpath('//tc:activities/tc:activity/tc:name', namespaces=ns)) > 0:
            act_def['name'] = {}

            for element in root.xpath('//tc:activities/tc:activity/tc:name', namespaces=ns):
                lang = element.get('lang')
                act_def['name'][lang] = element.text
        else:
            err_msg = "XML is missing name"
            log_message(self.log_dict, err_msg, __name__, self.parseXML.__name__, True) 
            update_parent_log_status(self.log_dict, 400)                                
            raise exceptions.ParamError(err_msg)
            
        #Parse the description (required)    
        if len(root.xpath('//tc:activities/tc:activity/tc:description', namespaces=ns)) > 0:
            act_def['description'] = {}
            
            for element in root.xpath('//tc:activities/tc:activity/tc:description', namespaces=ns):
                lang = element.get('lang')
                act_def['description'][lang] = element.text
        else:
            err_msg = "XML is missing description"
            log_message(self.log_dict, err_msg, __name__, self.parseXML.__name__, True)
            update_parent_log_status(self.log_dict, 400)
            raise exceptions.ParamError(err_msg)
            
        #Parse the interactionType (required)
        if root.xpath('//tc:activities/tc:activity/tc:interactionType/text()', namespaces=ns)[0]:
            act_def['interactionType'] = root.xpath('//tc:activities/tc:activity/tc:interactionType/text()', namespaces=ns)[0]
        else:
            err_msg = "XML is missing interactionType"
            log_message(self.log_dict, err_msg, __name__, self.parseXML.__name__, True)  
            update_parent_log_status(self.log_dict, 400)          
            raise exceptions.ParamError(err_msg)

        #Parse the type (required)
        if root.xpath('//tc:activities/tc:activity/@type', namespaces=ns)[0]:
            act_def['type'] = root.xpath('//tc:activities/tc:activity/@type', namespaces=ns)[0]
        else:
            err_msg = "XML is missing type"
            log_message(self.log_dict, err_msg, __name__, self.parseXML.__name__, True)
            update_parent_log_status(self.log_dict, 400)
            raise exceptions.ParamError(err_msg)

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

    #Save activity definition to DB
    def save_activity_definition_to_db(self,act_def_type, intType):
        created = True
        try:
            self.activity.activity_definition
            created = False
        except:
            actdef = models.activity_definition(activity_definition_type=act_def_type,
                  interactionType=intType, activity=self.activity)
            actdef.save()

        if created:
            log_message(self.log_dict, "Activity definition saved to database",
                __name__, self.save_activity_definition_to_db.__name__)            
        else:
            log_message(self.log_dict, "Activity definition retrieved from database",
                __name__,self.save_activity_definition_to_db.__name__)            

        return created

    def check_activity_definition_value(self, new_name_value, existing_name_value):
        return new_name_value == existing_name_value

    def update_activity_name_and_description(self, new_activity, existing_activity):
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
            the_definition = new_activity
            
            try:
                the_names = the_definition['name']
            except KeyError:
                err_msg = "Activity definition has no name attribute"
                log_message(self.log_dict, err_msg, __name__, self.update_activity_name_and_description.__name__, True)
                update_parent_log_status(self.log_dict, 400)
                raise exceptions.ParamError(err_msg)
            for new_name_lang_map in the_names.items():
                # If there is already an entry in the same language
                if new_name_lang_map[0] in existing_name_key_set:
                    name_same = True                    
                    # Retrieve existing language map with same key (all in the existing act_def)
                    existing_lang_map = existing_act_def.name.get(key=new_name_lang_map[0])
                    name_same = self.check_activity_definition_value(new_name_lang_map[1], existing_lang_map.value)
                    # If names are different, update the language map with the new name
                    if not name_same:
                        existing_act_def.name.filter(id=existing_lang_map.id).update(value=new_name_lang_map[1])
                # Else it's a new lang map and needs added
                else:
                    existing_act_def.name.create(key=new_name_lang_map[0], value=new_name_lang_map[1])
                    existing_act_def.save()                    

            # Loop through all language maps in description
            try:
                the_descriptions = the_definition['description']
            except KeyError:
                err_msg = "Activity definition has no description attribute"
                log_message(self.log_dict, err_msg, __name__, self.update_activity_name_and_description.__name__, True)
                update_parent_log_status(self.log_dict, 400)
                raise exceptions.ParamError()
            for new_desc_lang_map in the_descriptions.items():
                # If there is already an entry in the same language
                if new_desc_lang_map[0] in existing_desc_key_set:
                    desc_same = False
                    # Retrieve existing language map with same key (all in the existing act_def)
                    existing_lang_map = existing_act_def.description.get(key=new_desc_lang_map[0])
                    desc_same = self.check_activity_definition_value(new_desc_lang_map[1], existing_lang_map.value)
                    # If desc are different, update the langage map with the new desc
                    if not desc_same:
                        existing_act_def.description.filter(id=existing_lang_map.id).update(value=new_desc_lang_map[1])
                else:
                    existing_act_def.description.create(key=new_desc_lang_map[0], value=new_desc_lang_map[1])
                    existing_act_def.save()                    

    #Once JSON is verified, populate the activity objects
    def populate(self, the_object):        
        #Must include activity_id - set object's activity_id
        try:
            activity_id = the_object['id']
        except KeyError:
            err_msg = "No id provided, must provide 'id' field"
            log_message(self.log_dict, err_msg, __name__, self.populate.__name__, True) 
            update_parent_log_status(self.log_dict, 400)          
            raise exceptions.ParamError(err_msg)

        # If allowed to define activities-create or get the global version
        if self.define:
            self.activity, act_created = models.activity.objects.get_or_create(activity_id=activity_id,
                global_representation=True)
        else:
            # Not allowed to create global version b/c don't have define permissions
            self.activity = models.activity(activity_id=activity_id, global_representation=False)
            self.activity.save()
            act_created = False
        if act_created: 
            log_message(self.log_dict, "Populating Activity - created Activity in database", __name__, self.populate.__name__)            
            if self.auth:
                self.activity.authoritative = self.auth
                self.activity.save()
        else:
            log_message(self.log_dict, "Populating Activity - retrieved Activity from database", __name__, self.populate.__name__)            

        valid_schema = False
        xml_data = {}
        
        #Try to grab XML from ID if no other JSON is provided - since it won't have a definition it's not a link
        #therefore it can be allowed to not resolve and will just return an empty dictionary
        if not 'definition' in the_object.keys():
            xml_data = self.validateID(activity_id)

            #If the ID validated against the XML schema then proceed with populating the definition with the info
            #from the XML - else just save the activity (someone sent in an ID that doesn't resolve and an objectType
            #with no other data)                
            if xml_data:
                self.populate_definition(xml_data, act_created)
        
        #Definition is provided
        else:
            self.validate_definition(the_object, act_created)

    def validate_definition(self, the_object, act_created):
        activity_definition = the_object['definition']
        activity_id = self.activity.activity_id
        #Verify the given activity_id resolves if it is a link (has to resolve if link) 
        xml_data = {}
        try:
            if activity_definition['type'] == 'link':
                try:
                    Activity.validator(activity_id)
                except ValidationError, e:
                    if act_created:
                        self.activity.delete()
                        self.activity = None
                    err_msg = str(e)    
                    log_message(self.log_dict, err_msg, __name__, self.validate_definition.__name__, True) 
                    update_parent_log_status(self.log_dict, 400)                   
                    raise exceptions.ParamError(err_msg)
            else:
                #Type is not a link - it can be allowed to not resolve and will just return an empty dictionary    
                #If activity is not a link, the ID either must not resolve or validate against metadata schema
                xml_data = self.validateID(activity_id)
        except KeyError:
            if act_created:
                self.activity.delete()
                self.activity = None
            err_msg = "Activity definition type is missing or malformed"
            log_message(self.log_dict, err_msg, __name__, self.validate_definition.__name__, True)
            update_parent_log_status(self.log_dict, 400)
            raise exceptions.ParamError(err_msg)
        
        #If the returned data is not empty, it overrides any JSON data sent in
        if xml_data:
            activity_definition = xml_data
        #If the URL did not resolve and is not type link, it will use the JSON data provided
        self.populate_definition(activity_definition, act_created)
        
    # Save language map object for activity definition name or description
    def save_lang_map(self, lang_map, parent):
        language_map = models.LanguageMap(key = lang_map[0], value = lang_map[1], content_object=parent)       
        language_map.save()        
        return language_map

    def validate_cmi_interaction(self, act_def, act_created):
        interaction_flag = None
        scormInteractionTypes = ['true-false', 'choice', 'fill-in', 'long-fill-in',
                                 'matching', 'performance', 'sequencing', 'likert', 'numeric',
                                 'other']
    
        #Check if valid SCORM interactionType
        if act_def['interactionType'] not in scormInteractionTypes:
            if act_created:
                self.activity.delete()
                self.activity = None
            err_msg = "Activity definition interactionType not valid"
            log_message(self.log_dict, err_msg, __name__, self.validate_cmi_interaction.__name__, True)
            update_parent_log_status(self.log_dict, 400)
            raise exceptions.ParamError(err_msg)

        #Must have correctResponsesPattern if they have a valid interactionType
        try:
            act_def['correctResponsesPattern']  
        except KeyError: 
            if act_created:
                self.activity.delete()
                self.activity = None   
            err_msg = "Activity definition missing correctResponsesPattern"
            log_message(self.log_dict, err_msg, __name__, self.validate_cmi_interaction.__name__, True)
            update_parent_log_status(self.log_dict, 400)
            raise exceptions.ParamError(err_msg)    

        #Multiple choice and sequencing must have choices
        if act_def['interactionType'] == 'choice' or \
            act_def['interactionType'] == 'sequencing':
                try:
                    act_def['choices']
                except KeyError:
                    if act_created:
                        self.activity.delete()
                        self.activity = None
                    err_msg = "Activity definition missing choices"
                    log_message(self.log_dict, err_msg, __name__, self.validate_cmi_interaction.__name__, True)
                    update_parent_log_status(self.log_dict, 400)
                    raise exceptions.ParamError(err_msg)
                interaction_flag = 'choices' 

        #Matching must have both source and target
        elif act_def['interactionType'] == 'matching':
            try:
                act_def['source']
                act_def['target']
            except KeyError:
                if act_created:
                    self.activity.delete()
                    self.activity = None
                err_msg = "Activity definition missing source/target for matching"
                log_message(self.log_dict, err_msg, __name__, self.validate_cmi_interaction.__name__, True)
                update_parent_log_status(self.log_dict, 400)
                raise exceptions.ParamError(err_msg)
            interaction_flag = 'source'

        #Performance must have steps
        elif act_def['interactionType'] == 'performance':
            try:
                act_def['steps']
            except KeyError:
                if act_created:
                    self.activity.delete()
                    self.activity = None
                err_msg = "Activity definition missing steps for performance"
                log_message(self.log_dict, err_msg, __name__, self.validate_cmi_interaction.__name__, True)
                update_parent_log_status(self.log_dict, 400)
                raise exceptions.ParamError(err_msg)    
            interaction_flag = 'steps'

        #Likert must have scale
        elif act_def['interactionType'] == 'likert':
            try:
                act_def['scale']
            except KeyError:
                if act_created:
                    self.activity.delete()
                    self.activity = None
                err_msg = "Activity definition missing scale for likert"
                log_message(self.log_dict, err_msg, __name__, self.validate_cmi_interaction.__name__, True)
                update_parent_log_status(self.log_dict, 400)
                raise exceptions.ParamError(err_msg)
            interaction_flag = 'scale'
        return interaction_flag

    #Populate definition either from JSON or validated XML
    def populate_definition(self, act_def, act_created):
        log_message(self.log_dict, "Populating activity definition", __name__, self.populate_definition.__name__)
        # only update existing def stuff if request has authority to do so
        if not act_created and (self.activity.authoritative is not None and self.activity.authoritative != self.auth):
            err_msg = "This ActivityID already exists, and you do not have the correct authority to create or update it."
            log_message(self.log_dict, err_msg, __name__, self.populate_definition.__name__, True)
            update_parent_log_status(self.log_dict, 403)
            raise exceptions.Forbidden(err_msg)

        #Check if all activity definition required fields are present - deletes existing activity model
        #if error with required activity definition fields
        for k in Activity.ADRFs:
            if k not in act_def.keys() and k != 'extensions':
                if act_created:
                    self.activity.delete()
                    self.activity = None
                err_msg = "Activity definition error with key: %s" % k
                log_message(self.log_dict, err_msg, __name__, self.populate_definition.__name__, True)
                update_parent_log_status(self.log_dict, 400)
                raise exceptions.ParamError(err_msg)

        #If the type is cmi.interaction, have to check interactionType
        interaction_flag = None
        if act_def['type'] == 'http://www.adlnet.gov/experienceapi/activity-types/cmi.interaction':
            interaction_flag = self.validate_cmi_interaction(act_def, act_created)

        act_def_created = self.save_activity_definition_to_db(act_def['type'], act_def.get('interactionType', None))

        if not act_created: 
            if self.activity.authoritative is None or self.activity.authoritative == self.auth:
                # Update name and desc if needed
                self.update_activity_name_and_description(act_def, self.activity)
            else:
                err_msg = "This ActivityID already exists, and you do not have the correct authority to create or update it."
                log_message(self.log_dict, err_msg, __name__, self.populate_definition.__name__, True)
                update_parent_log_status(self.log_dict, 403)
                raise exceptions.Forbidden(err_msg)
        else:
            # If created and have permisson to (re)define activities
            if self.define:
                # Save activity definition name and description
                for name_lang_map in act_def['name'].items():
                    if isinstance(name_lang_map, tuple):
                        n = models.name_lang(key=name_lang_map[0],
                                      value=name_lang_map[1],
                                      content_object=self.activity.activity_definition)
                        n.save()
                    else:
                        err_msg = "Activity with id %s has a name that is not a language map" % self.activity.activity_id
                        log_message(self.log_dict, err_msg, __name__, self.populate_definition.__name__, True)
                        update_parent_log_status(self.log_dict, 400)
                        raise exceptions.ParamError(err_msg)

                for desc_lang_map in act_def['description'].items():
                    if isinstance(desc_lang_map, tuple):
                        d = models.desc_lang(key=desc_lang_map[0],
                                      value=desc_lang_map[1],
                                      content_object=self.activity.activity_definition)
                        d.save()
                    else:
                        err_msg = "Activity with id %s has a description that is not a language map" % self.activity.activity_id
                        log_message(self.log_dict, err_msg, __name__, self.populate_definition.__name__, True) 
                        update_parent_log_status(self.log_dict, 400)                   
                        raise exceptions.ParamError(err_msg)
        
        #If there is a correctResponsesPattern then save the pattern
        if act_def_created and 'correctResponsesPattern' in act_def.keys():
            self.populate_correctResponsesPattern(act_def, interaction_flag)
        #See if activity definition has extensions
        if act_def_created and 'extensions' in act_def.keys():
            self.populate_extensions(act_def) 

    def populate_correctResponsesPattern(self, act_def, interactionFlag):
        crp = models.activity_def_correctresponsespattern(activity_definition=self.activity.activity_definition)
        crp.save()

        log_message(self.log_dict, "Populating correct responses pattern", __name__, self.populate_correctResponsesPattern.__name__)                    

        #For each answer in the pattern save it
        for i in act_def['correctResponsesPattern']:
            answer = models.correctresponsespattern_answer(answer=i, correctresponsespattern=crp)
            answer.save()

        #Depending on which type of interaction, save the unique fields accordingly
        if interactionFlag == 'choices' or interactionFlag == 'sequencing':
            for c in act_def['choices']:
                choice = models.activity_definition_choice(choice_id=c['id'], activity_definition=self.activity.activity_definition)
                choice.save()
                #Save description as string, not a dictionary
                for desc_lang_map in c['description'].items():
                    if isinstance(desc_lang_map, tuple):
                        lang_map = self.save_lang_map(desc_lang_map, choice)
                        choice.save()
                    else:
                        choice.delete()
                        err_msg = "Choice description must be a language map"
                        log_message(self.log_dict, err_msg, __name__, self.populate_correctResponsesPattern.__name__, True)  
                        update_parent_log_status(self.log_dict, 400)                  
                        raise exceptions.ParamError(err_msg)

        elif interactionFlag == 'scale':
            for s in act_def['scale']:
                scale = models.activity_definition_scale(scale_id=s['id'], activity_definition=self.activity.activity_definition)        
                scale.save()
                # Save description as string, not a dictionary
                for desc_lang_map in s['description'].items():
                    if isinstance(desc_lang_map, tuple):
                        lang_map = self.save_lang_map(desc_lang_map, scale)
                        scale.save()
                    else:
                        scale.delete()
                        err_msg = "Scale description must be a language map"
                        log_message(self.log_dict, err_msg, __name__, self.populate_correctResponsesPattern.__name__, True) 
                        update_parent_log_status(self.log_dict, 400)                   
                        raise exceptions.ParamError(err_msg)

        elif interactionFlag == 'steps':
            for s in act_def['steps']:
                step = models.activity_definition_step(step_id=s['id'], activity_definition=self.activity.activity_definition)
                step.save()
                #Save description as string, not a dictionary
                for desc_lang_map in s['description'].items():
                    if isinstance(desc_lang_map, tuple):
                        lang_map = self.save_lang_map(desc_lang_map, step)
                        step.save()
                    else:
                        step.delete()
                        err_msg = "Step description must be a language map"
                        log_message(self.log_dict, err_msg, __name__, self.populate_correctResponsesPattern.__name__, True) 
                        update_parent_log_status(self.log_dict, 400)                   
                        raise exceptions.ParamError(err_msg)  

        elif interactionFlag == 'source':
            for s in act_def['source']:
                source = models.activity_definition_source(source_id=s['id'], activity_definition=self.activity.activity_definition)
                source.save()                        
                #Save description as string, not a dictionary
                for desc_lang_map in s['description'].items():
                    if isinstance(desc_lang_map, tuple):
                        lang_map = self.save_lang_map(desc_lang_map, source)
                        source.save()
                    else:
                        source.delete()
                        err_msg = "Source description must be a language map"
                        log_message(self.log_dict, err_msg, __name__, self.populate_correctResponsesPattern.__name__, True) 
                        update_parent_log_status(self.log_dict, 400)                   
                        raise exceptions.ParamError(err_msg)

            for t in act_def['target']:
                target = models.activity_definition_target(target_id=t['id'], activity_definition=self.activity.activity_definition)
                target.save()
                #Save description as string, not a dictionary
                for desc_lang_map in t['description'].items():
                    if isinstance(desc_lang_map, tuple):
                        lang_map = self.save_lang_map(desc_lang_map, target)
                        target.save()
                    else:
                        target.delete()
                        err_msg = "Target description must be a language map"
                        log_message(self.log_dict, err_msg, __name__, self.populate_correctResponsesPattern.__name__, True) 
                        update_parent_log_status(self.log_dict, 400)                   
                        raise exceptions.ParamError(err_msg)

    def populate_extensions(self, act_def):
        for k, v in act_def['extensions'].items():
            if not uri.validate_uri(k):
                err_msg = "Extension ID %s is not a valid URI" % k
                log_message(self.log_dict, err_msg, __name__, self.populate_extensions.__name__, True) 
                update_parent_log_status(self.log_dict, 400)                   
                raise exceptions.ParamError(err_msg)

            act_def_ext = models.extensions(key=k, value=v,
                content_object=self.activity.activity_definition)
            act_def_ext.save()    
