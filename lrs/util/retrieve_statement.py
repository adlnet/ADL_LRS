from lrs import models
from django.core.cache import cache
from lrs.objects import Agent, Statement
from datetime import datetime
from django.conf import settings
from django.core.paginator import Paginator
import bencode
import pytz
import hashlib
import json
import pickle
import ast
import pdb

import pprint

MORE_ENDPOINT = '/TCAPI/statements/more/'

def convertToUTC(timestr):
    # Strip off TZ info
    timestr = timestr[:timestr.rfind('+')]
    
    # Convert to date_object (directive for parsing TZ out is buggy, which is why we do it this way)
    date_object = datetime.strptime(timestr, '%Y-%m-%dT%H:%M:%S.%f')
    
    # Localize TZ to UTC since everything is being stored in DB as UTC
    date_object = pytz.timezone("UTC").localize(date_object)
    return date_object

# def retrieve_result(objectData):
#     if 'score' in objectData:
#         objectData['score'] = models.score.objects.filter(**objectData['score'])[0]
#     try:
#         result = models.result.objects.filter(**objectData)
#     except models.result.DoesNotExist:
#         result = None
#     return result

def retrieve_context(objectData):
    # pdb.set_trace()
    # if 'instructor' in objectData:
    #     objectData['instructor'] = models.agent.objects.filter(**objectData['instructor'])[0]

    # if 'team' in objectData:
    #     objectData['team'] = models.group.objects.filter(**objectData['team'])[0]

    # if 'statement' in objectData:
    #     objectData['statement'] = models.StatementRef.filter(ref_id=objectData['statement'['id']])[0]

    # if 'contextActivities' in objectData:
    #     del objectData['contextActivities']

    if 'registration' in objectData:
        context = models.context.objects.get(registration=objectData['registration'])
    return context


def parse_incoming_object(objectData, args):
    # If object is not dict, try to load as one
    # pdb.set_trace()
    obj = None
    if not type(objectData) is dict:
        try:
            objectData = json.loads(objectData)
        except Exception, e:
            try:
                objectData = json.loads(objectData.replace("'",'"'))
            except Exception, e:
                objectData = ast.literal_eval(objectData)
                
    # Check the objectType
    if 'objectType' in objectData:
        # If type is activity try go retrieve object
        if objectData['objectType'].lower() == 'activity':
            try:
                activity = models.activity.objects.filter(activity_id=objectData['id'])[0]
                # If there is an activity set it to the found one, else it's empty
                if activity:
                    # args['stmt_object'] = activity
                    obj = activity
            except models.activity.DoesNotExist:
                pass # no object found
        # If type is not an activity then it must be an agent
        elif objectData['objectType'].lower() == 'agent':
            try:
                agent = Agent.Agent(json.dumps(objectData)).agent
                if agent:
                    # args['stmt_object'] = agent
                    obj = agent
            except models.IDNotFoundError:
                pass # no stmt_object filter added
        elif objectData['objectType'].lower() == 'substatement':
            # pdb.set_trace()
            sub_args = {}
            if 'verb' in objectData:
                verb_id = objectData['verb']['id']
                try:
                    sub_args['verb'] = models.Verb.objects.get(verb_id=verb_id)
                except models.Verb.DoesNotExist:
                    pass # no verb filter added                

            if 'timestamp' in objectData:
                sub_args['timestamp'] = objectData['timestamp']

            # if 'result' in objectData:
            #     result = retrieve_result(objectData['result'])
            #     if result:
            #         sub_args['result'] = result

            if 'context' in objectData:
                context = retrieve_context(objectData['context'])
                if context:
                    sub_args['context'] = context

            if 'actor' in objectData:
                actor = parse_incoming_actor(objectData['actor'])
                if actor:
                    sub_args['actor'] = actor

            if 'object' in objectData:
                stmt_object = parse_incoming_object(objectData['object'], sub_args)
                sub_args['stmt_object'] = stmt_object

            try:
                sub = models.SubStatement.objects.get(**sub_args)
                if sub:
                    # args['stmt_object'] = sub
                    obj = sub
            except Exception, e:
                pass # no object filter added
    # Default to activity
    else:
        try:
            activity = models.activity.objects.get(activity_id=objectData['id'])
            if activity:
                # args['stmt_object'] = activity
                obj = activity
        except Exception, e:
            pass
    return obj

def parse_incoming_actor(actorData):
    actor = None
    if not type(actorData) is dict:
        try:
            actorData = json.loads(actorData)
        except Exception, e:
            actorData = json.loads(actorData.replace("'",'"'))
    try:
        agent = Agent.Agent(json.dumps(actorData)).agent
        # args['actor'] = agent
        actor = agent
    except models.IDNotFoundError:
        pass # no actor filter added
    return actor

def parse_incoming_instructor(instData):
    inst = None
    if not type(instData) is dict:
        try:
            instData = json.loads(instData)
        except Exception, e:
            instData = json.loads(instData.replace("'",'"'))        
    try:
        instructor = Agent.Agent(json.dumps(instData)).agent                 
        if instructor:
            cntxList = models.context.objects.filter(instructor=instructor)
            # args['context__in'] = cntxList
            inst = cntxList
    except models.IDNotFoundError:
        pass # no actor filter added
    return inst

def retrieve_stmts_from_db(the_dict, limit, stored_param, args):
    # If no limit and no retrieving paging results from buildStatementResult
    if limit == 0 and 'more_start' not in the_dict:
        # Retrieve statements from DB
        stmt_list = models.statement.objects.filter(**args).order_by(stored_param)
    # If need paging results (limit doesn't matter here since paging will handle it)
    elif 'more_start' in the_dict:
        # If more start then start at that page point
        start = int(the_dict['more_start'])
        stmt_list = models.statement.objects.filter(**args).order_by(stored_param)[start:]
    # Limiting results since limit won't be 0
    else:
        stmt_list = models.statement.objects.filter(**args).order_by(stored_param)[:limit]
    return stmt_list

def complexGet(req_dict):


    args = {}
    language = None
    # Set language if one
    if 'language' in req_dict:
        language = req_dict['language']
    
    user = None
    if 'user' in req_dict:
        user = req_dict['user']

    # Parse out params into single dict
    try:
        the_dict = req_dict['body']
        if isinstance(the_dict, str):
            try:
                the_dict = ast.literal_eval(the_dict)
            except:
                the_dict = json.loads(the_dict)
    except KeyError:
        the_dict = req_dict
    
    # If want ordered by ascending
    if 'ascending' in the_dict:
        if the_dict['ascending']:
            ascending = True
    # Cycle through the_dict and set since and until params
    for k,v in the_dict.items():
        if k.lower() == 'since':
            date_object = convertToUTC(v)
            args['stored__gt'] = date_object
        elif k.lower() == 'until':
            date_object = convertToUTC(v)
            args['stored__lte'] = date_object   
    
    # If searching by activity or actor
    # pdb.set_trace()
    if 'object' in the_dict:
        objectData = the_dict['object']
        obj = parse_incoming_object(objectData, args)
        if obj:
            args['stmt_object'] = obj

    # If searching by verb
    # pdb.set_trace()
    if 'verb' in the_dict:
        verb_id = the_dict['verb']
        verb = models.Verb.objects.filter(verb_id=verb_id)
        if verb:
            args['verb'] = verb


    # If searching by registration
    if 'registration' in the_dict:
        uuid = str(the_dict['registration'])
        cntx = models.context.objects.get(registration=uuid)
        args['context'] = cntx
    
    # If searching by actor
    if 'actor' in the_dict:
        actorData = the_dict['actor']
        actor = parse_incoming_actor(actorData)
        if actor:
            args['actor'] = actor

    # If searching by instructor
    if 'instructor' in the_dict:
        instData = the_dict['instructor']
        inst = parse_incoming_instructor(instData)
        if inst:
            args['context__in'] = inst
    
    # there's a default of true
    if not 'authoritative' in the_dict or str(the_dict['authoritative']).upper() == 'TRUE':
        args['authoritative'] = True   

    limit = 0    
    # If want results limited
    if 'limit' in the_dict:
        limit = int(the_dict['limit'])
   
    sparse = True    
    # If want sparse results
    if 'sparse' in the_dict:
        if not type(the_dict['sparse']) is bool:
            if the_dict['sparse'].lower() == 'false':
                sparse = False
        else:
            sparse = the_dict['sparse']
    
    ascending = False    
    # Set stored param based on ascending
    if ascending:
        stored_param = 'stored'
    else:
        stored_param = '-stored'
    stmt_list = retrieve_stmts_from_db(the_dict, limit, stored_param, args)
    full_stmt_list = []
    # For each stmt convert to our Statement class and retrieve all json
    # pdb.set_trace()
    for stmt in stmt_list:
        stmt = Statement.Statement(statement_id=stmt.statement_id, get=True, auth=user)
        full_stmt_list.append(stmt.get_full_statement_json(sparse, language))
    return full_stmt_list

def createCacheKey(stmt_list):
    # Create unique hash data to use for the cache key
    hash_data = []
    hash_data.append(str(datetime.now()))
    hash_data.append(str(stmt_list))

    # Create cache key from hashed data (always 32 digits)
    key = hashlib.md5(bencode.bencode(hash_data)).hexdigest()
    return key

def initialCacheReturn(stmt_list, encoded_list, req_dict):
    # First time someone queries POST/GET
    result = {}
    stmt_pager = Paginator(stmt_list, settings.SERVER_STMT_LIMIT)
 
    cache_list = []
    
    # Always going to start on page 1
    current_page = 1
    total_pages = stmt_pager.num_pages
    
    # Create cache key from hashed data (always 32 digits)
    cache_key = createCacheKey(stmt_list)

    # Add data to cache
    cache_list.append(req_dict)
    cache_list.append(current_page)
    cache_list.append(total_pages)

    # Encode data
    encoded_info = pickle.dumps(cache_list)

    # Save encoded_dict in cache
    cache.set(cache_key,encoded_info)

    # Return first page of results
    result['statements'] = stmt_pager.page(1).object_list
    result['more'] = MORE_ENDPOINT + cache_key        
    return result

def getStatementRequest(req_id):  
    # Retrieve encoded info for statements
    encoded_info = cache.get(req_id)

    # Could have expired or never existed
    if not encoded_info:
        return ['List does not exist - may have expired after 24 hours']

    # Decode info
    decoded_info = pickle.loads(encoded_info)

    # Info is always cached as [query_dict, start_page, total_pages]
    query_dict = decoded_info[0]
    start_page = decoded_info[1]

    # Set 'more_start' to slice query from where you left off 
    query_dict['more_start'] = start_page * settings.SERVER_STMT_LIMIT

    #Build list from query_dict
    stmt_list = complexGet(query_dict)

    # Build statementResult
    stmt_result = buildStatementResult(query_dict, stmt_list, req_id)
    return stmt_result

def buildStatementResult(req_dict, stmt_list, more_id=None, created=False, next_more_id=None):
    result = {}
    # Get length of stmt list
    statement_amount = len(stmt_list)  
    # See if something is already stored in cache
    encoded_list = cache.get(more_id)
    # If there is a more_id (means this is being called from getStatementRequest)
    if more_id:
        more_cache_list = []
        # Get query_info and there should always be an encoded_list if there is a more_id
        query_info = pickle.loads(encoded_list)
        # Get page info 
        start_page = query_info[1]
        total_pages = query_info[2]
        next_page = start_page + 1
        # If that was the last page to display then just return the remaining stmts
        if next_page == total_pages:
            result['statements'] = stmt_list
            result['more'] = ''
            # Set current page back for when someone hits the URL again
            query_info[1] = query_info[1] - 1
            encoded_list = pickle.dumps(query_info)
            cache.set(more_id, encoded_list)
            return result
        # There are more pages to display
        else:
            stmt_pager = Paginator(stmt_list, settings.SERVER_STMT_LIMIT)
            # Create cache key from hashed data (always 32 digits)
            cache_key = createCacheKey(stmt_list)
            # Set result to have selected page of stmts and more endpoing
            result['statement'] = stmt_pager.page(start_page).object_list
            result['more'] = MORE_ENDPOINT + cache_key
            more_cache_list = []
            # Increment next page
            start_page = query_info[1] + 1
            more_cache_list.append(req_dict)
            more_cache_list.append(start_page)
            more_cache_list.append(query_info[2])
            # Encode info
            encoded_list = pickle.dumps(more_cache_list)
            cache.set(cache_key, encoded_list)
            return result
    # List will only be larger first time - getStatementRequest should truncate rest of results
    # of more URLs.
    if statement_amount > settings.SERVER_STMT_LIMIT:
        result = initialCacheReturn(stmt_list, encoded_list, req_dict)
    # Just provide statements since the list is under the limit
    else:
        result['statements'] = stmt_list
        result['more'] = ''
    return result

