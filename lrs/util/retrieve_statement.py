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
import ast

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
                activity = models.activity.objects.get(activity_id=objectData['id'])
                if activity:
                    obj = activity
            except models.activity.DoesNotExist:
                pass # no object found
        # If type is not an activity then it must be an agent
        elif objectData['objectType'].lower() == 'agent':
            try:
                agent = Agent.Agent(json.dumps(objectData)).agent
                if agent:
                    obj = agent
            except models.IDNotFoundError:
                pass # no stmt_object filter added
        elif objectData['objectType'].lower() == 'statementref':
            try:
                stmt_ref = models.StatementRef.objects.get(ref_id=objectData['id'])
                if stmt_ref:
                    obj = stmt_ref
            except models.StatementRef.DoesNotExist:
                pass
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
    return models.statement.objects.filter(**args).order_by(stored_param)

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
    if 'object' in the_dict:
        objectData = the_dict['object']
        obj = parse_incoming_object(objectData, args)
        if obj:
            args['stmt_object'] = obj

    # If searching by verb
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
    for stmt in stmt_list:
        st = Statement.Statement(statement_id=stmt.statement_id, get=True, auth=user)
        full_stmt_list.append(st.get_full_statement_json(sparse, language))
    return full_stmt_list

def createCacheKey(stmt_list):
    # Create unique hash data to use for the cache key
    hash_data = []
    hash_data.append(str(datetime.now()))
    hash_data.append(str(stmt_list))

    # Create cache key from hashed data (always 32 digits)
    key = hashlib.md5(bencode.bencode(hash_data)).hexdigest()
    return key

def initialCacheReturn(stmt_list, encoded_list, req_dict, limit):
    # First time someone queries POST/GET
    result = {}
    stmt_pager = Paginator(stmt_list, limit)
 
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
    cache_list.append(limit)

    # Encode data
    encoded_info = pickle.dumps(cache_list)

    # Save encoded_dict in cache
    cache.set(cache_key,encoded_info)
    # Return first page of results
    stmts = stmt_pager.page(1).object_list
    result['statements'] = stmts
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

    # Info is always cached as [query_dict, start_page, total_pages, limit]
    query_dict = decoded_info[0]
    start_page = decoded_info[1]
    limit = decoded_info[3]

    #Build list from query_dict
    stmt_list = complexGet(query_dict)

    # Build statementResult
    stmt_result = buildStatementResult(query_dict, stmt_list, req_id)
    return stmt_result

def buildStatementResult(req_dict, stmt_list, more_id=None, created=False, next_more_id=None):
    result = {}
    limit = None
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
        limit = query_info[3]
        current_page = start_page + 1
        # If that was the last page to display then just return the remaining stmts
        if current_page == total_pages:
            stmt_pager = Paginator(stmt_list, limit)
            result['statements'] = stmt_pager.page(current_page).object_list
            result['more'] = ''
            # Set current page back for when someone hits the URL again
            query_info[1] = query_info[1] - 1
            encoded_list = pickle.dumps(query_info)
            cache.set(more_id, encoded_list)
            return result
        # There are more pages to display
        else:
            stmt_pager = Paginator(stmt_list, limit)
            # Create cache key from hashed data (always 32 digits)
            cache_key = createCacheKey(stmt_list)
            # Set result to have selected page of stmts and more endpoing
            result['statements'] = stmt_pager.page(current_page).object_list
            result['more'] = MORE_ENDPOINT + cache_key
            more_cache_list = []
            # Increment next page
            start_page = query_info[1] + 1
            more_cache_list.append(req_dict)
            more_cache_list.append(start_page)
            more_cache_list.append(query_info[2])
            more_cache_list.append(limit)
            # Encode info
            encoded_list = pickle.dumps(more_cache_list)
            cache.set(cache_key, encoded_list)
            return result
    # List will only be larger first time - getStatementRequest should truncate rest of results
    # of more URLs.
    if not limit:
        try:
            limit = int(req_dict['limit'])
        except KeyError:
            try:
                bdy = req_dict['body']
                if isinstance(bdy, basestring):
                    try:
                        bdy = ast.literal_eval(bdy)
                    except:
                        bdy = json.loads(bdy)
                limit = int(bdy['limit'])
            except:
                limit = None
        if not limit or limit > settings.SERVER_STMT_LIMIT:
            limit = settings.SERVER_STMT_LIMIT

    if statement_amount > limit:
        result = initialCacheReturn(stmt_list, encoded_list, req_dict, limit)
    # Just provide statements since the list is under the limit
    else:
        result['statements'] = stmt_list
        result['more'] = ''
    return result

