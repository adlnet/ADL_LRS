import hashlib

def create_tag(resource):
    return hashlib.sha1(resource).hexdigest()
