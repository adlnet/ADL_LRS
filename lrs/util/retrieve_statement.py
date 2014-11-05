import bencode
import hashlib
import json
from datetime import datetime
from itertools import chain

from django.core.cache import cache
from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Q

from util import convert_to_utc, convert_to_dict
from ..models import Statement, Agent
from ..objects.AgentManager import AgentManager
from ..exceptions import NotFound, IDNotFoundError

MORE_ENDPOINT = '/xapi/statements/more/'

def complex_get(param_dict, limit, language, format, attachments):
    # Tests if value is True or "true"
    voidQ = Q(voided=False)
    # keep track if a filter other than time or sequence is used
    reffilter = False

    sinceQ = Q()
    if 'since' in param_dict:
        sinceQ = Q(stored__gt=convert_to_utc(param_dict['since']))

    untilQ = Q()
    if 'until' in param_dict:
        untilQ = Q(stored__lte=convert_to_utc(param_dict['until']))

    # For statements/read/mine oauth scope
    authQ = Q()
    if 'auth' in param_dict and (param_dict['auth'] and 'statements_mine_only' in param_dict['auth']):
        q_auth = param_dict['auth']['authority']

        # If oauth - set authority to look for as the user
        if q_auth.oauth_identifier:
            authQ = Q(authority=q_auth) | Q(authority=q_auth.get_user_from_oauth_group())
        # Chain all of user's oauth clients as well
        else:
            oauth_clients = Agent.objects.filter(member__in=[q_auth])
            authQ = Q(authority=q_auth)
            for client in oauth_clients:
                authQ = authQ | Q(authority=client.get_user_from_oauth_group())

    agentQ = Q()
    if 'agent' in param_dict:
        reffilter = True
        agent = None
        data = param_dict['agent']
        related = 'related_agents' in param_dict and param_dict['related_agents']
        
        if not type(data) is dict:
            data = convert_to_dict(data)
        
        try:
            agent = AgentManager(data).Agent
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
                    agentQ = agentQ | Q(object_agent=a) | Q(authority=a) \
                          | Q(context_instructor=a) | Q(context_team=a) \
                          | Q(object_substatement__actor=a) \
                          | Q(object_substatement__object_agent=a) \
                          | Q(object_substatement__context_instructor=a) \
                          | Q(object_substatement__context_team=a)       
        except IDNotFoundError:
            return[]     
    
    verbQ = Q()
    if 'verb' in param_dict:
        reffilter = True
        verbQ = Q(verb__verb_id=param_dict['verb'])
        
    # activity
    activityQ = Q()
    if 'activity' in param_dict:
        reffilter = True
        activityQ = Q(object_activity__activity_id=param_dict['activity'])
        if 'related_activities' in param_dict and param_dict['related_activities']:
            activityQ = activityQ | Q(statementcontextactivity__context_activity__activity_id=param_dict['activity']) \
                    | Q(object_substatement__object_activity__activity_id=param_dict['activity']) \
                    | Q(object_substatement__substatementcontextactivity__context_activity__activity_id=param_dict['activity'])

    registrationQ = Q()
    if 'registration' in param_dict:
        reffilter = True
        registrationQ = Q(context_registration=param_dict['registration'])

    # If want ordered by ascending
    stored_param = '-stored'
    if 'ascending' in param_dict and param_dict['ascending']:
            stored_param = 'stored'

    stmtset = Statement.objects.filter(voidQ & untilQ & sinceQ & authQ & agentQ & verbQ & activityQ & registrationQ)
    
    # only find references when a filter other than
    # since, until, or limit was used 
    if reffilter:
        stmtset = findstmtrefs(stmtset.distinct(), sinceQ, untilQ)
    
    # Calculate limit of stmts to return
    return_limit = set_limit(limit)
    
    # If there are more stmts than the limit, need to break it up and return more id
    if stmtset.count() > return_limit:
        return initial_cache_return(stmtset, stored_param, return_limit, language, format, attachments)
    else:
        return create_stmt_result(stmtset, stored_param, language, format)

def create_stmt_result(stmt_set, stored, language, format):
    stmt_result = {}

    # blows up if the idlist is empty... so i gotta check for that
    idlist = stmt_set.values_list('id', flat=True)
    if idlist > 0:
        if format == 'exact':
            stmt_result = '{"statements": [%s], "more": ""}' % ",".join([json.dumps(stmt.full_statement) for stmt in \
                Statement.objects.filter(id__in=idlist).order_by(stored)])
        else:
            stmt_result['statements'] = [stmt.to_dict(language, format) for stmt in \
                Statement.objects.filter(id__in=idlist).order_by(stored)]
            stmt_result['more'] = ""
    else:
        stmt_result['statements'] = []
        stmt_result['more'] = ""
    return stmt_result

def findstmtrefs(stmtset, sinceQ, untilQ):
    if stmtset.count() == 0:
        return stmtset
    q = Q()
    for s in stmtset:
        q = q | Q(object_statementref__ref_id=s.statement_id)

    if sinceQ and untilQ:
        q = q & Q(sinceQ, untilQ)
    elif sinceQ:
        q = q & sinceQ
    elif untilQ:
        q = q & untilQ
    # finally weed out voided statements in this lookup
    q = q & Q(voided=False)
    return findstmtrefs(Statement.objects.filter(q).distinct(), sinceQ, untilQ) | stmtset

def create_cache_key(stmt_list):
    # Create unique hash data to use for the cache key
    hash_data = []
    hash_data.append(str(datetime.now()))
    hash_data.append(str(stmt_list))

    # Create cache key from hashed data (always 32 digits)
    key = hashlib.md5(bencode.bencode(hash_data)).hexdigest()
    return key

def initial_cache_return(stmt_list, stored, limit, language, format, attachments):
    # First time someone queries POST/GET
    result = {}
    cache_list = []
    
    cache_list.append([s for s in stmt_list.order_by(stored).values_list('id', flat=True)])
    stmt_pager = Paginator(cache_list[0], limit)
 
    # Always start on first page
    current_page = 1
    total_pages = stmt_pager.num_pages

    # Create cache key from hashed data (always 32 digits)
    cache_key = create_cache_key(cache_list[0])

    # Add data to cache
    cache_list.append(current_page)
    cache_list.append(total_pages)
    cache_list.append(limit)
    cache_list.append(attachments)
    cache_list.append(language)
    cache_list.append(format)
    cache_list.append(stored)
    
    # Encode data
    encoded_info = json.dumps(cache_list)

    # Save encoded_dict in cache
    cache.set(cache_key,encoded_info)

    # Return first page of results
    if format == 'exact':
        result = '{"statements": [%s], "more": "%s"}' % (",".join([json.dumps(stmt.full_statement) for stmt in \
                Statement.objects.filter(id__in=stmt_pager.page(1).object_list).order_by(stored)]), MORE_ENDPOINT + cache_key)
    else:
        result['statements'] = [stmt.to_dict(language, format) for stmt in \
                        Statement.objects.filter(id__in=stmt_pager.page(1).object_list).order_by(stored)]
        result['more'] = MORE_ENDPOINT + cache_key    
            
    return result

def set_limit(req_limit):
    if not req_limit or req_limit > settings.SERVER_STMT_LIMIT:
        req_limit = settings.SERVER_STMT_LIMIT
    return req_limit

def get_more_statement_request(req_id):  
    # Retrieve encoded info for statements
    encoded_info = cache.get(req_id)

    # Could have expired or never existed
    if not encoded_info:
        raise NotFound("List does not exist - may have expired after 24 hours")

    # Decode info
    decoded_info = json.loads(encoded_info)

    # Info is always cached as [stmt_list, start_page, total_pages, limit, attachments, language, format]
    stmt_list = decoded_info[0]
    start_page = decoded_info[1]
    total_pages = decoded_info[2]
    limit = decoded_info[3]
    attachments = decoded_info[4]
    language = decoded_info[5]
    format = decoded_info[6]
    stored = decoded_info[7]

    # Build statementResult
    stmt_result = build_statement_result(stmt_list, start_page, total_pages, limit, attachments, language, format, stored, req_id)
    return stmt_result, attachments

# Gets called from req_process after complex_get with list of django objects and also gets called from get_more_statement_request when
# more_id is used so list will be serialized
def build_statement_result(stmt_list, start_page, total_pages, limit, attachments, language, format, stored, more_id):
    result = {}
    current_page = start_page + 1
    # If that was the last page to display then just return the remaining stmts
    if current_page == total_pages:
        stmt_pager = Paginator(stmt_list, limit)       
        # Return first page of results
        if format == 'exact':
            result = '{"statements": [%s], "more": ""}' % ",".join([stmt.to_dict(language, format) for stmt in \
                Statement.objects.filter(id__in=stmt_pager.page(current_page).object_list).order_by(stored)])
        else:
            result['statements'] = [stmt.to_dict(language, format) for stmt in \
                    Statement.objects.filter(id__in=stmt_pager.page(current_page).object_list).order_by(stored)]
            result['more'] = ""
        # Set current page back for when someone hits the URL again
        current_page -= 1
        # Retrieve list stored in cache
        encoded_list = cache.get(more_id)
        # Decode info to set the current page back then encode again
        decoded_list = json.loads(encoded_list)
        decoded_list[1] = current_page
        encoded_list = json.dumps(decoded_list)
        cache.set(more_id, encoded_list)
    # There are more pages to display
    else:
        stmt_pager = Paginator(stmt_list, limit)
        # Create cache key from hashed data (always 32 digits)
        cache_key = create_cache_key(stmt_list)
        # Return first page of results
        if format == 'exact':
            result = '{"statements": [%s], "more": "%s"}' % (",".join([stmt.to_dict(language, format) for stmt in \
                Statement.objects.filter(id__in=stmt_pager.page(current_page).object_list).order_by(stored)]), MORE_ENDPOINT + cache_key)
        else:
            # Set result to have selected page of stmts and more endpoint
            result['statements'] = [stmt.to_dict(language, format) for stmt in \
                    Statement.objects.filter(id__in=stmt_pager.page(current_page).object_list).order_by(stored)]
            result['more'] = MORE_ENDPOINT + cache_key
        more_cache_list = []
        # Increment next page
        start_page = current_page
        more_cache_list.append(stmt_list)
        more_cache_list.append(start_page)
        more_cache_list.append(total_pages)
        more_cache_list.append(limit)
        more_cache_list.append(attachments)
        more_cache_list.append(language)
        more_cache_list.append(format)
        more_cache_list.append(stored)
        # Encode info
        encoded_list = json.dumps(more_cache_list)
        cache.set(cache_key, encoded_list)
    return result
