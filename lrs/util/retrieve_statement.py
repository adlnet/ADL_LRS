from lrs import objects, models
from django.core.cache import cache
from lrs.objects import Actor, Activity, Statement
from datetime import datetime
from django.conf import settings
import bencode
import pytz
import hashlib
import json
import jwt
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

    if limit == 0:
        # Retrieve statements from DB
        stmt_list = models.statement.objects.filter(**args).order_by('-stored')
    else:
        stmt_list = models.statement.objects.filter(**args).order_by('-stored')[:limit]


    full_stmt_list = []

    # For each stmt convert to our Statement class and retrieve all json
    for stmt in stmt_list:
        stmt = Statement.Statement(statement_id=stmt.statement_id, get=True)
        full_stmt_list.append(stmt.get_full_statement_json(sparse))
    return full_stmt_list

def getStatementRequest(req_id):    
    # Retrieve encoded list of statements
    encoded_dict = cache.get(req_id)

    # Could have expired or never existed
    if not encoded_dict:
        return ['List does not exist - may have expired after 24 hours']

    # Decode dict
    query_dict = jwt.decode(encoded_dict, req_id) 
    
    # Get list TODO - limit the result
    stmt_list = complexGet(query_dict)
    stmt_result = buildStatementResult(query_dict, stmt_list)
    return stmt_list

def buildStatementResult(req_dict, stmt_list):
    result = {}
    # pdb.set_trace()
    statement_amount = len(stmt_list)  
    # If the list is larger than the limit, truncate statements and give more url
    # TODO: more should display the stmts already being shown? if so, just change
    # encoded_dict = jwt.encode(stmt_list[SERVER_STMT_LIMIT:], cache_key)
    if statement_amount > settings.SERVER_STMT_LIMIT:
        # Create unique hash data to use for the cache key
        hash_data = []
        hash_data.append(str(datetime.now()))
        hash_data.append(str(stmt_list))

        # Create cache key from hashed data (always 32 digits)
        cache_key = hashlib.md5(bencode.bencode(hash_data)).hexdigest()

        # Encode the list of statements
        encoded_dict = jwt.encode(req_dict, cache_key)

        # Save encoded_dict in cache
        cache.set(cache_key,encoded_dict)

        result['statments'] = stmt_list[:settings.SERVER_STMT_LIMIT]
        result['more'] = '/TCAPI/statements/more/%s' % cache_key    
    # Just provide statements since the list is under the limit
    else:
        result['statements'] = stmt_list
        result['more'] = ''
    return result

