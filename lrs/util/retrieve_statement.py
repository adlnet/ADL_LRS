from lrs import objects, models
from django.core.cache import cache
from lrs.objects import Actor, Activity, Statement
from datetime import datetime
from django.conf import settings
from django.core.paginator import Paginator
import bencode
import pytz
import hashlib
import json
import jwt
import pickle
import pdb


def convertToUTC(timestr):
    # Strip off TZ info
    timestr = timestr[:timestr.rfind('+')]
    
    # Convert to date_object (directive for parsing TZ out is buggy, which is why we do it this way)
    date_object = datetime.strptime(timestr, '%Y-%m-%dT%H:%M:%S.%f')
    
    # Localize TZ to UTC since everything is being stored in DB as UTC
    date_object = pytz.timezone("UTC").localize(date_object)
    return date_object

def complexGet(req_dict):
    limit = 0    
    args = {}
    sparse = True
    # Cycle through req_dict and find simple args
    for k,v in req_dict.items():
        if k.lower() == 'verb':
            args[k] = v 
        elif k.lower() == 'since':
            date_object = convertToUTC(v)
            args['stored__gt'] = date_object
        elif k.lower() == 'until':
            date_object = convertToUTC(v)
            args['stored__lte'] = date_object
    # If searching by activity or actor
    if 'object' in req_dict:
        objectData = req_dict['object']        
        
        if not type(objectData) is dict:
            try:
                objectData = json.loads(objectData) 
            except Exception, e:
                objectData = json.loads(objectData.replace("'",'"'))
     
        if objectData['objectType'].lower() == 'activity':
            activity = models.activity.objects.get(activity_id=objectData['id'])
            args['stmt_object'] = activity
        elif objectData['objectType'].lower() == 'agent' or objectData['objectType'].lower() == 'person':
            agent = Actor.Actor(json.dumps(objectData)).agent
            args['stmt_object'] = agent
        else:
            activity = models.activity.objects.get(activity_id=objectData['id'])
            args['stmt_object'] = activity

    if 'registration' in req_dict:
        uuid = str(req_dict['registration'])
        cntx = models.context.objects.filter(registration=uuid)
        args['context'] = cntx

    if 'actor' in req_dict:
        actorData = req_dict['actor']
        if not type(actorData) is dict:
            try:
                actorData = json.loads(actorData) 
            except Exception, e:
                actorData = json.loads(actorData.replace("'",'"'))
            
        agent = Actor.Actor(json.dumps(actorData)).agent
        args['actor'] = agent

    if 'instructor' in req_dict:
        instData = req_dict['instructor']
        
        if not type(instData) is dict:
            try:
                instData = json.loads(instData) 
            except Exception, e:
                instData = json.loads(instData.replace("'",'"'))
            
        instructor = Actor.Actor(json.dumps(instData)).agent                 

        cntxList = models.context.objects.filter(instructor=instructor)
        args['context__in'] = cntxList

    if 'authoritative' in req_dict:
        authData = req_dict['authoritative']

        if not type(authData) is dict:
            try:
                authData = json.loads(authData) 
            except Exception, e:
                authData = json.loads(authData.replace("'",'"'))

        authority = Actor.Actor(json.dumps(authData)).agent
        args['authority'] = authority

    if 'limit' in req_dict:
        limit = int(req_dict['limit'])    

    if 'sparse' in req_dict:
        if not type(req_dict['sparse']) is bool:
            if req_dict['sparse'].lower() == 'false':
                sparse = False
        else:
            sparse = req_dict['sparse']
    pdb.set_trace()
    if limit == 0 and 'more_start' not in req_dict:
        # Retrieve statements from DB
        stmt_list = models.statement.objects.filter(**args).order_by('-stored')
    elif 'more_start' in req_dict:
        start = int(req_dict['more_start'])
        stmt_list = models.statement.objects.filter(**args).order_by('-stored')[start:]
    else:
        stmt_list = models.statement.objects.filter(**args).order_by('-stored')[:limit]

    full_stmt_list = []

    # For each stmt convert to our Statement class and retrieve all json
    for stmt in stmt_list:
        stmt = Statement.Statement(statement_id=stmt.statement_id, get=True)
        full_stmt_list.append(stmt.get_full_statement_json(sparse))
    return full_stmt_list

def getStatementRequest(req_id):  
    pdb.set_trace()  
    # Retrieve encoded list of statements
    # encoded_dict = cache.get(req_id)
    encoded_list = cache.get(req_id)

    # Could have expired or never existed
    if not encoded_list:
        return ['List does not exist - may have expired after 24 hours']

    # Decode dict
    # query_dict = jwt.decode(encoded_dict, req_id) 
    query_info = pickle.loads(encoded_list)

    query_dict = query_info[0]
    start_page = query_info[1]

    query_dict['more_start'] = (start_page - 1) * 10

    #Build list from query_dict
    stmt_list = complexGet(query_dict)

    # This is when someone initally queries using POST/GET - that sends them to buildStatementResult which
    # creates the more URL and displays first X amount - they then click more URL and views.py sends them 
    # here. This adds more_start query param to start from where buildStatementResult left off

    # Build statementResult
    stmt_result = buildStatementResult(query_dict, stmt_list, req_id)
    return stmt_list

def buildStatementResult(req_dict, stmt_list, more_id=None):
    pdb.set_trace()
    result = {}

    # Get length of stmt list
    statement_amount = len(stmt_list)  

    cache_list = []

    # Create unique hash data to use for the cache key
    hash_data = []
    hash_data.append(str(datetime.now()))
    hash_data.append(str(stmt_list))

    # Create cache key from hashed data (always 32 digits)
    cache_key = hashlib.md5(bencode.bencode(hash_data)).hexdigest()

    # See if something is already stored in cache
    encoded_list = cache.get(more_id)

    # If there is a more_id (means this is being called from getStatementRequest)
    if more_id:
        # Should always be an encoded_list if there is a more_id
        if encoded_list: 
            # Get query_info
            query_info = pickle.loads(encoded_list)
            # getStatementRequest just displayed the previous set of stmts, so increment start page since
            start_page = query_info[1] + 1
            total_pages = query_info[2]

            # If that was the last page to display then just return the remaining stmts
            if start_page == total_pages:
                result['statements'] = stmt_list
                result['more'] = ''

            # Update cache info (including new start_page)
            cache_list.append(req_dict)
            cache_list.append(start_page)
            cache_list.append(total_pages)

            encoded_info = pickle.dumps(cache_list)

            cache.set(cache_key, encoded_info)

    # If the list is larger than the limit, truncate statements and give more url
    # List will only be larger first time - getStatementRequest should truncate rest of results
    # of more URLs.
    if statement_amount > settings.SERVER_STMT_LIMIT:

        if not encoded_list:
            # Encode the list of statements
            # encoded_dict = jwt.encode(req_dict, cache_key)

            stmt_pager = Paginator(stmt_list, settings.SERVER_STMT_LIMIT)   
            # current_page = stmt_pager.next_page_number()
            # Always going to start on page 2
            current_page = 2
            total_pages = stmt_pager.count
            
            cache_list.append(req_dict)
            cache_list.append(current_page)
            cache_list.append(total_pages)

            encoded_info = pickle.dumps(cache_list)

            # Save encoded_dict in cache
            cache.set(cache_key,encoded_info)

            result['statements'] = stmt_pager.page(1).object_list
            result['more'] = '/TCAPI/statements/more/%s' % cache_key    
        
    # Just provide statements since the list is under the limit
    else:
        result['statements'] = stmt_list
        result['more'] = ''
    return result

