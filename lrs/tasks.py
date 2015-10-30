from __future__ import absolute_import

import urllib2
import json

from celery import shared_task
from celery.utils.log import get_task_logger

from django.conf import settings
from django.db.models import Q

from lrs.util import StatementValidator as SV

celery_logger = get_task_logger('celery-task')

@shared_task
def check_activity_metadata(stmts):
    from lrs.models import Activity
    activity_ids = list(Activity.objects.filter(object_of_statement__statement_id__in=stmts).values_list('activity_id', flat=True).distinct())
    [get_activity_metadata(a_id) for a_id in activity_ids]

@shared_task
def void_statements(stmts):
    from lrs.models import Statement    
    try:
        Statement.objects.filter(statement_id__in=stmts).update(voided=True)
    except Exception, e:
        celery_logger.exception("Voiding Statement Error: " + e.message)

@shared_task
def check_statement_hooks(stmt_ids):
    from lrs.models import Hook, Statement
    hooks = Hook.objects.all()
    for h in hooks:
        filters = h.filters
        config = h.config
        if 'endpoint' not in config:
            celery_logger.exception("Endpoint not in hook %s" % str(h.name))
        else:
            secret = str(config['secret']) if 'secret' in config else None
            filterQ = parse_filter(filters, Q()) & Q(statement_id__in=stmt_ids)
            found = Statement.objects.filter(filterQ)
            if found:
                data = '{"statements": [%s], "id": "%s"}' % (",".join(stmt for stmt in found.values_list('full_statement', flat=True)), h.hook_id)
                req = urllib2.Request(str(h.config['endpoint']))
                req.add_header('Content-Type', 'application/json')
                if secret:
                    req.add_header('X-XAPI-Signature', secret)
                try:
                    celery_logger.info("Sending statements to hook endpoint %s" % str(h.config['endpoint']))
                    resp = urllib2.urlopen(req, data)
                    resp.close()
                    celery_logger.info("Response code for sending statements to hook endpoint %s : %s" % (str(h.config['endpoint']), resp.getcode()))
                except Exception, e:
                    celery_logger.exception("Could not send statements to hook %s: %s" % (str(h.config['endpoint']), e.message))

def parse_filter(filters, filterQ):
    from lrs.models import Agent
    actorQ, verbQ, objectQ, filterQ = Q(), Q(), Q(), Q()
    
    if isinstance(filters, dict):
        if 'actor' in filters.keys():
            actors = filters.pop('actor')
            if isinstance(actors, list):
                for a in actors:
                    try:
                        agent = Agent.objects.retrieve_or_create(**a)[0]
                    except Exception:
                        celery_logger.exception("Agent data was invalid for agent filter")
                    else:
                        actorQ = actorQ | Q(actor=agent)
        if 'verb' in filters.keys():
            verbs = filters.pop('verb')
            if isinstance(verbs, list):
                for v in verbs:
                    if 'id' in v:
                        verbQ = verbQ | Q(verb__verb_id=v['id'])
        if 'object' in filters.keys():
            objects = filters.pop('object')
            if isinstance(objects, list):
                for o in objects:
                    if 'id' in o:
                        objectQ = objectQ | Q(object_activity__activity_id=o['id'])
        filterQ = actorQ & verbQ & objectQ

        if 'related' in filters.keys():
            related = filters.pop('related')
            if isinstance(related, list):
                filterQ = filterQ & parse_related_filter(related, True)
    return filterQ

def parse_related_filter(related, or_operand):
    from lrs.models import Agent
    innerQ = Q()
    objectQ = Q()
    for ob in related:
        # Any or/and values should be a list
        if 'or' in ob.keys():
            ors = ob['or']
            if isinstance(ors, list):
                innerQ = innerQ | parse_related_filter(ors, True)
        elif 'and' in ob.keys():
            ands = ob['and']
            if isinstance(ands, list):
                innerQ = innerQ & parse_related_filter(ands, False)
        # Any other values will be an object
        else:
            if 'id' in ob:
                objectQ = set_object_activity_query(objectQ, ob['id'], or_operand)
            else:
                try:
                    agent = Agent.objects.retrieve_or_create(**ob)[0]
                except Exception:
                    celery_logger.exception("Agent data was invalid for agent filter")
                else:
                    objectQ = set_object_agent_query(objectQ, agent, or_operand)
    if or_operand:
        return objectQ | innerQ
    else:
        return objectQ & innerQ

def set_object_activity_query(q, act_id, or_operand):
    if or_operand:
        return q | (Q(context_ca_parent__activity_id=act_id) \
            | Q(context_ca_grouping__activity_id=act_id) \
            | Q(context_ca_category__activity_id=act_id) \
            | Q(context_ca_other__activity_id=act_id) \
            | Q(object_substatement__object_activity__activity_id=act_id) \
            | Q(object_substatement__context_ca_parent__activity_id=act_id) \
            | Q(object_substatement__context_ca_grouping__activity_id=act_id) \
            | Q(object_substatement__context_ca_category__activity_id=act_id) \
            | Q(object_substatement__context_ca_other__activity_id=act_id))        

    return q & (Q(context_ca_parent__activity_id=act_id) \
        | Q(context_ca_grouping__activity_id=act_id) \
        | Q(context_ca_category__activity_id=act_id) \
        | Q(context_ca_other__activity_id=act_id) \
        | Q(object_substatement__object_activity__activity_id=act_id) \
        | Q(object_substatement__context_ca_parent__activity_id=act_id) \
        | Q(object_substatement__context_ca_grouping__activity_id=act_id) \
        | Q(object_substatement__context_ca_category__activity_id=act_id) \
        | Q(object_substatement__context_ca_other__activity_id=act_id))

def set_object_agent_query(q, agent, or_operand):
    if or_operand:
        return q | (Q(object_agent=agent) | Q(authority=agent) \
              | Q(context_instructor=agent) | Q(context_team=agent) \
              | Q(object_substatement__actor=agent) \
              | Q(object_substatement__object_agent=agent) \
              | Q(object_substatement__context_instructor=agent) \
              | Q(object_substatement__context_team=agent))

    return q & (Q(object_agent=agent) | Q(authority=agent) \
          | Q(context_instructor=agent) | Q(context_team=agent) \
          | Q(object_substatement__actor=agent) \
          | Q(object_substatement__object_agent=agent) \
          | Q(object_substatement__context_instructor=agent) \
          | Q(object_substatement__context_team=agent))
    
# Retrieve JSON data from ID
def get_activity_metadata(act_id):
    act_url_data = {}
    # See if id resolves
    try:
        req = urllib2.Request(act_id)
        req.add_header('Accept', 'application/json, */*')
        act_resp = urllib2.urlopen(req, timeout=settings.ACTIVITY_ID_RESOLVE_TIMEOUT)
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
                validator = SV.StatementValidator()
                validator.validate_activity(fake_activity)
            except Exception, e:
                valid_url_data = False
                celery_logger.exception("Activity Metadata Retrieval Error: " + e.message)

            if valid_url_data:
                update_activity_definition(fake_activity)

def update_activity_definition(act):
    from lrs.models import Activity
    # Try to get activity by id
    try:
        activity = Activity.objects.get(activity_id=act['id'])
    except Activity.DoesNotExist:
        # Could not exist yet
        pass
    # If the activity already exists in the db
    else:
        # If there is a name in the IRI act definition add it to what already exists
        if 'name'in act['definition']:
            activity.activity_definition_name = dict(activity.activity_definition_name.items() + act['definition']['name'].items())
        # If there is a description in the IRI act definition add it to what already exists
        if 'description' in act['definition']:
            activity.activity_definition_description = dict(activity.activity_definition_description.items() + act['definition']['description'].items())

        activity.activity_definition_type = act['definition'].get('type', '')
        activity.activity_definition_moreInfo = act['definition'].get('moreInfo', '')
        activity.activity_definition_interactionType = act['definition'].get('interactionType', '')
        activity.activity_definition_extensions = act['definition'].get('extensions', {})
        activity.activity_definition_crpanswers = act['definition'].get('correctResponsesPattern', {})
        activity.activity_definition_choices = act['definition'].get('choices', {})
        activity.activity_definition_sources = act['definition'].get('source', {}) 
        activity.activity_definition_targets = act['definition'].get('target', {})
        activity.activity_definition_steps = act['definition'].get('steps', {})
        activity.activity_definition_scales = act['definition'].get('scale', {})
        activity.save()