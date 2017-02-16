import json
from isodate.isodatetime import parse_datetime
from isodate.isoerror import ISO8601Error
import uuid

from . import get_agent_ifp, convert_to_datatype
from authorization import auth
from StatementValidator import StatementValidator

from ..models import Statement, Agent, Activity, ActivityState, ActivityProfile, AgentProfile
from ..exceptions import ParamConflict, ParamError, Forbidden, BadRequest, IDNotFoundError


def check_for_existing_statementId(stmtID):
    return Statement.objects.filter(statement_id=stmtID).exists()


def check_for_no_other_params_supplied(query_dict):
    supplied = True
    if len(query_dict) <= 1:
        supplied = False
    return supplied

# Extra agent validation for state and profile


def validate_oauth_for_documents(req_dict, endpoint): 
    ag = req_dict['params']['agent']
    token = req_dict['auth']['oauth_token']
    scopes = token.scope_to_list()
    if 'all' not in scopes:
        try:
            agent = Agent.objects.get(**ag)
        except Agent.DoesNotExist:
            # if agent DNE, profile/state scope should still be able to create one
            pass
        else:
            if agent not in req_dict['auth']['agent'].member.all():
                err_msg = "Agent for %s is out of scope" % endpoint
                raise Forbidden(err_msg)


def validate_void_statement(void_id):
    # Retrieve statement, check if the verb is 'voided' - if not then set the voided flag to true else return error
    # since you cannot unvoid a statement and should just reissue the
    # statement under a new ID.
    stmts = Statement.objects.filter(statement_id=void_id)
    if len(stmts) > 1:
        raise IDNotFoundError(
            "Something went wrong. %s statements found with id %s" % (len(stmts), void_id))
    elif len(stmts) == 1:
        if stmts[0].voided:
            err_msg = "Statement with ID: %s is already voided, cannot unvoid. Please re-issue the statement under a new ID." % void_id
            raise BadRequest(err_msg)
        if stmts[0].verb.verb_id == "http://adlnet.gov/expapi/verbs/voided":
            err_msg = "Statement with ID: %s is a voiding statement and cannot be voided." % void_id
            raise BadRequest(err_msg)

def validate_body(body, auth, payload_sha2s, content_type):
    [server_validate_statement(
        stmt, auth, payload_sha2s, content_type) for stmt in body]


def server_validate_statement(stmt, auth, payload_sha2s, content_type):
    if 'id' in stmt:
        statement_id = stmt['id']
        if check_for_existing_statementId(statement_id):
            err_msg = "A statement with ID %s already exists" % statement_id
            raise ParamConflict(err_msg)

    if stmt['verb']['id'] == 'http://adlnet.gov/expapi/verbs/voided':
        validate_void_statement(stmt['object']['id'])

    if 'attachments' in stmt:
        attachment_data = stmt['attachments']
        validate_attachments(attachment_data, payload_sha2s, content_type)


@auth
def statements_post(req_dict):
    if req_dict['params'].keys():
        raise ParamError("The post statements request contained unexpected parameters: %s" % ", ".join(
            req_dict['params'].keys()))

    try:
        validator = StatementValidator(req_dict['body'])
        validator.validate()
    except Exception as e:
        raise BadRequest(e.message)
    except ParamError as e:
        raise ParamError(e.message)

    if isinstance(req_dict['body'], dict):
        body = [req_dict['body']]
    else:
        body = req_dict['body']
    validate_body(body, req_dict['auth'], req_dict.get(
        'payload_sha2s', None), req_dict['headers']['CONTENT_TYPE'])

    return req_dict


@auth
def statements_more_get(req_dict):
    if 'more_id' not in req_dict:
        err_msg = "Missing more_id while trying to hit /more endpoint"
        raise ParamError(err_msg)
    return req_dict


def validate_statementId(req_dict):
    if 'statementId' in req_dict['params'] and 'voidedStatementId' in req_dict['params']:
        err_msg = "Cannot have both statementId and voidedStatementId in a GET request"
        raise ParamError(err_msg)
    elif 'statementId' in req_dict['params']:
        statementId = req_dict['params']['statementId']
        voided = False
    else:
        statementId = req_dict['params']['voidedStatementId']
        voided = True

    not_allowed = ["agent", "verb", "activity", "registration",
                   "related_activities", "related_agents", "since",
                   "until", "limit", "ascending"]
    bad_keys = set(not_allowed) & set(req_dict['params'].keys())
    if bad_keys:
        err_msg = "Cannot have %s in a GET request only 'format' and/or 'attachments' are allowed with 'statementId' and 'voidedStatementId'" % ', '.join(
            bad_keys)
        raise ParamError(err_msg)

    # Try to retrieve stmt, if DNE then return empty else return stmt info
    try:
        uuidId = uuid.UUID(str(statementId))
        st = Statement.objects.get(statement_id=uuidId)
    except (Statement.DoesNotExist):
        err_msg = 'There is no statement associated with the id: %s' % statementId
        raise IDNotFoundError(err_msg)
    except (ValueError):
        err_msg = 'Not a valid id for query: %s' % statementId
        raise BadRequest(err_msg)

    auth = req_dict.get('auth', None)
    mine_only = auth and 'statements_mine_only' in auth

    if auth['agent']:
        if mine_only and st.authority.id != auth['agent'].id:
            err_msg = "Incorrect permissions to view statements"
            raise Forbidden(err_msg)

    if st.voided != voided:
        if st.voided:
            err_msg = 'The requested statement (%s) is voided. Use the "voidedStatementId" parameter to retrieve your statement.' % statementId
        else:
            err_msg = 'The requested statement (%s) is not voided. Use the "statementId" parameter to retrieve your statement.' % statementId
        raise IDNotFoundError(err_msg)

    return statementId


@auth
def statements_get(req_dict):
    rogueparams = set(req_dict['params']) - set(["statementId", "voidedStatementId", "agent", "verb", "activity", "registration",
                                                 "related_activities", "related_agents", "since",
                                                 "until", "limit", "format", "attachments", "ascending"])
    if rogueparams:
        raise ParamError(
            "The get statements request contained unexpected parameters: %s" % ", ".join(rogueparams))

    formats = ['exact', 'canonical', 'ids']
    if 'params' in req_dict and 'format' in req_dict['params']:
        if req_dict['params']['format'] not in formats:
            raise ParamError("The format filter value (%s) was not one of the known values: %s" % (
                req_dict['params']['format'], ','.join(formats)))
    else:
        req_dict['params']['format'] = 'exact'

    # StatementId could be for voided statement as well
    if 'params' in req_dict and ('statementId' in req_dict['params'] or 'voidedStatementId' in req_dict['params']):
        req_dict['statementId'] = validate_statementId(req_dict)

    if 'since' in req_dict['params']:
        try:
            parse_datetime(req_dict['params']['since'])
        except (Exception, ISO8601Error):
            raise ParamError(
                "Since parameter was not a valid ISO8601 timestamp")

    if 'until' in req_dict['params']:
        try:
            parse_datetime(req_dict['params']['until'])
        except (Exception, ISO8601Error):
            raise ParamError(
                "Until parameter was not a valid ISO8601 timestamp")

    # Django converts all query values to string - make boolean depending on if client wants attachments or not
    # Only need to do this in GET b/c GET/more will have it saved in pickle
    # information
    if 'params' in req_dict and 'attachments' in req_dict['params']:
        if req_dict['params']['attachments'].lower() == 'true':
            req_dict['params']['attachments'] = True
        else:
            req_dict['params']['attachments'] = False
    else:
        req_dict['params']['attachments'] = False
    return req_dict


@auth
def statements_put(req_dict):
    # Find any unexpected parameters
    rogueparams = set(req_dict['params']) - set(["statementId"])
    if rogueparams:
        raise ParamError(
            "The put statements request contained unexpected parameters: %s" % ", ".join(rogueparams))

    # Statement id can must be supplied in query param. If in the body too, it
    # must be the same
    if 'statementId' not in req_dict['params']:
        raise ParamError(
            "Error -- statements - method = %s, but no statementId parameter or ID given in statement" % req_dict['method'])
    else:
        statement_id = req_dict['params']['statementId']

    # Try to get id if in body
    try:
        statement_body_id = req_dict['body']['id']
    except Exception as e:
        statement_body_id = None

    # If ids exist in both places, check if they are equal
    if statement_body_id and statement_id != statement_body_id:
        raise ParamError(
            "Error -- statements - method = %s, param and body ID both given, but do not match" % req_dict['method'])

    # Set id inside of statement with param id
    if not statement_body_id:
        req_dict['body']['id'] = statement_id

    # If there are no other params-raise param error since nothing else is
    # supplied
    if not check_for_no_other_params_supplied(req_dict['body']):
        raise ParamError("No other params are supplied with statementId.")

    # Validate statement in body
    try:
        validator = StatementValidator(req_dict['body'])
        validator.validate()
    except Exception as e:
        raise BadRequest(e.message)
    except ParamError as e:
        raise ParamError(e.message)
    validate_body([req_dict['body']], req_dict['auth'], req_dict.get(
        'payload_sha2s', None), req_dict['headers']['CONTENT_TYPE'])
    return req_dict


def validate_attachments(attachment_data, payload_sha2s, content_type):
    if "multipart/mixed" in content_type:
        if not payload_sha2s:
            fileUrls = [att.get('fileUrl', None) for att in attachment_data]
            sha2s = [att.get('sha2', None) for att in attachment_data]
            if set(sha2s) != set(payload_sha2s):
                raise BadRequest(
                    "sha2 values in statement do not match sha2 headers")
            if None in fileUrls:
                raise BadRequest(
                    "Missing X-Experience-API-Hash field in header")
    elif "application/json" == content_type:
        for attachment in attachment_data:
            if 'fileUrl' not in attachment:
                raise BadRequest(
                    "When sending statements with attachments as 'application/json', you must include fileUrl field")
    else:
        raise BadRequest(
            'Invalid Content-Type %s when sending statements with attachments' % content_type)


@auth
def activity_state_post(req_dict):
    rogueparams = set(req_dict['params']) - \
        set(["activityId", "agent", "stateId", "registration"])
    if rogueparams:
        raise ParamError(
            "The post activity state request contained unexpected parameters: %s" % ", ".join(rogueparams))

    validator = StatementValidator()
    if 'activityId' in req_dict['params']:
        validator.validate_iri(
            req_dict['params']['activityId'], "activityId param for activity state")
    else:
        err_msg = "Error -- activity_state - method = %s, but activityId parameter is missing.." % req_dict[
            'method']
        raise ParamError(err_msg)

    if 'stateId' not in req_dict['params']:
        err_msg = "Error -- activity_state - method = %s, but stateId parameter is missing.." % req_dict[
            'method']
        raise ParamError(err_msg)

    if 'registration' in req_dict['params']:
        validator.validate_uuid(
            req_dict['params']['registration'], "registration param for activity state")

    if 'agent' in req_dict['params']:
        try:
            agent = json.loads(req_dict['params']['agent'])
            req_dict['params']['agent'] = agent
        except Exception:
            raise ParamError("agent param for activity state is not valid")
        validator.validate_agent(agent, "Activity state agent param")
    else:
        err_msg = "Error -- activity_state - method = %s, but agent parameter is missing.." % req_dict[
            'method']
        raise ParamError(err_msg)

    # Must have body included for state
    if 'body' not in req_dict:
        err_msg = "Could not find the state"
        raise ParamError(err_msg)

    # Extra validation if oauth
    if req_dict['auth']['type'] == 'oauth':
        validate_oauth_for_documents(req_dict, "state")

    # Check json for incoming POSTed document
    if "application/json" not in req_dict['headers']['CONTENT_TYPE']:
        raise ParamError(
            "Activity state document to be posted does not has a Content-Type of 'application/json'")

    # expected to be json
    try:
        raw_state = req_dict.pop('raw_body', req_dict.pop('body', None))
        convert_to_datatype(raw_state)
    except Exception:
        raise ParamError("Activity state document is not valid JSON")
    else:
        req_dict['state'] = raw_state

    # Check the content type if the document already exists
    registration = req_dict['params'].get('registration', None)
    agent = req_dict['params']['agent']
    a = Agent.objects.retrieve_or_create(**agent)[0]
    exists = False
    if registration:
        try:
            s = ActivityState.objects.get(state_id=req_dict['params']['stateId'], agent=a,
                                          activity_id=req_dict['params']['activityId'], registration_id=req_dict['params']['registration'])
            exists = True
        except ActivityState.DoesNotExist:
            pass
    else:
        try:
            s = ActivityState.objects.get(state_id=req_dict['params']['stateId'], agent=a,
                                          activity_id=req_dict['params']['activityId'])
            exists = True
        except ActivityState.DoesNotExist:
            pass
    
    if exists and str(s.content_type) != "application/json":
        raise ParamError("Activity state already exists but is not JSON, cannot update it with new JSON document")
    return req_dict


@auth
def activity_state_put(req_dict):
    rogueparams = set(req_dict['params']) - \
        set(["activityId", "agent", "stateId", "registration"])
    if rogueparams:
        raise ParamError(
            "The put activity state request contained unexpected parameters: %s" % ", ".join(rogueparams))

    validator = StatementValidator()
    if 'activityId' in req_dict['params']:
        validator.validate_iri(
            req_dict['params']['activityId'], "activityId param for activity state")
    else:
        err_msg = "Error -- activity_state - method = %s, but activityId parameter is missing.." % req_dict[
            'method']
        raise ParamError(err_msg)

    if 'stateId' not in req_dict['params']:
        err_msg = "Error -- activity_state - method = %s, but stateId parameter is missing.." % req_dict[
            'method']
        raise ParamError(err_msg)

    if 'registration' in req_dict['params']:
        validator.validate_uuid(
            req_dict['params']['registration'], "registration param for activity state")

    if 'agent' in req_dict['params']:
        try:
            agent = json.loads(req_dict['params']['agent'])
            req_dict['params']['agent'] = agent
        except Exception:
            raise ParamError("agent param for activity state is not valid")
        validator.validate_agent(agent, "Activity state agent param")
    else:
        err_msg = "Error -- activity_state - method = %s, but agent parameter is missing.." % req_dict[
            'method']
        raise ParamError(err_msg)

    # Must have body included for state
    if 'body' not in req_dict:
        err_msg = "Could not find the state"
        raise ParamError(err_msg)

    # Extra validation if oauth
    if req_dict['auth']['type'] == 'oauth':
        validate_oauth_for_documents(req_dict, "state")

    # Set state
    req_dict['state'] = req_dict.pop('raw_body', req_dict.pop('body', None))
    return req_dict


@auth
def activity_state_get(req_dict):
    rogueparams = set(req_dict['params']) - set(["activityId",
                                                 "agent", "stateId", "registration", "since"])
    if rogueparams:
        raise ParamError(
            "The get activity state request contained unexpected parameters: %s" % ", ".join(rogueparams))

    validator = StatementValidator()
    if 'activityId' in req_dict['params']:
        validator.validate_iri(
            req_dict['params']['activityId'], "activityId param for activity state")
    else:
        err_msg = "Error -- activity_state - method = %s, but activityId parameter is missing.." % req_dict[
            'method']
        raise ParamError(err_msg)

    if 'registration' in req_dict['params']:
        validator.validate_uuid(
            req_dict['params']['registration'], "registration param for activity state")

    if 'agent' in req_dict['params']:
        try:
            agent = json.loads(req_dict['params']['agent'])
            req_dict['params']['agent'] = agent
        except Exception:
            raise ParamError("agent param for activity state is not valid")
        validator.validate_agent(agent, "Activity state agent param")
    else:
        err_msg = "Error -- activity_state - method = %s, but agent parameter is missing.." % req_dict[
            'method']
        raise ParamError(err_msg)

    if 'since' in req_dict['params']:
        try:
            parse_datetime(req_dict['params']['since'])
        except (Exception, ISO8601Error):
            raise ParamError(
                "Since parameter was not a valid ISO8601 timestamp")

    # Extra validation if oauth
    if req_dict['auth']['type'] == 'oauth':
        validate_oauth_for_documents(req_dict, "state")
    return req_dict


@auth
def activity_state_delete(req_dict):
    rogueparams = set(req_dict['params']) - \
        set(["activityId", "agent", "stateId", "registration"])
    if rogueparams:
        raise ParamError(
            "The delete activity state request contained unexpected parameters: %s" % ", ".join(rogueparams))

    validator = StatementValidator()
    if 'activityId' in req_dict['params']:
        validator.validate_iri(
            req_dict['params']['activityId'], "activityId param for activity state")
    else:
        err_msg = "Error -- activity_state - method = %s, but activityId parameter is missing.." % req_dict[
            'method']
        raise ParamError(err_msg)

    if 'registration' in req_dict['params']:
        validator.validate_uuid(
            req_dict['params']['registration'], "registration param for activity state")

    if 'agent' in req_dict['params']:
        try:
            agent = json.loads(req_dict['params']['agent'])
            req_dict['params']['agent'] = agent
        except Exception:
            raise ParamError("agent param for activity state is not valid")
        validator.validate_agent(agent, "Activity state agent param")
    else:
        err_msg = "Error -- activity_state - method = %s, but agent parameter is missing.." % req_dict[
            'method']
        raise ParamError(err_msg)

    # Extra validation if oauth
    if req_dict['auth']['type'] == 'oauth':
        validate_oauth_for_documents(req_dict, "state")
    return req_dict


@auth
def activity_profile_post(req_dict):
    rogueparams = set(req_dict['params']) - set(["activityId", "profileId"])
    if rogueparams:
        raise ParamError(
            "The post activity profile request contained unexpected parameters: %s" % ", ".join(rogueparams))

    validator = StatementValidator()
    if 'activityId' in req_dict['params']:
        validator.validate_iri(
            req_dict['params']['activityId'], "activityId param for activity profile")
    else:
        err_msg = "Error -- activity_profile - method = %s, but activityId parameter missing.." % req_dict[
            'method']
        raise ParamError(err_msg)

    if 'profileId' not in req_dict['params']:
        err_msg = "Error -- activity_profile - method = %s, but profileId parameter missing.." % req_dict[
            'method']
        raise ParamError(err_msg)

    if 'body' not in req_dict:
        err_msg = "Could not find the profile document"
        raise ParamError(err_msg)

    # Check json for incoming POSTed document
    if "application/json" not in req_dict['headers']['CONTENT_TYPE']:
        raise ParamError(
            "Activity profile document to be posted does not has a Content-Type of 'application/json'")

    # expected to be json
    try:
        raw_profile = req_dict.pop('raw_body', req_dict.pop('body', None))
        convert_to_datatype(raw_profile)
    except Exception:
        raise ParamError("Activity profile document is not valid JSON")
    else:
        req_dict['profile'] = raw_profile

    # Check the content type if the document already exists
    exists = False
    try:
        p = ActivityProfile.objects.get(activity_id=req_dict['params']['activityId'],
                                        profile_id=req_dict['params']['profileId'])
        exists = True
    except ActivityProfile.DoesNotExist:
        pass

    # Since document to be POSTed has to be json, so does the existing document
    if exists and str(p.content_type) != "application/json":
        raise ParamError("Activity profile already exists but is not JSON, cannot update it with new JSON document")
    return req_dict


@auth
def activity_profile_put(req_dict):
    rogueparams = set(req_dict['params']) - set(["activityId", "profileId"])
    if rogueparams:
        raise ParamError(
            "The put activity profile request contained unexpected parameters: %s" % ", ".join(rogueparams))

    validator = StatementValidator()
    if 'activityId' in req_dict['params']:
        validator.validate_iri(
            req_dict['params']['activityId'], "activityId param for activity profile")
    else:
        err_msg = "Error -- activity_profile - method = %s, but activityId parameter missing.." % req_dict[
            'method']
        raise ParamError(err_msg)

    if 'profileId' not in req_dict['params']:
        err_msg = "Error -- activity_profile - method = %s, but profileId parameter missing.." % req_dict[
            'method']
        raise ParamError(err_msg)

    if 'body' not in req_dict:
        err_msg = "Could not find the profile document"
        raise ParamError(err_msg)

    # Set profile - req_parse converts all request bodies to dict, act profile needs it as string and need to replace single quotes with double quotes
    # b/c of quotation issue when using javascript with activity profile
    req_dict['profile'] = req_dict.pop('raw_body', req_dict.pop('body', None))
    return req_dict


@auth
def activity_profile_get(req_dict):
    rogueparams = set(req_dict['params']) - \
        set(["activityId", "profileId", "since"])
    if rogueparams:
        raise ParamError(
            "The get activity profile request contained unexpected parameters: %s" % ", ".join(rogueparams))

    validator = StatementValidator()
    if 'activityId' in req_dict['params']:
        validator.validate_iri(
            req_dict['params']['activityId'], "activityId param for activity profile")
    else:
        err_msg = "Error -- activity_profile - method = %s, but activityId parameter missing.." % req_dict[
            'method']
        raise ParamError(err_msg)

    if 'since' in req_dict['params']:
        try:
            parse_datetime(req_dict['params']['since'])
        except (Exception, ISO8601Error):
            raise ParamError(
                "Since parameter was not a valid ISO8601 timestamp")

    return req_dict


@auth
def activity_profile_delete(req_dict):
    rogueparams = set(req_dict['params']) - set(["activityId", "profileId"])
    if rogueparams:
        raise ParamError(
            "The delete activity profile request contained unexpected parameters: %s" % ", ".join(rogueparams))

    validator = StatementValidator()
    if 'activityId' in req_dict['params']:
        validator.validate_iri(
            req_dict['params']['activityId'], "activityId param for activity profile")
    else:
        err_msg = "Error -- activity_profile - method = %s, but activityId parameter missing.." % req_dict[
            'method']
        raise ParamError(err_msg)

    if 'profileId' not in req_dict['params']:
        err_msg = "Error -- activity_profile - method = %s, but profileId parameter missing.." % req_dict[
            'method']
        raise ParamError(err_msg)

    return req_dict


@auth
def activities_get(req_dict):
    rogueparams = set(req_dict['params']) - set(["activityId"])
    if rogueparams:
        raise ParamError(
            "The get activities request contained unexpected parameters: %s" % ", ".join(rogueparams))

    try:
        activity_id = req_dict['params']['activityId']
    except KeyError:
        err_msg = "Error -- activities - method = %s, but activityId parameter is missing" % req_dict[
            'method']
        raise ParamError(err_msg)

    # Try to retrieve activity, if DNE then return empty else return activity
    # info
    try:
        Activity.objects.get(activity_id=activity_id, authority__isnull=False)
    except Activity.DoesNotExist:
        err_msg = "No activity found with ID %s" % activity_id
        raise IDNotFoundError(err_msg)

    return req_dict


@auth
def agent_profile_post(req_dict):
    rogueparams = set(req_dict['params']) - set(["agent", "profileId"])
    if rogueparams:
        raise ParamError(
            "The post agent profile request contained unexpected parameters: %s" % ", ".join(rogueparams))

    validator = StatementValidator()
    if 'agent' in req_dict['params']:
        try:
            agent = json.loads(req_dict['params']['agent'])
            req_dict['params']['agent'] = agent
        except Exception:
            raise ParamError("agent param for agent profile is not valid")
        validator.validate_agent(agent, "agent param for agent profile")
    else:
        err_msg = "Error -- agent_profile - method = %s, but agent parameter missing.." % req_dict[
            'method']
        raise ParamError(err_msg)

    if 'profileId' not in req_dict['params']:
        err_msg = "Error -- agent_profile - method = %s, but profileId parameter missing.." % req_dict[
            'method']
        raise ParamError(err_msg)

    if 'body' not in req_dict:
        err_msg = "Could not find the profile document"
        raise ParamError(err_msg)

    # Extra validation if oauth
    if req_dict['auth']['type'] == 'oauth':
        validate_oauth_for_documents(req_dict, "agent profile")

    # Check json for incoming POSTed document
    if "application/json" not in req_dict['headers']['CONTENT_TYPE']:
        raise ParamError(
            "Agent profile document to be posted does not has a Content-Type of 'application/json'")

    # expected to be json
    try:
        raw_profile = req_dict.pop('raw_body', req_dict.pop('body', None))
        convert_to_datatype(raw_profile)
    except Exception:
        raise ParamError("Agent profile document is not valid JSON")
    else:
        req_dict['profile'] = raw_profile

    # Check the content type if the document already exists
    exists = False
    agent = req_dict['params']['agent']
    a = Agent.objects.retrieve_or_create(**agent)[0]
    try:
        p = AgentProfile.objects.get(
            profile_id=req_dict['params']['profileId'], agent=a)
        exists = True
    except AgentProfile.DoesNotExist:
        pass

    # Since document to be POSTed has to be json, so does the existing document
    if exists and str(p.content_type) != "application/json":
        raise ParamError("Agent profile already exists but is not JSON, cannot update it with new JSON document")
    return req_dict


@auth
def agent_profile_put(req_dict):
    rogueparams = set(req_dict['params']) - set(["agent", "profileId"])
    if rogueparams:
        raise ParamError(
            "The put agent profile request contained unexpected parameters: %s" % ", ".join(rogueparams))

    validator = StatementValidator()
    if 'agent' in req_dict['params']:
        try:
            agent = json.loads(req_dict['params']['agent'])
            req_dict['params']['agent'] = agent
        except Exception:
            raise ParamError("agent param for agent profile is not valid")
        validator.validate_agent(agent, "agent param for agent profile")
    else:
        err_msg = "Error -- agent_profile - method = %s, but agent parameter missing.." % req_dict[
            'method']
        raise ParamError(err_msg)

    if 'profileId' not in req_dict['params']:
        err_msg = "Error -- agent_profile - method = %s, but profileId parameter missing.." % req_dict[
            'method']
        raise ParamError(err_msg)

    if 'body' not in req_dict:
        err_msg = "Could not find the profile document"
        raise ParamError(err_msg)

    # Extra validation if oauth
    if req_dict['auth']['type'] == 'oauth':
        validate_oauth_for_documents(req_dict, "agent profile")

    req_dict['profile'] = req_dict.pop('raw_body', req_dict.pop('body', None))
    return req_dict


@auth
def agent_profile_get(req_dict):
    rogueparams = set(req_dict['params']) - \
        set(["agent", "profileId", "since"])
    if rogueparams:
        raise ParamError(
            "The get agent profile request contained unexpected parameters: %s" % ", ".join(rogueparams))

    validator = StatementValidator()
    if 'agent' in req_dict['params']:
        try:
            agent = json.loads(req_dict['params']['agent'])
            req_dict['params']['agent'] = agent
        except Exception:
            raise ParamError("agent param for agent profile is not valid")
        validator.validate_agent(agent, "agent param for agent profile")
    else:
        err_msg = "Error -- agent_profile - method = %s, but agent parameter missing.." % req_dict[
            'method']
        raise ParamError(err_msg)

    if 'since' in req_dict['params']:
        try:
            parse_datetime(req_dict['params']['since'])
        except (Exception, ISO8601Error):
            raise ParamError(
                "Since parameter was not a valid ISO8601 timestamp")

    # Extra validation if oauth
    if req_dict['auth']['type'] == 'oauth':
        validate_oauth_for_documents(req_dict, "agent profile")
    return req_dict


@auth
def agent_profile_delete(req_dict):
    rogueparams = set(req_dict['params']) - set(["agent", "profileId"])
    if rogueparams:
        raise ParamError(
            "The delete agent profile request contained unexpected parameters: %s" % ", ".join(rogueparams))

    validator = StatementValidator()
    if 'agent' in req_dict['params']:
        try:
            agent = json.loads(req_dict['params']['agent'])
            req_dict['params']['agent'] = agent
        except Exception:
            raise ParamError("agent param for agent profile is not valid")
        validator.validate_agent(agent, "agent param for agent profile")
    else:
        err_msg = "Error -- agent_profile - method = %s, but agent parameter missing.." % req_dict[
            'method']
        raise ParamError(err_msg)

    if 'profileId' not in req_dict['params']:
        err_msg = "Error -- agent_profile - method = %s, but profileId parameter missing.." % req_dict[
            'method']
        raise ParamError(err_msg)

    # Extra validation if oauth
    if req_dict['auth']['type'] == 'oauth':
        validate_oauth_for_documents(req_dict, "agent profile")
    return req_dict


@auth
def agents_get(req_dict):
    rogueparams = set(req_dict['params']) - set(["agent"])
    if rogueparams:
        raise ParamError(
            "The get agent request contained unexpected parameters: %s" % ", ".join(rogueparams))

    try:
        req_dict['params']['agent']
    except KeyError:
        err_msg = "Error -- agents url, but no agent parameter.. the agent parameter is required"
        raise ParamError(err_msg)

    validator = StatementValidator()
    try:
        agent = json.loads(req_dict['params']['agent'])
    except Exception:
        raise ParamError("agent param for agent resource is not valid")
    validator.validate_agent(agent, "agent param for agent resource")

    params = get_agent_ifp(agent)
    if not Agent.objects.filter(**params).exists():
        raise IDNotFoundError(
            "Error with Agent. The agent partial did not match any agents on record")

    req_dict['agent_ifp'] = params
    return req_dict
