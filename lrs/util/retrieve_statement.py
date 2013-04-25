import bencode
import hashlib
import json
import pickle
from datetime import datetime
from django.core.cache import cache
from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Q
from itertools import chain
from lrs import models
from lrs.objects import Agent, Statement
from lrs.util import convert_to_utc, convert_to_dict
import pdb

MORE_ENDPOINT = '/XAPI/statements/more/'

def parse_incoming_object(obj_data, args):
    # If object is not dict, try to load as one. Even when parsing body in req_parse-data in object key
    # is not converted
    obj = None
    if not type(obj_data) is dict:
        object_data = convert_to_dict(obj_data)
    else:
        object_data = obj_data
    # If it's activity, since there could be multiple activities with the same ID, we want to return all
    # stmts that have any of those actIDs-do filter instead of get and check if ID is in the list
    activity = False
    # Check the objectType
    if 'objectType' in object_data:
        object_type = object_data['objectType'].lower()
        # If type is activity try go retrieve object
        if object_type == 'activity':
            activity = models.activity.objects.filter(activity_id=object_data['id'])
            # Have to filter activity since there can be 'local' activities with the same ID
            if activity:
                obj = activity
                activity = True
        # If type is not an activity then it must be an agent
        elif object_type == 'agent':
            try:
                agent = Agent.Agent(json.dumps(object_data)).agent
                if agent:
                    obj = agent
            except models.IDNotFoundError:
                pass # no stmt_object filter added
        elif object_type == 'statementref':
            try:
                stmt_ref = models.StatementRef.objects.get(ref_id=object_data['id'])
                if stmt_ref:
                    obj = stmt_ref
            except models.StatementRef.DoesNotExist:
                pass # no stmt_object filter added
    # Default to activity
    else:
        activity = models.activity.objects.filter(activity_id=object_data['id'])
        # Have to filter activity since there can be 'local' activities with the same ID
        if activity:
            obj = activity
            activity = True
    return obj, activity

def parse_incoming_actor(actor_data):
    actor = None
    if not type(actor_data) is dict:
        actor_data = convert_to_dict(actor_data)
    try:
        actor = Agent.Agent(actor_data).agent
    except models.IDNotFoundError:
        pass # no actor filter added
    return actor

def parse_incoming_instructor(inst_data):
    inst = None
    if not type(inst_data) is dict:
        inst_data = convert_to_dict(inst_data)
    try:
        instructor = Agent.Agent(inst_data).agent                 
        # If there is an instructor, filter contexts against it
        if instructor:
            cntx_list = models.context.objects.filter(instructor=instructor)
            inst = cntx_list
    except models.IDNotFoundError:
        pass # no instructor filter added
    return inst

def retrieve_stmts_from_db(the_dict, limit, stored_param, args):
    return models.statement.objects.filter(**args).order_by(stored_param)

def complex_get(req_dict):
    # tests if value is True or "true"
    bt = lambda x: x if type(x)==bool else x.lower()=="true"
    stmtset = models.statement.objects.filter(voided=False)
    # keep track if a filter other than time or sequence is used
    reffilter = False

    # Parse out params into single dict-GET data not in body
    try:
        the_dict = req_dict['body']
        if not isinstance(the_dict, dict):
            the_dict = convert_to_dict(the_dict)
    except KeyError:
        the_dict = req_dict

    sinceq = None
    if 'since' in the_dict:
        sinceq = Q(stored__gt=convert_to_utc(the_dict['since']))
        stmtset = stmtset.filter(sinceq)
    untilq = None
    if 'until' in the_dict:
        untilq = Q(stored__lte=convert_to_utc(the_dict['until']))
        stmtset = stmtset.filter(untilq)

    # For statements/read/mine oauth scope
    if 'statements_mine_only' in the_dict:
        stmtset = stmtset.filter(authority=the_dict['auth'])

    agentQ = Q()
    if 'agent' in the_dict:
        reffilter = True
        agent = None
        data = the_dict['agent']
        related = 'related_agents' in the_dict and bt(the_dict['related_agents'])
        
        if not type(data) is dict:
            data = convert_to_dict(data)
        
        try:
            agent = Agent.Agent(data).agent
            if agent.objectType == "Group":
                groups = []
            else:
                groups = agent.member.all()
            agentQ = Q(actor=agent)
            for g in groups:
                agentQ = agentQ | Q(actor=g)
            if related:
                me = chain([agent], groups)
                for a in me:
                    agentQ = agentQ | Q(stmt_object=a) | Q(authority=a) \
                          | Q(context__instructor=a) | Q(context__team=a) \
                          | Q(stmt_object__substatement__actor=a) \
                          | Q(stmt_object__substatement__stmt_object=a) \
                          | Q(stmt_object__substatement__context__instructor=a) \
                          | Q(stmt_object__substatement__context__team=a)       
        except models.IDNotFoundError:
            return[]     
    
    verbQ = Q()
    if 'verb' in req_dict:
        reffilter = True
        verbQ = Q(verb__verb_id=the_dict['verb'])
        
    # activity
    activityQ = Q()
    if 'activity' in the_dict:
        reffilter = True
        activityQ = Q(stmt_object__activity__activity_id=the_dict['activity'])
        if 'related_activities' in the_dict and bt(the_dict['related_activities']):
            activityQ = activityQ | Q(context__contextactivity__context_activity__activity_id=the_dict['activity']) \
                    | Q(stmt_object__substatement__stmt_object__activity__activity_id=the_dict['activity']) \
                    | Q(stmt_object__substatement__context__contextactivity__context_activity__activity_id=the_dict['activity'])


    registrationQ = Q()
    if 'registration' in the_dict:
        reffilter = True
        registrationQ = Q(context__registration=the_dict['registration'])

    format = the_dict['format']
    
    # attachments
    
    # Set language if one
    # pull from req_dict since language is from a header, not an arg 
    language = None
    if 'language' in req_dict:
        language = req_dict['language']

    # If want ordered by ascending
    stored_param = '-stored'
    if 'ascending' in the_dict and bt(the_dict['ascending']):
            stored_param = 'stored'

    stmtset = stmtset.filter(agentQ & verbQ & activityQ & registrationQ)
    # only find references when a filter other than
    # since, until, or limit was used 
    if reffilter:
        stmtset = findstmtrefs(stmtset.distinct(), sinceq, untilq)
    stmt_list = stmtset.order_by(stored_param)
    # For each stmt retrieve all json
    full_stmt_list = []
    full_stmt_list = [stmt.object_return(language, format) for stmt in stmt_list]
    return full_stmt_list

def findstmtrefs(stmtset, sinceq, untilq):
    if stmtset.count() == 0:
        return stmtset
    q = Q()
    for s in stmtset:
        q = q | Q(stmt_object__statementref__ref_id=s.statement_id)

    if sinceq and untilq:
        q = q & Q(sinceq, untilq)
    elif sinceq:
        q = q & sinceq
    elif untilq:
        q = q & untilq
    # finally weed out voided statements in this lookup
    q = q & Q(voided=False)
    return findstmtrefs(models.statement.objects.filter(q).distinct(), sinceq, untilq) | stmtset

def old_complex_get(req_dict):
    args = {}
    
    language = None
    # Set language if one
    if 'language' in req_dict:
        language = req_dict['language']
    
    user = None
    if 'user' in req_dict:
        user = req_dict['user']

    # Parse out params into single dict-GET data not in body
    try:
        the_dict = req_dict['body']
        if not isinstance(the_dict, dict):
            the_dict = convert_to_dict(the_dict)
    except KeyError:
        the_dict = req_dict

    # The ascending initilization statement here sometimes throws mysql warning, but needs to be here
    ascending = False    
    # If want ordered by ascending
    if 'ascending' in the_dict:
        if the_dict['ascending']:
            ascending = True

    # Cycle through the_dict and set since and until params
    for k,v in the_dict.items():
        if k.lower() == 'since':
            date_object = convert_to_utc(v)
            args['stored__gt'] = date_object
        elif k.lower() == 'until':
            date_object = convert_to_utc(v)
            args['stored__lte'] = date_object   
    
    # If searching by activity or actor
    if 'object' in the_dict:
        object_data = the_dict['object']
        obj, activity = parse_incoming_object(object_data, args)
        if obj and activity:
            args['stmt_object__in'] = obj
        elif obj and not activity:
            args['stmt_object'] = obj
        else:
            return []

    # If searching by verb
    if 'verb' in the_dict:
        verb_id = the_dict['verb']
        verb = models.Verb.objects.filter(verb_id=verb_id)
        if verb:
            args['verb'] = verb
        else:
            return []

    # If searching by registration
    if 'registration' in the_dict:
        uuid = str(the_dict['registration'])
        cntx = models.context.objects.filter(registration=uuid)
        if cntx:
            args['context'] = cntx
        else:
            return []

    # If searching by agent
    if 'agent' in the_dict:
        actor_data = the_dict['agent']
        agent = parse_incoming_actor(actor_data)
        if agent:
            args['actor'] = agent
        else:
            return []

    # If searching by instructor
    if 'instructor' in the_dict:
        inst_data = the_dict['instructor']
        inst = parse_incoming_instructor(inst_data)
        if inst:
            args['context__in'] = inst
        else:
            return []

    limit = 0    
    # If want results limited
    if 'limit' in the_dict:
        limit = int(the_dict['limit'])
   
    sparse = True    
    # If want sparse results
    if 'sparse' in the_dict:
        # If sparse input as string
        if not type(the_dict['sparse']) is bool:
            if the_dict['sparse'].lower() == 'false':
                sparse = False
        else:
            sparse = the_dict['sparse']

    # For statements/read/mine oauth scope
    if 'statements_mine_only' in the_dict:
        args['authority'] = the_dict['auth']

    # Set stored param based on ascending
    if ascending:
        stored_param = 'stored'
    else:
        stored_param = '-stored'

    # don't return voided statements
    args['voided'] = False        

    stmt_list = retrieve_stmts_from_db(the_dict, limit, stored_param, args)

    # For each stmt convert to our Statement class and retrieve all json
    full_stmt_list = []
    full_stmt_list = [stmt.object_return(sparse, language) for stmt in stmt_list]
    return full_stmt_list

def create_cache_key(stmt_list):
    # Create unique hash data to use for the cache key
    hash_data = []
    hash_data.append(str(datetime.now()))
    hash_data.append(str(stmt_list))

    # Create cache key from hashed data (always 32 digits)
    key = hashlib.md5(bencode.bencode(hash_data)).hexdigest()
    return key

def initial_cache_return(stmt_list, encoded_list, req_dict, limit):
    # First time someone queries POST/GET
    result = {}
    stmt_pager = Paginator(stmt_list, limit)
 
    cache_list = []
    
    # Always going to start on page 1
    current_page = 1
    total_pages = stmt_pager.num_pages
    # Create cache key from hashed data (always 32 digits)
    cache_key = create_cache_key(stmt_list)

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

def get_statement_request(req_id):  
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
    stmt_list = complex_get(query_dict)

    # Build statementResult
    stmt_result = build_statement_result(query_dict, stmt_list, req_id)
    return stmt_result

def set_limit(req_dict):
    limit = None
    if 'limit' in req_dict:
        limit = int(req_dict['limit'])
    elif 'body' in req_dict and 'limit' in req_dict['body']:
        limit = int(req_dict['body']['limit'])

    if not limit or limit > settings.SERVER_STMT_LIMIT:
        limit = settings.SERVER_STMT_LIMIT

    return limit

def build_statement_result(req_dict, stmt_list, more_id=None):
    result = {}
    limit = None
    # Get length of stmt list
    statement_amount = len(stmt_list)  
    # See if something is already stored in cache
    encoded_list = cache.get(more_id)
    # If there is a more_id (means this is being called from get_statement_request) this is not the initial request (someone is pinging the 'more' link)
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
            cache_key = create_cache_key(stmt_list)
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
    # If get to here, this is on the initial request
    # List will only be larger first time of more URLs. Limit can be set directly in request dict if 
    # a GET or in request dict body if a POST
    if not limit:
        limit = set_limit(req_dict)

    # If there are more than the limit, build the initial return
    if statement_amount > limit:
        result = initial_cache_return(stmt_list, encoded_list, req_dict, limit)
    # Just provide statements since the list is under the limit
    else:
        result['statements'] = stmt_list
        result['more'] = ''
    return result