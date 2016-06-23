import json
import logging

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.db import transaction
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden, JsonResponse
from django.utils.decorators import decorator_from_middleware
from django.views.decorators.http import require_http_methods

from .exceptions import BadRequest, Unauthorized, Forbidden, NotFound, Conflict, PreconditionFail, OauthUnauthorized, OauthBadRequest
from .utils import req_validate, req_parse, req_process, XAPIVersionHeaderMiddleware

# This uses the lrs logger for LRS specific information
logger = logging.getLogger(__name__)


@require_http_methods(["GET", "HEAD"])
def about(request):
    lrs_data = {
        "version": settings.XAPI_VERSIONS,
        "extensions": {
            "xapi": {
                "statements":
                {
                    "name": "Statements",
                    "methods": ["GET", "POST", "PUT", "HEAD"],
                    "endpoint": reverse('lrs:statements'),
                    "description": "Endpoint to submit and retrieve XAPI statements.",
                },
                "activities":
                {
                    "name": "Activities",
                    "methods": ["GET", "HEAD"],
                    "endpoint": reverse('lrs:activities'),
                    "description": "Endpoint to retrieve a complete activity object.",
                },
                "activities_state":
                {
                    "name": "Activities State",
                    "methods": ["PUT", "POST", "GET", "DELETE", "HEAD"],
                    "endpoint": reverse('lrs:activity_state'),
                    "description": "Stores, fetches, or deletes the document specified by the given stateId that exists in the context of the specified activity, agent, and registration (if specified).",
                },
                "activities_profile":
                {
                    "name": "Activities Profile",
                    "methods": ["PUT", "POST", "GET", "DELETE", "HEAD"],
                    "endpoint": reverse('lrs:activity_profile'),
                    "description": "Saves/retrieves/deletes the specified profile document in the context of the specified activity.",
                },
                "agents":
                {
                    "name": "Agents",
                    "methods": ["GET", "HEAD"],
                    "endpoint": reverse('lrs:agents'),
                    "description": "Returns a special, Person object for a specified agent.",
                },
                "agents_profile":
                {
                    "name": "Agent Profile",
                    "methods": ["PUT", "POST", "GET", "DELETE", "HEAD"],
                    "endpoint": reverse('lrs:agent_profile'),
                    "description": "Saves/retrieves/deletes the specified profile document in the context of the specified agent.",
                }
            }
        }
    }
    return JsonResponse(lrs_data)


@require_http_methods(["GET", "HEAD"])
@decorator_from_middleware(XAPIVersionHeaderMiddleware.XAPIVersionHeader)
def statements_more(request, more_id):
    return handle_request(request, more_id)


@require_http_methods(["GET", "HEAD"])
@decorator_from_middleware(XAPIVersionHeaderMiddleware.XAPIVersionHeader)
def statements_more_placeholder(request):
    return HttpResponseForbidden("Forbidden")


@require_http_methods(["PUT", "GET", "POST", "HEAD"])
@decorator_from_middleware(XAPIVersionHeaderMiddleware.XAPIVersionHeader)
def statements(request):
    return handle_request(request)


@require_http_methods(["PUT", "POST", "GET", "DELETE", "HEAD"])
@decorator_from_middleware(XAPIVersionHeaderMiddleware.XAPIVersionHeader)
def activity_state(request):
    return handle_request(request)


@require_http_methods(["PUT", "POST", "GET", "DELETE", "HEAD"])
@decorator_from_middleware(XAPIVersionHeaderMiddleware.XAPIVersionHeader)
def activity_profile(request):
    return handle_request(request)


@require_http_methods(["GET", "HEAD"])
@decorator_from_middleware(XAPIVersionHeaderMiddleware.XAPIVersionHeader)
def activities(request):
    return handle_request(request)


@require_http_methods(["PUT", "POST", "GET", "DELETE", "HEAD"])
@decorator_from_middleware(XAPIVersionHeaderMiddleware.XAPIVersionHeader)
def agent_profile(request):
    return handle_request(request)


@require_http_methods(["GET", "HEAD"])
@decorator_from_middleware(XAPIVersionHeaderMiddleware.XAPIVersionHeader)
def agents(request):
    return handle_request(request)


@transaction.atomic
def handle_request(request, more_id=None):
    validators = {
        reverse('lrs:statements').lower(): {
            "POST": req_validate.statements_post,
            "GET": req_validate.statements_get,
            "PUT": req_validate.statements_put,
            "HEAD": req_validate.statements_get
        },
        reverse('lrs:statements_more_placeholder').lower(): {
            "GET": req_validate.statements_more_get,
            "HEAD": req_validate.statements_more_get
        },
        reverse('lrs:activity_state').lower(): {
            "POST": req_validate.activity_state_post,
            "PUT": req_validate.activity_state_put,
            "GET": req_validate.activity_state_get,
            "HEAD": req_validate.activity_state_get,
            "DELETE": req_validate.activity_state_delete
        },
        reverse('lrs:activity_profile').lower(): {
            "POST": req_validate.activity_profile_post,
            "PUT": req_validate.activity_profile_put,
            "GET": req_validate.activity_profile_get,
            "HEAD": req_validate.activity_profile_get,
            "DELETE": req_validate.activity_profile_delete
        },
        reverse('lrs:activities').lower(): {
            "GET": req_validate.activities_get,
            "HEAD": req_validate.activities_get
        },
        reverse('lrs:agent_profile').lower(): {
            "POST": req_validate.agent_profile_post,
            "PUT": req_validate.agent_profile_put,
            "GET": req_validate.agent_profile_get,
            "HEAD": req_validate.agent_profile_get,
            "DELETE": req_validate.agent_profile_delete
        },
        reverse('lrs:agents').lower(): {
            "GET": req_validate.agents_get,
            "HEAD": req_validate.agents_get
        }
    }
    processors = {
        reverse('lrs:statements').lower(): {
            "POST": req_process.statements_post,
            "GET": req_process.statements_get,
            "HEAD": req_process.statements_get,
            "PUT": req_process.statements_put
        },
        reverse('lrs:statements_more_placeholder').lower(): {
            "GET": req_process.statements_more_get,
            "HEAD": req_process.statements_more_get
        },
        reverse('lrs:activity_state').lower(): {
            "POST": req_process.activity_state_post,
            "PUT": req_process.activity_state_put,
            "GET": req_process.activity_state_get,
            "HEAD": req_process.activity_state_get,
            "DELETE": req_process.activity_state_delete
        },
        reverse('lrs:activity_profile').lower(): {
            "POST": req_process.activity_profile_post,
            "PUT": req_process.activity_profile_put,
            "GET": req_process.activity_profile_get,
            "HEAD": req_process.activity_profile_get,
            "DELETE": req_process.activity_profile_delete
        },
        reverse('lrs:activities').lower(): {
            "GET": req_process.activities_get,
            "HEAD": req_process.activities_get
        },
        reverse('lrs:agent_profile').lower(): {
            "POST": req_process.agent_profile_post,
            "PUT": req_process.agent_profile_put,
            "GET": req_process.agent_profile_get,
            "HEAD": req_process.agent_profile_get,
            "DELETE": req_process.agent_profile_delete
        },
        reverse('lrs:agents').lower(): {
            "GET": req_process.agents_get,
            "HEAD": req_process.agents_get
        }
    }

    try:
        r_dict = req_parse.parse(request, more_id)
        path = request.path.lower()
        if path.endswith('/'):
            path = path.rstrip('/')
        # Cutoff more_id
        if 'more' in path:
            path = "%s/%s" % (reverse('lrs:statements').lower(), "more")
        req_dict = validators[path][r_dict['method']](r_dict)
        return processors[path][req_dict['method']](req_dict)
    except BadRequest as err:
        log_exception(request.path, err)
        return HttpResponse(err.message, status=400)
    except ValidationError as ve:
        log_exception(request.path, ve)
        return HttpResponse(ve.messages[0], status=400)
    except OauthBadRequest as oauth_err:
        log_exception(request.path, oauth_err)
        return HttpResponse(oauth_err.message, status=400)
    except Unauthorized as autherr:
        log_exception(request.path, autherr)
        r = HttpResponse(autherr, status=401)
        r['WWW-Authenticate'] = 'Basic realm="ADLLRS"'
        return r
    except OauthUnauthorized as oauth_err:
        log_exception(request.path, oauth_err)
        return HttpResponse(oauth_err.message, status=401)
    except Forbidden as forb:
        log_exception(request.path, forb)
        return HttpResponse(forb.message, status=403)
    except NotFound as nf:
        log_exception(request.path, nf)
        return HttpResponse(nf.message, status=404)
    except Conflict as c:
        log_exception(request.path, c)
        return HttpResponse(c.message, status=409)
    except PreconditionFail as pf:
        log_exception(request.path, pf)
        return HttpResponse(pf.message, status=412)
    # Added BadResponse for OAuth validation
    except HttpResponseBadRequest as br:
        log_exception(request.path, br)
        return br
    except Exception as err:
        log_exception(request.path, err)
        return HttpResponse(err.message, status=500)


def log_exception(path, ex):
    logger.info("\nException while processing: %s" % path)
    logger.exception(ex)
