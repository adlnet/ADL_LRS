

import urllib.request, urllib.error, urllib.parse
import json
import hmac
import requests
import uuid
from hashlib import sha1

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
from celery.utils.log import get_task_logger

from django.conf import settings
from django.db import transaction
from django.db.models import Q

from .utils.StatementValidator import StatementValidator

celery_logger = get_task_logger('celery-task')


@shared_task
def check_activity_metadata(stmts):
    from .models import Activity
    activity_ids = list(Activity.objects.filter(
        object_of_statement__statement_id__in=stmts).values_list('activity_id', flat=True).distinct())
    [get_activity_metadata(a_id) for a_id in activity_ids]


@shared_task
def check_statement_hooks(stmt_ids):
    try:
        from .models import Statement
        from adl_lrs.models import Hook
        hooks = Hook.objects.all().values_list('hook_id', 'filters', 'config')
        stmt_ids = [uuid.UUID(st) for st in stmt_ids]        
        for h in hooks:
            filters = h[1]
            config = h[2]
            secret = config['secret'] if 'secret' in config else False
            filterQ = parse_filter(filters, Q()) & Q(statement_id__in=stmt_ids)
            found = Statement.objects.filter(filterQ).distinct()
            if found:
                if config['content_type'] == 'json':
                    data = '{"statements": [%s], "id": "%s"}' % (",".join(json.dumps(
                        stmt) for stmt in found.values_list('full_statement', flat=True)), str(h[0]))
                    headers = {'Content-Type': 'application/json'}
                else:
                    data = 'payload={"statements": [%s], "id": "%s"}' % (",".join(json.dumps(
                        stmt) for stmt in found.values_list('full_statement', flat=True)), str(h[0]))
                    headers = {
                        'Content-Type': 'application/x-www-form-urlencoded'}
                try:
                    if secret:
                        headers[
                            'X-LRS-Signature'] = hmac.new(str(secret), str(data), sha1).hexdigest()
                    headers['Connection'] = 'close'
                    celery_logger.info(
                        "Sending statements to hook endpoint %s" % str(config['endpoint']))
                    resp = requests.post(
                        str(config['endpoint']), data=data, headers=headers, verify=False)
                    celery_logger.info("Response code for sending statements to hook endpoint %s : %s - %s" % (
                        str(config['endpoint']), resp.status_code, resp.content))
                except Exception as e:
                    celery_logger.exception("Could not send statements to hook %s: %s" % (
                        str(config['endpoint']), str(e)))
    except SoftTimeLimitExceeded:
        celery_logger.exception("Statement hook task timed out")


def parse_filter(filters, filterQ):
    from .models import Agent
    actorQ, verbQ, objectQ, filterQ = Q(), Q(), Q(), Q()
    if isinstance(filters, dict):
        if 'actor' in list(filters.keys()):
            actors = filters.pop('actor')
            if isinstance(actors, list):
                for a in actors:
                    try:
                        agent = Agent.objects.retrieve(**a)
                    except Exception:
                        celery_logger.exception(
                            "Agent data was invalid for agent filter")
                    else:
                        if agent:
                            actorQ = actorQ | Q(actor=agent)
        if 'verb' in list(filters.keys()):
            verbs = filters.pop('verb')
            if isinstance(verbs, list):
                for v in verbs:
                    if 'id' in v:
                        verbQ = verbQ | Q(verb__verb_id=v['id'])
        if 'object' in list(filters.keys()):
            objects = filters.pop('object')
            if isinstance(objects, list):
                for o in objects:
                    if 'id' in o:
                        objectQ = objectQ | Q(
                            object_activity__activity_id=o['id'])
        filterQ = actorQ & verbQ & objectQ

        if 'related' in list(filters.keys()):
            related = filters.pop('related')
            if isinstance(related, list):
                filterQ = filterQ & parse_related_filter(related, True)
    return filterQ


def parse_related_filter(related, or_operand):
    from .models import Agent
    innerQ = Q()
    objectQ = Q()
    act_list = []
    for ob in related:
        # Any or/and values should be a list
        if 'or' in list(ob.keys()):
            ors = ob['or']
            if isinstance(ors, list):
                innerQ = innerQ | parse_related_filter(ors, True)
        elif 'and' in list(ob.keys()):
            ands = ob['and']
            if isinstance(ands, list):
                innerQ = innerQ & parse_related_filter(ands, False)
        # Any other values will be an object
        else:
            if 'id' in ob:
                act_list.append(ob['id'])
            else:
                try:
                    agent = Agent.objects.retrieve(**ob)
                except Exception:
                    celery_logger.exception(
                        "Agent data was invalid for agent filter")
                else:
                    if agent:
                        objectQ = set_object_agent_query(
                            objectQ, agent, or_operand)
    if act_list:
        objectQ = set_object_activity_query(objectQ, act_list, or_operand)
    if or_operand:
        return objectQ | innerQ
    else:
        return objectQ & innerQ


def set_object_activity_query(q, act_list, or_operand):
    if or_operand:
        return q | (Q(object_activity__activity_id__in=act_list) |
                    Q(context_ca_parent__activity_id__in=act_list) |
                    Q(context_ca_grouping__activity_id__in=act_list) |
                    Q(context_ca_category__activity_id__in=act_list) |
                    Q(context_ca_other__activity_id__in=act_list) |
                    Q(object_substatement__object_activity__activity_id__in=act_list) |
                    Q(object_substatement__context_ca_parent__activity_id__in=act_list) |
                    Q(object_substatement__context_ca_grouping__activity_id__in=act_list) |
                    Q(object_substatement__context_ca_category__activity_id__in=act_list) |
                    Q(object_substatement__context_ca_other__activity_id__in=act_list))

    return q & (Q(object_activity__activity_id__in=act_list) |
                Q(context_ca_parent__activity_id__in=act_list) |
                Q(context_ca_grouping__activity_id__in=act_list) |
                Q(context_ca_category__activity_id__in=act_list) |
                Q(context_ca_other__activity_id__in=act_list) |
                Q(object_substatement__object_activity__activity_id__in=act_list) |
                Q(object_substatement__context_ca_parent__activity_id__in=act_list) |
                Q(object_substatement__context_ca_grouping__activity_id__in=act_list) |
                Q(object_substatement__context_ca_category__activity_id__in=act_list) |
                Q(object_substatement__context_ca_other__activity_id__in=act_list))


def set_object_agent_query(q, agent, or_operand):
    if or_operand:
        return q | (Q(actor=agent) | Q(object_agent=agent) | Q(authority=agent) |
                    Q(context_instructor=agent) | Q(context_team=agent) |
                    Q(object_substatement__actor=agent) |
                    Q(object_substatement__object_agent=agent) |
                    Q(object_substatement__context_instructor=agent) |
                    Q(object_substatement__context_team=agent))

    return q & (Q(actor=agent) | Q(object_agent=agent) | Q(authority=agent) |
                Q(context_instructor=agent) | Q(context_team=agent) |
                Q(object_substatement__actor=agent) |
                Q(object_substatement__object_agent=agent) |
                Q(object_substatement__context_instructor=agent) |
                Q(object_substatement__context_team=agent))

# Retrieve JSON data from ID


def get_activity_metadata(act_id):
    act_url_data = {}
    # See if id resolves
    try:
        req = urllib.request.Request(act_id)
        req.add_header('Accept', 'application/json, */*')
        act_resp = urllib.request.urlopen(
            req, timeout=settings.ACTIVITY_ID_RESOLVE_TIMEOUT)
    except Exception:
        # Doesn't resolve-hopefully data is in payload
        pass
    else:
        # If it resolves then try parsing JSON from it
        try:
            act_url_data = json.loads(act_resp.read())
        except Exception:
            # Resolves but no data to retrieve - this is OK
            pass

        # If there was data from the URL
        if act_url_data:
            valid_url_data = True
            # Have to validate new data given from URL
            try:
                fake_activity = {"id": act_id, "definition": act_url_data}
                validator = StatementValidator()
                validator.validate_activity(fake_activity)
            except Exception as e:
                valid_url_data = False
                celery_logger.exception(
                    "Activity Metadata Retrieval Error: " + str(e))

            if valid_url_data:
                update_activity_definition(fake_activity)


@transaction.atomic
def update_activity_definition(act):
    from .models import Activity
    # Try to get activity by id
    try:
        activity = Activity.objects.get(activity_id=act['id'])
    except Activity.DoesNotExist:
        # Could not exist yet
        pass
    # If the activity already exists in the db
    else:
        activity.canonical_data = dict(
            list(activity.canonical_data.items()) + list(act.items()))
        activity.save()
