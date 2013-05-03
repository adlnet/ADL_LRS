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
from lrs.objects import Agent
from lrs.util import convert_to_utc, convert_to_dict

MORE_ENDPOINT = '/XAPI/statements/more/'

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
    if 'format' in req_dict and req_dict['format'] == "canonical":
        if 'language' in req_dict:
            language = req_dict['language']
        else:
            language = settings.LANGUAGE_CODE

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