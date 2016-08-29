import bencode
import hashlib
import json
from datetime import datetime
from itertools import chain

from django.core.cache import cache
from django.conf import settings
from django.core.paginator import Paginator
from django.core.urlresolvers import reverse
from django.db.models import Q

from . import convert_to_datetime_object
from ..models import Statement, Agent
from ..exceptions import NotFound


def complex_get(param_dict, limit, language, format, attachments):
    voidQ = Q(voided=False)
    # keep track if a filter other than time or sequence is used
    reffilter = False

    sinceQ = Q()
    if 'since' in param_dict:
        sinceQ = Q(stored__gt=convert_to_datetime_object(param_dict['since']))

    untilQ = Q()
    if 'until' in param_dict:
        untilQ = Q(stored__lte=convert_to_datetime_object(param_dict['until']))

    # For statements/read/mine oauth scope
    authQ = Q()
    if 'auth' in param_dict and (param_dict['auth'] and 'statements_mine_only' in param_dict['auth']):
        q_auth = param_dict['auth']['agent']

        # If oauth - set authority to look for as the user
        if q_auth.oauth_identifier:
            authQ = Q(authority=q_auth) | Q(
                authority=q_auth.get_user_from_oauth_group())
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
        related = 'related_agents' in param_dict and param_dict[
            'related_agents']

        agent = Agent.objects.retrieve(**data)
        if agent:
            # If agent is already a group, it can't be part of another group
            if agent.objectType == "Group":
                groups = []
            # Since single agent, return all groups it is in
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
            activityQ = activityQ | Q(context_ca_parent__activity_id=param_dict['activity']) \
                | Q(context_ca_grouping__activity_id=param_dict['activity']) \
                | Q(context_ca_category__activity_id=param_dict['activity']) \
                | Q(context_ca_other__activity_id=param_dict['activity']) \
                | Q(object_substatement__object_activity__activity_id=param_dict['activity']) \
                | Q(object_substatement__context_ca_parent__activity_id=param_dict['activity']) \
                | Q(object_substatement__context_ca_grouping__activity_id=param_dict['activity']) \
                | Q(object_substatement__context_ca_category__activity_id=param_dict['activity']) \
                | Q(object_substatement__context_ca_other__activity_id=param_dict['activity'])

    registrationQ = Q()
    if 'registration' in param_dict:
        reffilter = True
        registrationQ = Q(context_registration=param_dict['registration'])
    # If want ordered by ascending
    stored_param = '-stored'
    if 'ascending' in param_dict and param_dict['ascending']:
        stored_param = 'stored'

    stmtset = Statement.objects.select_related('actor', 'verb', 'context_team', 'context_instructor', 'authority',
                                               'object_agent', 'object_activity', 'object_substatement') \
        .prefetch_related('context_ca_parent', 'context_ca_grouping', 'context_ca_category', 'context_ca_other') \
        .filter(untilQ & sinceQ & authQ & agentQ & verbQ & activityQ & registrationQ).distinct()
    # Workaround since flat doesn't work with UUIDFields
    st_ids = stmtset.values_list('statement_id')
    stmtset = [st_id[0] for st_id in st_ids]

    # only find references when a filter other than
    # since, until, or limit was used
    if reffilter:
        stmtset = stmtset + stmt_ref_search(stmtset, untilQ, sinceQ)

    # Calculate limit of stmts to return
    return_limit = set_limit(limit)
    actual_length = Statement.objects.filter(
        Q(statement_id__in=stmtset) & voidQ).distinct().count()

    # If there are more stmts than the limit, need to break it up and return
    # more id
    if actual_length > return_limit:
        return create_over_limit_stmt_result(stmtset, stored_param, return_limit, language, format, attachments)
    else:
        return create_under_limit_stmt_result(stmtset, stored_param, language, format)


def stmt_ref_search(stmt_list, untilQ, sinceQ, acc=[]):
    while stmt_list:
        ref_list = [sid for sid in Statement.objects.filter(
            Q(object_statementref__in=stmt_list) & untilQ & sinceQ)
            .distinct().values_list('statement_id', flat=True)]
        (acc, stmt_list) = (acc + stmt_list, ref_list)
    return acc


def set_limit(req_limit):
    if not req_limit or req_limit > settings.SERVER_STMT_LIMIT:
        req_limit = settings.SERVER_STMT_LIMIT
    return req_limit


def create_under_limit_stmt_result(stmt_set, stored, language, format):
    stmt_result = {}
    if stmt_set:
        stmt_set = Statement.objects.select_related('actor', 'verb', 'context_team', 'context_instructor', 'authority',
                                                    'object_agent', 'object_activity', 'object_substatement') \
            .prefetch_related('context_ca_parent', 'context_ca_grouping', 'context_ca_category', 'context_ca_other') \
            .filter(Q(statement_id__in=stmt_set) & Q(voided=False)).distinct()

        stmt_result['statements'] = [stmt.to_dict(language, format) for stmt in
                                     stmt_set.order_by(stored)]
        stmt_result['more'] = ""
    else:
        stmt_result['statements'] = []
        stmt_result['more'] = ""
    return stmt_result


def create_cache_key(stmt_list):
    # Create unique hash data to use for the cache key
    hash_data = []
    hash_data.append(str(datetime.now()))
    hash_data.append(str(stmt_list))

    # Create cache key from hashed data (always 32 digits)
    key = hashlib.md5(bencode.bencode(hash_data)).hexdigest()
    return key


def create_over_limit_stmt_result(stmt_list, stored, limit, language, format, attachments):
    from ..views import statements_more_placeholder
    # First time someone queries POST/GET
    result = {}
    cache_list = []

    stmt_list = Statement.objects.filter(
        Q(statement_id__in=stmt_list) & Q(voided=False)).distinct()
    cache_list.append([s for s in stmt_list.order_by(
        stored).values_list('id', flat=True)])
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
    cache.set(cache_key, encoded_info)

    result['statements'] = [stmt.to_dict(language, format) for stmt in
                            Statement.objects.select_related('actor', 'verb', 'context_team', 'context_instructor', 'authority',
                                                             'object_agent', 'object_activity', 'object_substatement')
                            .prefetch_related('context_ca_parent', 'context_ca_grouping', 'context_ca_category', 'context_ca_other')
                            .filter(id__in=stmt_pager.page(1).object_list).order_by(stored)]
    result['more'] = "%s/%s" % (reverse('lrs:statements_more_placeholder').lower(), cache_key)
    return result


def parse_more_request(req_id):
    # Retrieve encoded info for statements
    encoded_info = cache.get(req_id)
    # Could have expired or never existed
    if not encoded_info:
        raise NotFound("List does not exist - may have expired after 24 hours")
    # Decode info
    decoded_info = json.loads(encoded_info)

    data = {}
    # Info is always cached as [stmt_list, start_page, total_pages, limit,
    # attachments, language, format]
    data["stmt_list"] = decoded_info[0]
    data["start_page"] = decoded_info[1]
    data["total_pages"] = decoded_info[2]
    data["limit"] = decoded_info[3]
    data["attachments"] = decoded_info[4]
    data["language"] = decoded_info[5]
    data["format"] = decoded_info[6]
    data["stored"] = decoded_info[7]

    # Build statementResult
    stmt_result = build_more_statement_result(req_id, **data)
    return stmt_result, data["attachments"]

# Gets called from req_process after complex_get with list of django objects and also gets called from parse_more_request when
# more_id is used so list will be serialized


def build_more_statement_result(more_id, **data):
    result = {}
    current_page = data["start_page"] + 1
    stmt_pager = Paginator(data["stmt_list"], data["limit"])
    result['statements'] = [stmt.to_dict(data["language"], data["format"]) for stmt in
                            Statement.objects.select_related('actor', 'verb', 'context_team', 'context_instructor', 'authority',
                                                             'object_agent', 'object_activity', 'object_substatement')
                            .prefetch_related('context_ca_parent', 'context_ca_grouping', 'context_ca_category', 'context_ca_other')
                            .filter(id__in=stmt_pager.page(current_page).object_list).order_by(data["stored"])]

    # If that was the last page to display then just return the remaining stmts
    if current_page == data["total_pages"]:
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
        # Create cache key from hashed data (always 32 digits)
        cache_key = create_cache_key(data["stmt_list"])
        result['more'] = "%s/%s" % (reverse('lrs:statements_more_placeholder').lower(), cache_key)

        more_cache_list = []
        # Increment next page
        start_page = current_page
        more_cache_list.append(data["stmt_list"])
        more_cache_list.append(start_page)
        more_cache_list.append(data["total_pages"])
        more_cache_list.append(data["limit"])
        more_cache_list.append(data["attachments"])
        more_cache_list.append(data["language"])
        more_cache_list.append(data["format"])
        more_cache_list.append(data["stored"])
        # Encode info
        encoded_list = json.dumps(more_cache_list)
        cache.set(cache_key, encoded_list)
    return result
