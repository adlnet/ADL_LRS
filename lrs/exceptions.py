class BadRequest(Exception):
    pass

class ParamError(BadRequest):
    pass

class Unauthorized(Exception):
    pass

class Forbidden(Exception):
    pass

class NotFound(Exception):
    pass

class IDNotFoundError(NotFound):
    pass


class Conflict(Exception):
    pass

class ParamConflict(Conflict):
    pass

class PreconditionFail(Exception):
    pass

class OauthUnauthorized(Exception):
    def __init__(self, response):
        self.response = response
