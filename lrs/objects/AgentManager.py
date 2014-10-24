import json

from ..models import Agent
from ..exceptions import ParamError

class AgentManager():
    def __init__(self, params, define=True):
        # This parsing is kept for profile/state/agents endpoints
        if not isinstance(params, dict):
            try:
                params = json.loads(params)
            except Exception:
                err_msg = "Error parsing the Agent object. Expecting json. Received: %s which is %s" % (params,
                    type(params))
                raise ParamError(err_msg) 
        
        # Define determines if the user submitting the statement with the agent in it has the ability
        # to make canonical agents and/or update canonical agents
        # TODO - this falls in line with the todo in statementmanager...if come across a stmt with auth field
        # but no auth in request, we try to get the auth agent - if it's oauth we don't know what define permission they have
        params['canonical_version'] = define
        self.Agent, self.created = Agent.objects.retrieve_or_create(**params)