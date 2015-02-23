# coding=utf-8
import json
import base64
import os
import uuid
import math
import urllib
import hashlib

from email import message_from_string
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText

from django.test import TestCase
from django.core.urlresolvers import reverse
from django.conf import settings

from ..models import Statement
from ..views import register, statements, statements_more
from ..util.util import convert_to_utc

class StatementFilterTests(TestCase):

    @classmethod
    def setUpClass(cls):
        print "\n%s" % __name__

    def setUp(self):
        self.saved_stmt_limit=settings.SERVER_STMT_LIMIT
        settings.SERVER_STMT_LIMIT=100
        self.username = "tom"
        self.email = "tom@example.com"
        self.password = "1234"
        self.auth = "Basic %s" % base64.b64encode("%s:%s" % (self.username, self.password))

        form = {"username":self.username, "email":self.email,"password":self.password,"password2":self.password}
        self.client.post(reverse(register),form, X_Experience_API_Version="1.0")
    
    def tearDown(self):
        settings.SERVER_STMT_LIMIT = 100
        attach_folder_path = os.path.join(settings.MEDIA_ROOT, "attachment_payloads")
        for the_file in os.listdir(attach_folder_path):
            file_path = os.path.join(attach_folder_path, the_file)
            try:
                os.unlink(file_path)
            except Exception, e:
                raise e
    
    def test_limit_filter(self):
        # Test limit
        for i in range(1,4):
            stmt = {"actor":{"mbox":"mailto:test%s" % i},"verb":{"id":"http://tom.com/tested"},"object":{"id":"act:activity%s" %i}}
            resp = self.client.post(reverse(statements), json.dumps(stmt), Authorization=self.auth, content_type="application/json", X_Experience_API_Version="1.0.0")
        self.assertEqual(resp.status_code, 200)
        limitGetResponse = self.client.post(reverse(statements),{"limit":2}, content_type="application/x-www-form-urlencoded", X_Experience_API_Version="1.0", Authorization=self.auth)
        self.assertEqual(limitGetResponse.status_code, 200)
        rsp = limitGetResponse.content
        respList = json.loads(rsp)
        stmts = respList["statements"]
        self.assertEqual(len(stmts), 2)    

    def test_get_id(self):
        stmt = {
            "timestamp": "2013-04-08 21:07:11.459000+00:00", 
            "object": { 
                "id": "act:adlnet.gov/JsTetris_TCAPI/level18"
            }, 
            "actor": {
                "mbox": "mailto:tom@example.com", 
                "name": "tom"
            },
            "verb": {
                "id": "http://adlnet.gov/xapi/verbs/passed(to_go_beyond)", 
                "display": {
                    "en-US": "passed"
                }
            }, 
            "result": {
                "score": {
                    "raw": 1918560.0, 
                    "min": 0.0
                }, 
                "extensions": {
                    "ext:apm": "241", 
                    "ext:lines": "165", 
                    "ext:time": "1119"
                }
            }, 
            "context": {
                "contextActivities": {
                    "grouping": {
                        "id": "act:adlnet.gov/JsTetris_TCAPI"
                    }
                }
            }
        }
        resp = self.client.post(reverse(statements), json.dumps(stmt), Authorization=self.auth, content_type="application/json", X_Experience_API_Version="1.0.0")
        self.assertEqual(resp.status_code, 200)
        sid = Statement.objects.get(verb__verb_id="http://adlnet.gov/xapi/verbs/passed(to_go_beyond)").statement_id
        param = {"statementId":sid}
        path = "%s?%s" % (reverse(statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        obj = json.loads(r.content)
        self.assertEqual(obj['result']['score']['raw'], 1918560.0)

    def test_agent_filter_does_not_exist(self):
        param = {"agent":{"mbox":"mailto:fail@faile.com"}}
        path = "%s?%s" % (reverse(statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0.1", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        obj = json.loads(r.content)
        self.assertEqual(len(obj['statements']), 0)

    def test_agent_filter(self):
        stmt = {
            "verb": {
                "id": "http://special.adlnet.gov/xapi/verbs/stopped", 
                "display": {
                    "en-US": "nixed"
                }
            }, 
            "timestamp": "2013-04-11 23:24:03.603184+00:00", 
            "object": {
                "timestamp": "2013-04-11 23:24:03.578795+00:00", 
                "object": {
                    "id": "act:adlnet.gov/website", 
                    "objectType": "Activity"
                }, 
                "actor": {
                    "mbox": "mailto:louo@example.com", 
                    "name": "louo", 
                    "objectType": "Agent"
                }, 
                "verb": {
                    "id": "http://special.adlnet.gov/xapi/verbs/hacked", 
                    "display": {
                        "en-US": "hax0r5"
                    }
                }, 
                "objectType": "SubStatement"
            }, 
            "actor": {
                "mbox": "mailto:timmy@example.com", 
                "name": "timmy", 
                "objectType": "Agent"
            }
        }
        resp = self.client.post(reverse(statements), json.dumps(stmt), Authorization=self.auth, content_type="application/json", X_Experience_API_Version="1.0.0")
        self.assertEqual(resp.status_code, 200)
        stmt = {
            "timestamp": "2013-04-08 21:07:20.392000+00:00", 
            "object": { 
                "id": "act:adlnet.gov/JsTetris_TCAPI", 
                "objectType": "Activity"
            }, 
            "actor": {
                "mbox": "mailto:tom@example.com", 
                "name": "tom", 
                "objectType": "Agent"
            }, 
            "verb": {
                "id": "http://adlnet.gov/xapi/verbs/completed", 
                "display": {
                    "en-US": "finished"
                }
            }, 
            "result": {
                "score": {
                    "raw": 1918560.0, 
                    "min": 0.0
                }, 
                "extensions": {
                    "ext:level": "19", 
                    "ext:apm": "241", 
                    "ext:lines": "165", 
                    "ext:time": "1128"
                }
            }
        }
        resp = self.client.post(reverse(statements), json.dumps(stmt), Authorization=self.auth, content_type="application/json", X_Experience_API_Version="1.0.0")
        self.assertEqual(resp.status_code, 200)

        param = {"agent":{"mbox":"mailto:tom@example.com"}}
        path = "%s?%s" % (reverse(statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        obj = json.loads(r.content)
        stmts = obj['statements']
        for s in stmts:
            if param['agent']['mbox'] not in str(s['actor']):
                self.assertEqual(s['object']['objectType'], "StatementRef")
                self.assertTrue(param['agent']['mbox'] in str(Statement.objects.get(statement_id=s['object']['id']).actor.to_dict()))
            else:
                self.assertTrue(param['agent']['mbox'] in str(s['actor']))

    def test_group_as_agent_filter(self):
        stmt = {
            "verb": {
                "id": "http://special.adlnet.gov/xapi/verbs/started", 
                "display": {
                    "en-US": "started"
                }
            },
            "timestamp": "2013-04-11 14:49:25.376782+00:00", 
            "object": {
                "id": "act:github.com/adlnet/ADL_LRS/tree/1.0dev", 
                "objectType": "Activity"
            }, 
            "actor": {
                "member": [
                    {
                        "mbox": "mailto:louo@example.com", 
                        "name": "louo", 
                        "objectType": "Agent"
                    }, 
                    {
                        "mbox": "mailto:tom@example.com", 
                        "name": "tom", 
                        "objectType": "Agent"
                    }
                ], 
                "mbox": "mailto:adllrsdevs@example.com", 
                "name": "adl lrs developers", 
                "objectType": "Group"
            }
        }
        resp = self.client.post(reverse(statements), json.dumps(stmt), Authorization=self.auth, content_type="application/json", X_Experience_API_Version="1.0.0")
        self.assertEqual(resp.status_code, 200)
        stmt = {
            "timestamp": "2013-04-10 21:25:59.583000+00:00", 
            "object": {
                "mbox": "mailto:louo@example.com", 
                "name": "louo", 
                "objectType": "Agent"
            }, 
            "actor": {
                "member": [
                    {
                        "mbox": "mailto:blobby@example.com", 
                        "name": "blobby", 
                        "objectType": "Agent"
                    }, 
                    {
                        "mbox": "mailto:timmy@example.com", 
                        "name": "timmy", 
                        "objectType": "Agent"
                    }, 
                    {
                        "mbox": "mailto:tom@example.com", 
                        "name": "tom", 
                        "objectType": "Agent"
                    }
                ], 
                "name": "the tourists", 
                "objectType": "Group"
            },
            "verb": {
                "id": "http://imaginarium.adlnet.org/xapi/verbs/sighted", 
                "display": {
                    "en-US": "sighted"
                }
            },
            "context": {
                "contextActivities": {
                    "parent": {
                        "id": "act:imaginarium.adlnet.org/xapi/imaginarium"
                    }
                }
            }
        }
        resp = self.client.post(reverse(statements), json.dumps(stmt), Authorization=self.auth, content_type="application/json", X_Experience_API_Version="1.0.0")
        self.assertEqual(resp.status_code, 200)
        param = {"agent":{"mbox":"mailto:adllrsdevs@example.com"}}
        path = "%s?%s" % (reverse(statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        count = len(Statement.objects.filter(actor__mbox=param['agent']['mbox']))
        obj = json.loads(r.content)
        stmts = obj['statements']
        self.assertEqual(len(stmts), count)
        for s in stmts:
            self.assertEqual(s['actor']['mbox'], param['agent']['mbox'])

    def test_related_agents_filter(self):
        stmt = {
            "timestamp": "2013-04-10 21:25:59.583000+00:00", 
            "object": {
                "mbox": "mailto:louo@example.com", 
                "name": "louo", 
                "objectType": "Agent"
            }, 
            "actor": {
                "member": [
                    {
                        "mbox": "mailto:blobby@example.com", 
                        "name": "blobby"
                    }, 
                    {
                        "mbox": "mailto:timmy@example.com", 
                        "name": "timmy"
                    }, 
                    {
                        "mbox": "mailto:tom@example.com", 
                        "name": "tom"
                    }
                ], 
                "name": "the tourists", 
                "objectType": "Group"
            },
            "verb": {
                "id": "http://imaginarium.adlnet.org/xapi/verbs/sighted", 
                "display": {
                    "en-US": "sighted"
                }
            },
            "context": {
                "contextActivities": {
                    "parent": {
                        "id": "act:imaginarium.adlnet.org/xapi/imaginarium"
                    }
                }
            }
        }
        resp = self.client.post(reverse(statements), json.dumps(stmt), Authorization=self.auth, content_type="application/json", X_Experience_API_Version="1.0.0")
        self.assertEqual(resp.status_code, 200)
        stmt = {
            "verb": {
                "id": "http://special.adlnet.gov/xapi/verbs/started", 
                "display": {
                    "en-US": "started"
                }
            }, 
            "timestamp": "2013-04-11 14:49:25.376782+00:00", 
            "object": {
                "id": "act:github.com/adlnet/ADL_LRS/tree/1.0dev"
            }, 
            "actor": {
                "member": [
                    {
                        "mbox": "mailto:louo@example.com", 
                        "name": "louo"
                    }, 
                    {
                        "mbox": "mailto:tom@example.com", 
                        "name": "tom"
                    }
                ], 
                "mbox": "mailto:adllrsdevs@example.com", 
                "name": "adl lrs developers", 
                "objectType": "Group"
            }
        }
        resp = self.client.post(reverse(statements), json.dumps(stmt), Authorization=self.auth, content_type="application/json", X_Experience_API_Version="1.0.0")
        self.assertEqual(resp.status_code, 200)
        stmt = {
            "verb": {
                "id": "http://special.adlnet.gov/xapi/verbs/stopped", 
                "display": {
                    "en-US": "nixed"
                }
            },
            "timestamp": "2013-04-11 23:24:03.603184+00:00", 
            "object": {
                "timestamp": "2013-04-11 23:24:03.578795+00:00", 
                "object": {
                    "id": "act:adlnet.gov/website"
                }, 
                "actor": {
                    "mbox": "mailto:louo@example.com", 
                    "name": "louo"
                }, 
                "verb": {
                    "id": "http://special.adlnet.gov/xapi/verbs/hacked", 
                    "display": {
                        "en-US": "hax0r5"
                    }
                }, 
                "objectType": "SubStatement"
            }, 
            "actor": {
                "mbox": "mailto:timmy@example.com", 
                "name": "timmy"
            }
        }
        resp = self.client.post(reverse(statements), json.dumps(stmt), Authorization=self.auth, content_type="application/json", X_Experience_API_Version="1.0.0")
        self.assertEqual(resp.status_code, 200)
        param = {"agent":{"mbox":"mailto:louo@example.com"}}
        path = "%s?%s" % (reverse(statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        obj = json.loads(r.content)
        stmts = obj['statements']
        self.assertEqual(len(stmts), 1)

        param = {"agent":{"mbox":"mailto:louo@example.com"}, "related_agents":True}
        path = "%s?%s" % (reverse(statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        obj = json.loads(r.content)
        stmts = obj['statements']
        self.assertEqual(len(stmts), 3)

    def test_agent_filter_since_and_until(self):
        batch = [
        {
            "timestamp": "2013-04-08 17:51:38.118000+00:00", 
            "object": {
                "id": "act:adlnet.gov/JsTetris_TCAPI"
            }, 
            "actor": {
                "mbox": "mailto:tom@example.com", 
                "name": "tom"
            }, 
            "verb": {
                "id": "http://adlnet.gov/xapi/verbs/attempted", 
                "display": {"en-US": "started"}
            }
        }, 
        {
            "timestamp": "2013-04-08 17:52:31.209000+00:00", 
            "object": {
                "id": "act:adlnet.gov/JsTetris_TCAPI"
            }, 
            "actor": {
                "mbox": "mailto:tom@example.com", 
                "name": "tom"
            }, 
            "verb": {
                "id": "http://adlnet.gov/xapi/verbs/attempted", 
                "display": {"en-US": "started"}
            }
        }, 
        {
            "timestamp": "2013-04-08 20:47:08.626000+00:00", 
            "object": {
                "id": "act:adlnet.gov/JsTetris_TCAPI"
            }, 
            "actor": {
                "mbox": "mailto:tom@example.com", 
                "name": "tom"
            }, 
            "verb": {
                "id": "http://adlnet.gov/xapi/verbs/attempted", 
                "display": {"en-US": "started"}
            }
        }, 
        {
            "timestamp": "2013-04-08 20:47:36.129000+00:00", 
            "object": {
                "id": "act:adlnet.gov/JsTetris_TCAPI/level1"
            }, 
            "actor": {
                "mbox": "mailto:tom@example.com", 
                "name": "tom"
            }, 
            "verb": {
                "id": "http://adlnet.gov/xapi/verbs/passed(to_go_beyond)", 
                "display": {"en-US": "passed"}
            }
        }, 
        {
            "timestamp": "2013-04-08 20:48:50.090000+00:00", 
            "object": {
                "id": "act:adlnet.gov/JsTetris_TCAPI/level2"
            }, 
            "actor": {
                "mbox": "mailto:tom@example.com", 
                "name": "tom"
            },
            "verb": {
                "id": "http://adlnet.gov/xapi/verbs/passed(to_go_beyond)", 
                "display": {"en-US": "passed"}
            }
        }, 
        {
            "timestamp": "2013-04-08 20:49:27.109000+00:00", 
            "object": {
                "id": "act:adlnet.gov/JsTetris_TCAPI/level3"
            }, 
            "actor": {
                "mbox": "mailto:tom@example.com", 
                "name": "tom"
            },
            "verb": {
                "id": "http://adlnet.gov/xapi/verbs/passed(to_go_beyond)", 
                "display": {"en-US": "passed"}
            }
        }]

        response = self.client.post(reverse(statements), json.dumps(batch), content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(response.status_code, 200)

        param = {"agent":{"mbox":"mailto:tom@example.com"}}
        path = "%s?%s" % (reverse(statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        obj = json.loads(r.content)
        stmts = obj['statements']
        # get some time points for since and until
        for s in stmts:
            if param['agent']['mbox'] not in str(s['actor']):
                self.assertEqual(s['object']['objectType'], "StatementRef")
                self.assertTrue(param['agent']['mbox'] in str(Statement.objects.get(statement_id=s['object']['id']).actor.to_dict()))
            else:
                self.assertTrue(param['agent']['mbox'] in str(s['actor']))

        cnt_all = len(stmts)
        since = stmts[int(math.floor(len(stmts)/1.5))]['stored']
        until = stmts[int(math.ceil(len(stmts)/3))]['stored']
        since_cnt = int(math.floor(len(stmts)/1.5))
        until_cnt = cnt_all - int(math.ceil(len(stmts)/3))
        since_until_cnt = int(math.floor(len(stmts)/1.5)) - int(math.ceil(len(stmts)/3))
        
        param = {"agent":{"mbox":"mailto:tom@example.com"}, "since": since}
        path = "%s?%s" % (reverse(statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        obj = json.loads(r.content)
        stmts = obj['statements']
        self.assertEqual(len(stmts), since_cnt)
        since_ids=[]
        for s in stmts:
            since_ids.append(s['id'])
            if param['agent']['mbox'] not in str(s['actor']):
                self.assertEqual(s['object']['objectType'], "StatementRef")
                self.assertTrue(param['agent']['mbox'] in str(Statement.objects.get(statement_id=s['object']['id']).actor.to_dict()))
            else:
                self.assertTrue(param['agent']['mbox'] in str(s['actor']))

        param = {"agent":{"mbox":"mailto:tom@example.com"}, "until": until}
        path = "%s?%s" % (reverse(statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        obj = json.loads(r.content)
        stmts = obj['statements']
        self.assertEqual(len(stmts), until_cnt)
        until_ids=[]
        for s in stmts:
            until_ids.append(s['id'])
            if param['agent']['mbox'] not in str(s['actor']):
                self.assertEqual(s['object']['objectType'], "StatementRef")
                self.assertTrue(param['agent']['mbox'] in str(Statement.objects.get(statement_id=s['object']['id']).actor.to_dict()))
            else:
                self.assertTrue(param['agent']['mbox'] in str(s['actor']))
        same = [x for x in since_ids if x in until_ids]
        self.assertEqual(len(same), since_until_cnt)

        param = {"agent":{"mbox":"mailto:tom@example.com"}, "since": since, "until": until}
        path = "%s?%s" % (reverse(statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        obj = json.loads(r.content)
        stmts = obj['statements']
        self.assertTrue(len(stmts) < cnt_all)
        self.assertEqual(len(stmts), since_until_cnt)
        slice_ids=[]
        for s in stmts:
            slice_ids.append(s['id'])
            if param['agent']['mbox'] not in str(s['actor']):
                self.assertEqual(s['object']['objectType'], "StatementRef")
                self.assertTrue(param['agent']['mbox'] in str(Statement.objects.get(statement_id=s['object']['id']).actor.to_dict()))
            else:
                self.assertTrue(param['agent']['mbox'] in str(s['actor']))
        self.assertItemsEqual(slice_ids, same)

    def test_related_agents_filter_until(self):
        stmt = {
            "timestamp": "2013-04-10 21:25:59.583000+00:00", 
            "object": {
                "mbox": "mailto:louo@example.com", 
                "name": "louo", 
                "objectType": "Agent"
            }, 
            "actor": {
                "member": [
                    {
                        "mbox": "mailto:blobby@example.com", 
                        "name": "blobby"
                    }, 
                    {
                        "mbox": "mailto:timmy@example.com", 
                        "name": "timmy"
                    }, 
                    {
                        "mbox": "mailto:tom@example.com", 
                        "name": "tom"
                    }
                ], 
                "name": "the tourists", 
                "objectType": "Group"
            },
            "verb": {
                "id": "http://imaginarium.adlnet.org/xapi/verbs/sighted", 
                "display": {
                    "en-US": "sighted"
                }
            },
            "context": {
                "contextActivities": {
                    "parent": {
                        "id": "act:imaginarium.adlnet.org/xapi/imaginarium"
                    }
                }
            }
        }
        resp = self.client.post(reverse(statements), json.dumps(stmt), Authorization=self.auth, content_type="application/json", X_Experience_API_Version="1.0.0")
        self.assertEqual(resp.status_code, 200)
        stmt = {
            "verb": {
                "id": "http://special.adlnet.gov/xapi/verbs/started", 
                "display": {
                    "en-US": "started"
                }
            }, 
            "timestamp": "2013-04-11 14:49:25.376782+00:00", 
            "object": {
                "id": "act:github.com/adlnet/ADL_LRS/tree/1.0dev"
            }, 
            "actor": {
                "member": [
                    {
                        "mbox": "mailto:louo@example.com", 
                        "name": "louo"
                    }, 
                    {
                        "mbox": "mailto:tom@example.com", 
                        "name": "tom"
                    }
                ], 
                "mbox": "mailto:adllrsdevs@example.com", 
                "name": "adl lrs developers", 
                "objectType": "Group"
            }
        }
        resp = self.client.post(reverse(statements), json.dumps(stmt), Authorization=self.auth, content_type="application/json", X_Experience_API_Version="1.0.0")
        self.assertEqual(resp.status_code, 200)
        stmt = {
            "verb": {
                "id": "http://special.adlnet.gov/xapi/verbs/stopped", 
                "display": {
                    "en-US": "nixed"
                }
            },
            "timestamp": "2013-04-11 23:24:03.603184+00:00", 
            "object": {
                "timestamp": "2013-04-11 23:24:03.578795+00:00", 
                "object": {
                    "id": "act:adlnet.gov/website"
                }, 
                "actor": {
                    "mbox": "mailto:louo@example.com", 
                    "name": "louo"
                }, 
                "verb": {
                    "id": "http://special.adlnet.gov/xapi/verbs/hacked", 
                    "display": {
                        "en-US": "hax0r5"
                    }
                }, 
                "objectType": "SubStatement"
            }, 
            "actor": {
                "mbox": "mailto:timmy@example.com", 
                "name": "timmy"
            }
        }
        resp = self.client.post(reverse(statements), json.dumps(stmt), Authorization=self.auth, content_type="application/json", X_Experience_API_Version="1.0.0")
        self.assertEqual(resp.status_code, 200)
        param = {"agent":{"mbox":"mailto:louo@example.com"}, "related_agents":True}
        path = "%s?%s" % (reverse(statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        obj = json.loads(r.content)
        stmts = obj['statements']
        for s in stmts:
            if param['agent']['mbox'] not in str(s['actor']):
                if s['object']['objectType'] != "StatementRef":
                    self.assertTrue(param['agent']['mbox'] in str(s))
                else:
                    self.assertEqual(s['object']['objectType'], "StatementRef")
                    refd = Statement.objects.get(statement_id=s['object']['id']).to_dict()
                    self.assertTrue(param['agent']['mbox'] in str(refd))
            else:
                self.assertTrue(param['agent']['mbox'] in str(s['actor']))

        cnt_all = len(stmts)

        param = {"agent":{"mbox":"mailto:louo@example.com"}, "related_agents": True, "until": "2013-04-10T00:00Z"}
        path = "%s?%s" % (reverse(statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        obj = json.loads(r.content)
        stmts = obj['statements']
        self.assertTrue(len(stmts) < cnt_all)
        until = convert_to_utc(param['until'])
        for s in stmts:
            if param['agent']['mbox'] not in str(s['actor']):
                if s['object']['objectType'] != "StatementRef":
                    self.assertTrue(param['agent']['mbox'] in str(s))
                else:
                    self.assertEqual(s['object']['objectType'], "StatementRef")
                    refd = Statement.objects.get(statement_id=s['object']['id']).to_dict()
                    self.assertTrue(param['agent']['mbox'] in str(refd))
            else:
                self.assertTrue(param['agent']['mbox'] in str(s['actor']))
            self.assertTrue(convert_to_utc(s['stored']) < until)

    def test_related_agents_filter_since(self):
        stmts = [{
            "timestamp": "2013-04-10 21:25:59.583000+00:00", 
            "object": {
                "mbox": "mailto:louo@example.com", 
                "name": "louo", 
                "objectType": "Agent"
            }, 
            "actor": {
                "member": [
                    {
                        "mbox": "mailto:blobby@example.com", 
                        "name": "blobby"
                    }, 
                    {
                        "mbox": "mailto:timmy@example.com", 
                        "name": "timmy"
                    }, 
                    {
                        "mbox": "mailto:tom@example.com", 
                        "name": "tom"
                    }
                ], 
                "name": "the tourists", 
                "objectType": "Group"
            },
            "verb": {
                "id": "http://imaginarium.adlnet.org/xapi/verbs/sighted", 
                "display": {
                    "en-US": "sighted"
                }
            },
            "context": {
                "contextActivities": {
                    "parent": {
                        "id": "act:imaginarium.adlnet.org/xapi/imaginarium"
                    }
                }
            }
        },
        {
            "verb": {
                "id": "http://special.adlnet.gov/xapi/verbs/started", 
                "display": {
                    "en-US": "started"
                }
            }, 
            "timestamp": "2013-04-11 14:49:25.376782+00:00", 
            "object": {
                "id": "act:github.com/adlnet/ADL_LRS/tree/1.0dev"
            }, 
            "actor": {
                "member": [
                    {
                        "mbox": "mailto:louo@example.com", 
                        "name": "louo"
                    }, 
                    {
                        "mbox": "mailto:tom@example.com", 
                        "name": "tom"
                    }
                ], 
                "mbox": "mailto:adllrsdevs@example.com", 
                "name": "adl lrs developers", 
                "objectType": "Group"
            }
        },
        {
            "verb": {
                "id": "http://special.adlnet.gov/xapi/verbs/stopped", 
                "display": {
                    "en-US": "nixed"
                }
            },
            "timestamp": "2013-04-11 23:24:03.603184+00:00", 
            "object": {
                "timestamp": "2013-04-11 23:24:03.578795+00:00", 
                "object": {
                    "id": "act:adlnet.gov/website"
                }, 
                "actor": {
                    "mbox": "mailto:louo@example.com", 
                    "name": "louo"
                }, 
                "verb": {
                    "id": "http://special.adlnet.gov/xapi/verbs/hacked", 
                    "display": {
                        "en-US": "hax0r5"
                    }
                }, 
                "objectType": "SubStatement"
            }, 
            "actor": {
                "mbox": "mailto:timmy@example.com", 
                "name": "timmy"
            }
        }]
        response = self.client.post(reverse(statements), json.dumps(stmts), content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(response.status_code, 200)

        param = {"agent":{"mbox":"mailto:louo@example.com"}, "related_agents":True}
        path = "%s?%s" % (reverse(statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        obj = json.loads(r.content)
        stmts = obj['statements']
        for s in stmts:
            if param['agent']['mbox'] not in str(s['actor']):
                if s['object']['objectType'] != "StatementRef":
                    self.assertTrue(param['agent']['mbox'] in str(s))
                else:
                    self.assertEqual(s['object']['objectType'], "StatementRef")
                    refd = Statement.objects.get(statement_id=s['object']['id']).to_dict()
                    self.assertTrue(param['agent']['mbox'] in str(refd))
            else:
                self.assertTrue(param['agent']['mbox'] in str(s['actor']))

        cnt_all = len(stmts)
        since = stmts[int(math.floor(cnt_all/2))]['stored']
        since_cnt = int(math.floor(cnt_all/2))

        param = {"agent":{"mbox":"mailto:louo@example.com"}, "related_agents": True, "since": since}
        path = "%s?%s" % (reverse(statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        obj = json.loads(r.content)
        stmts = obj['statements']
        self.assertEqual(len(stmts), since_cnt)
        since = convert_to_utc(param['since'])
        for s in stmts:
            if param['agent']['mbox'] not in str(s['actor']):
                if s['object']['objectType'] != "StatementRef":
                    self.assertTrue(param['agent']['mbox'] in str(s))
                else:
                    self.assertEqual(s['object']['objectType'], "StatementRef")
                    refd = Statement.objects.get(statement_id=s['object']['id']).to_dict()
                    self.assertTrue(param['agent']['mbox'] in str(refd))
            else:
                self.assertTrue(param['agent']['mbox'] in str(s['actor']))
            self.assertTrue(convert_to_utc(s['stored']) > since)


    def test_since_filter_tz(self):
        stmt1_guid = str(uuid.uuid1())
        stmt1 = json.dumps({"verb":{"id": "http://adlnet.gov/expapi/verbs/created",
                "display": {"en-US":"created"}}, "object": {"id":"act:activity"},
                "actor":{"objectType":"Agent","mbox":"mailto:s@s.com"}, "timestamp":"2013-02-02T12:00:00-05:00"})

        param = {"statementId":stmt1_guid}
        path = "%s?%s" % (reverse(statements), urllib.urlencode(param))
        stmt_payload = stmt1
        resp = self.client.put(path, stmt_payload, content_type="application/json", Authorization=self.auth, X_Experience_API_Version="1.0")
        self.assertEqual(resp.status_code, 204)
        time = "2013-02-02T12:00:32-05:00"
        Statement.objects.filter(statement_id=stmt1_guid).update(stored=time)

        stmt2_guid = str(uuid.uuid1())
        stmt2 = json.dumps({"verb":{"id": "http://adlnet.gov/expapi/verbs/created",
                "display": {"en-US":"created"}}, "object": {"id":"act:activity2"},
                "actor":{"objectType":"Agent","mbox":"mailto:s@s.com"}, "timestamp":"2013-02-02T20:00:00+05:00"})

        param = {"statementId":stmt2_guid}
        path = "%s?%s" % (reverse(statements), urllib.urlencode(param))
        stmt_payload = stmt2
        resp = self.client.put(path, stmt_payload, content_type="application/json", Authorization=self.auth, X_Experience_API_Version="1.0")
        self.assertEqual(resp.status_code, 204)
        time = "2013-02-02T10:00:32-05:00"
        Statement.objects.filter(statement_id=stmt2_guid).update(stored=time)

        param = {"since": "2013-02-02T14:00Z"}
        path = "%s?%s" % (reverse(statements), urllib.urlencode(param))      
        sinceGetResponse = self.client.get(path, X_Experience_API_Version="1.0", Authorization=self.auth)

        self.assertEqual(sinceGetResponse.status_code, 200)
        rsp = sinceGetResponse.content
        self.assertIn(stmt1_guid, rsp)
        self.assertIn(stmt2_guid, rsp)

        param2 = {"since": "2013-02-02T16:00Z"}
        path2 = "%s?%s" % (reverse(statements), urllib.urlencode(param2))      
        sinceGetResponse2 = self.client.get(path2, X_Experience_API_Version="1.0", Authorization=self.auth)

        self.assertEqual(sinceGetResponse2.status_code, 200)
        rsp2 = sinceGetResponse2.content
        self.assertIn(stmt1_guid, rsp2)
        self.assertNotIn(stmt2_guid, rsp2)

    def test_verb_filter(self):
        theid = str(uuid.uuid1())
        stmt = {
        "id":theid,
        "timestamp": "2013-04-10 21:27:15.613000+00:00", 
        "object": {
            "mbox": "mailto:louo@example.com", 
            "name": "louo",
            "objectType":"Agent"
        }, 
        "actor": {
            "member": [
                {
                    "mbox": "mailto:blobby@example.com", 
                    "name": "blobby"
                }, 
                {
                    "mbox": "mailto:timmy@example.com", 
                    "name": "timmy"
                }, 
                {
                    "mbox": "mailto:tom@example.com", 
                    "name": "tom"
                }
            ], 
            "name": "the tourists", 
            "objectType": "Group"
        }, 
        "verb": {
            "id": "http://special.adlnet.gov/xapi/verbs/high-fived", 
            "display": {"en-US": "high-fived"}
        },
        "context": {
            "contextActivities": {
                "parent": {
                    "id": "act:imaginarium.adlnet.org/xapi/imaginarium"
                }
            }
        }
        }
        resp = self.client.post(reverse(statements), json.dumps(stmt), Authorization=self.auth, content_type="application/json", X_Experience_API_Version="1.0.0")
        self.assertEqual(resp.status_code, 200)
        stman_id = str(uuid.uuid1())
        stmt = {"id": stman_id,
        "verb": {
            "id": "http://special.adlnet.gov/xapi/verbs/frowned", 
            "display": {
                "en-US": "frowned upon"
            }
        }, 
        
        "timestamp": "2013-04-10 21:28:33.870000+00:00", 
        "object": {
            "id": theid, 
            "objectType": "StatementRef"
        }, 
        "actor": {
            "member": [
                {
                    "mbox": "mailto:mrx@example.com", 
                    "name": "mr x", 
                    "objectType": "Agent"
                }, 
                {
                    "mbox": "mailto:msy@example.com", 
                    "name": "ms y", 
                    "objectType": "Agent"
                }, 
                {
                    "mbox": "mailto:drdre@example.com", 
                    "name": "dr dre", 
                    "objectType": "Agent"
                }
            ], 
            "name": "Managers", 
            "objectType": "Group"
        }
        }
        resp = self.client.post(reverse(statements), json.dumps(stmt), Authorization=self.auth, content_type="application/json", X_Experience_API_Version="1.0.0")
        self.assertEqual(resp.status_code, 200)
        param = {"verb":"http://special.adlnet.gov/xapi/verbs/high-fived"}
        path = "%s?%s" % (reverse(statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        obj = json.loads(r.content)
        stmts = obj['statements']
        self.assertEqual(len(stmts), 2)

        stmt_ref_stmt_ids = [k['object']['id'] for k in stmts if k['object']['objectType']=='StatementRef']
        stmt_ids = [k['id'] for k in stmts if k['object']['objectType']!='StatementRef']
        diffs = set(stmt_ref_stmt_ids) ^ set(stmt_ids)
        self.assertFalse(diffs)

        param = {"agent":{"mbox":"mailto:drdre@example.com"},"verb":"http://special.adlnet.gov/xapi/verbs/high-fived"}
        path = "%s?%s" % (reverse(statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        obj = json.loads(r.content)
        stmts = obj['statements']
        self.assertEqual(len(stmts), 0)

    def test_registration_filter(self):
        theid = str(uuid.uuid1())
        stmt = {
        "id":theid,
        "timestamp": "2013-04-10 21:27:15.613000+00:00", 
        "object": {
            "mbox": "mailto:louo@example.com", 
            "name": "louo",
            "objectType":"Agent"
        }, 
        "actor": {
            "member": [
                {
                    "mbox": "mailto:blobby@example.com", 
                    "name": "blobby"
                }, 
                {
                    "mbox": "mailto:timmy@example.com", 
                    "name": "timmy"
                }, 
                {
                    "mbox": "mailto:tom@example.com", 
                    "name": "tom"
                }
            ], 
            "name": "the tourists", 
            "objectType": "Group"
        }, 
        "verb": {
            "id": "http://special.adlnet.gov/xapi/verbs/high-fived", 
            "display": {"en-US": "high-fived"}
        },
        "context": {
            "contextActivities": {
                "parent": {
                    "id": "act:imaginarium.adlnet.org/xapi/imaginarium"
                }
            },
            "registration":"05bb4c1a-9ddb-44a0-ba4f-52ff77811a92"
        }
        }
        resp = self.client.post(reverse(statements), json.dumps(stmt), Authorization=self.auth, content_type="application/json", X_Experience_API_Version="1.0.0")
        self.assertEqual(resp.status_code, 200)
        stmt = {
            "timestamp": "2013-04-08 17:51:38.118000+00:00", 
            "object": {
                "id": "act:adlnet.gov/JsTetris_TCAPI"
            }, 
            "actor": {
                "mbox": "mailto:tom@example.com", 
                "name": "tom"
            }, 
            "verb": {
                "id": "http://adlnet.gov/xapi/verbs/attempted", 
                "display": {"en-US": "started"}
            },
            "context": {
                "registration":"05bb4c1a-9ddb-44a0-ba4f-52ff77811a91"
            }
        }
        resp = self.client.post(reverse(statements), json.dumps(stmt), Authorization=self.auth, content_type="application/json", X_Experience_API_Version="1.0.0")
        self.assertEqual(resp.status_code, 200)
        stmt =         {
        "timestamp": "2013-04-08 21:07:20.392000+00:00", 
        "object": { 
            "id": "act:adlnet.gov/JsTetris_TCAPI", 
            "objectType": "Activity"
        }, 
        "actor": {
            "mbox": "mailto:tom@example.com", 
            "name": "tom"
        }, 
        "verb": {
            "id": "http://adlnet.gov/xapi/verbs/completed", 
            "display": {"en-US": "finished"}
        }, 
        "result": {
            "score": {
                "raw": 1918560.0, 
                "min": 0.0
            }, 
            "extensions": {
                "ext:level": "19", 
                "ext:apm": "241", 
                "ext:lines": "165", 
                "ext:time": "1128"
            }
        },
        "context": {
            "registration":"05bb4c1a-9ddb-44a0-ba4f-52ff77811a91"
        }
        }
        resp = self.client.post(reverse(statements), json.dumps(stmt), Authorization=self.auth, content_type="application/json", X_Experience_API_Version="1.0.0")
        self.assertEqual(resp.status_code, 200)
        param = {"registration":"05bb4c1a-9ddb-44a0-ba4f-52ff77811a91"}
        path = "%s?%s" % (reverse(statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        obj = json.loads(r.content)
        stmts = obj['statements']
        self.assertEqual(len(stmts), 2)

        param = {"registration":"05bb4c1a-9ddb-44a0-ba4f-52ff77811a91","verb":"http://special.adlnet.gov/xapi/verbs/high-fived"}
        path = "%s?%s" % (reverse(statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        obj = json.loads(r.content)
        stmts = obj['statements']
        self.assertEqual(len(stmts), 0)

        param = {"registration":"05bb4c1a-9ddb-44a0-ba4f-52ff77811a91","verb":"http://adlnet.gov/xapi/verbs/completed"}
        path = "%s?%s" % (reverse(statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        obj = json.loads(r.content)
        stmts = obj['statements']
        self.assertEqual(len(stmts), 1)

        param = {"agent":{"mbox":"mailto:tom@example.com"}, "registration":"05bb4c1a-9ddb-44a0-ba4f-52ff77811a91","verb":"http://adlnet.gov/xapi/verbs/completed"}
        path = "%s?%s" % (reverse(statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        obj = json.loads(r.content)
        stmts = obj['statements']
        self.assertEqual(len(stmts), 1)

        param = {"agent":{"mbox":"mailto:louo@example.com"}, "registration":"05bb4c1a-9ddb-44a0-ba4f-52ff77811a91","verb":"http://adlnet.gov/xapi/verbs/completed"}
        path = "%s?%s" % (reverse(statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        obj = json.loads(r.content)
        stmts = obj['statements']
        self.assertEqual(len(stmts), 0)

    def test_activity_filter(self):
        stmt = {
        "timestamp": "2013-04-08 21:05:48.869000+00:00", 
        "object": {
            "id": "act:adlnet.gov/JsTetris_TCAPI/level17", 
            "objectType": "Activity"
        }, 
        "actor": {
            "mbox": "mailto:tom@example.com", 
            "name": "tom",
        }, 
        "verb": {
            "id": "http://adlnet.gov/xapi/verbs/passed(to_go_beyond)", 
            "display": {"en-US": "passed"}
        }, 
        "context": {
            "contextActivities": {
                "grouping": {
                    "id": "act:adlnet.gov/JsTetris_TCAPI"
                }
            }
        }
        }
        resp = self.client.post(reverse(statements), json.dumps(stmt), Authorization=self.auth, content_type="application/json", X_Experience_API_Version="1.0.0")
        self.assertEqual(resp.status_code, 200)
        stmt = {
            "timestamp": "2013-04-08 21:07:11.459000+00:00", 
            "object": {
                "id": "act:adlnet.gov/JsTetris_TCAPI/level18"
            }, 
            "actor": {
                "mbox": "mailto:tom@example.com", 
                "name": "tom"
            }, 
            "verb": {
                "id": "http://adlnet.gov/xapi/verbs/passed(to_go_beyond)", 
                "display": {"en-US": "passed"}
            }, 
            "result": {
                "score": {
                    "raw": 1918560.0, 
                    "min": 0.0
                }
            }, 
            "context": {
                "contextActivities": {
                    "grouping": {
                        "id": "act:adlnet.gov/JsTetris_TCAPI"
                    }
                }
            }
        }
        resp = self.client.post(reverse(statements), json.dumps(stmt), Authorization=self.auth, content_type="application/json", X_Experience_API_Version="1.0.0")
        self.assertEqual(resp.status_code, 200)
        stmt = {
        "timestamp": "2013-04-08 21:07:20.392000+00:00", 
        "object": {
            "definition": {
                "type": "type:media", 
                "name": {
                    "en-US": "Js Tetris - Tin Can Prototype"
                }, 
                "description": {
                    "en-US": "A game of tetris."
                }
            }, 
            "id": "act:adlnet.gov/JsTetris_TCAPI"
        }, 
        "actor": {
            "mbox": "mailto:tom@example.com", 
            "name": "tom"
        }, 
        "verb": {
            "id": "http://adlnet.gov/xapi/verbs/completed", 
            "display": {"en-US": "finished"}
        }, 
        "result": {
            "score": {
                "raw": 1918560.0, 
                "min": 0.0
            }, 
            "extensions": {
                "ext:level": "19", 
                "ext:apm": "241", 
                "ext:lines": "165", 
                "ext:time": "1128"
            }
        }, 
        "context": {
            "contextActivities": {
                "grouping": {
                    "id": "act:adlnet.gov/JsTetris_TCAPI"
                }
            }
        }
        }
        resp = self.client.post(reverse(statements), json.dumps(stmt), Authorization=self.auth, content_type="application/json", X_Experience_API_Version="1.0.0")
        self.assertEqual(resp.status_code, 200)
        param = {"activity":"act:adlnet.gov/JsTetris_TCAPI"}
        path = "%s?%s" % (reverse(statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        obj = json.loads(r.content)
        stmts = obj['statements']
        for s in stmts:
            if param['activity'] not in str(s['object']['id']):
                self.assertEqual(s['object']['objectType'], "StatementRef")
                self.assertTrue(param['activity'] in str(Statement.objects.get(statement_id=s['object']['id']).to_dict()))
            else:
                self.assertEqual(s['object']['id'], param['activity'])

        actcnt = len(stmts)
        self.assertEqual(actcnt, 1)

        param = {"activity":"act:adlnet.gov/JsTetris_TCAPI", "related_activities":True}
        path = "%s?%s" % (reverse(statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        obj = json.loads(r.content)
        stmts = obj['statements']
        for s in stmts:
            if param['activity'] not in str(s):
                self.assertEqual(s['object']['objectType'], "StatementRef")
                self.assertTrue(param['activity'] in str(Statement.objects.get(statement_id=s['object']['id']).to_dict()))
            else:
                self.assertIn(param['activity'], str(s))

        self.assertTrue(len(stmts) > actcnt, "stmts(%s) was not greater than actcnt(%s)" % (len(stmts), actcnt))

    def test_no_activity_filter(self):
        stmt = {
        "timestamp": "2013-04-08 21:05:48.869000+00:00", 
        "object": {
            "id": "act:adlnet.gov/JsTetris_TCAPI/level17", 
            "objectType": "Activity"
        }, 
        "actor": {
            "mbox": "mailto:tom@example.com", 
            "name": "tom",
        }, 
        "verb": {
            "id": "http://adlnet.gov/xapi/verbs/passed(to_go_beyond)", 
            "display": {"en-US": "passed"}
        }, 
        "context": {
            "contextActivities": {
                "grouping": {
                    "id": "act:adlnet.gov/JsTetris_TCAPI"
                }
            }
        }
        }
        resp = self.client.post(reverse(statements), json.dumps(stmt), Authorization=self.auth, content_type="application/json", X_Experience_API_Version="1.0.0")
        self.assertEqual(resp.status_code, 200)
        stmt = {
            "timestamp": "2013-04-08 21:07:11.459000+00:00", 
            "object": {
                "id": "act:adlnet.gov/JsTetris_TCAPI/level18"
            }, 
            "actor": {
                "mbox": "mailto:tom@example.com", 
                "name": "tom"
            }, 
            "verb": {
                "id": "http://adlnet.gov/xapi/verbs/passed(to_go_beyond)", 
                "display": {"en-US": "passed"}
            }, 
            "result": {
                "score": {
                    "raw": 1918560.0, 
                    "min": 0.0
                }
            }, 
            "context": {
                "contextActivities": {
                    "grouping": {
                        "id": "act:adlnet.gov/JsTetris_TCAPI"
                    }
                }
            }
        }
        resp = self.client.post(reverse(statements), json.dumps(stmt), Authorization=self.auth, content_type="application/json", X_Experience_API_Version="1.0.0")
        self.assertEqual(resp.status_code, 200)
        actorGetResponse = self.client.post(reverse(statements), 
            {"activity":"http://notarealactivity.com"},
             content_type="application/x-www-form-urlencoded", X_Experience_API_Version="1.0", Authorization=self.auth)
        self.assertEqual(actorGetResponse.status_code, 200)
        rsp = json.loads(actorGetResponse.content)
        stmts = rsp['statements']
        self.assertEqual(len(stmts), 0)

    def test_format_agent_filter(self):
        stmt = json.dumps({"actor":{"name":"lou wolford", "mbox":"mailto:louwolford@example.com"},
                          "verb":{"id":"http://special.adlnet.gov/xapi/verb/created",
                                  "display":{"en-US":"made"}},
                          "object":{"objectType":"Group","name":"androids","mbox":"mailto:androids@example.com",
                                    "member":[{"name":"Adam Link", "mbox":"mailto:alink@example.com"},
                                              {"name":"Andrew Martin", "mbox":"mailto:amartin@example.com"},
                                              {"name":"Astro Boy", "mbox":"mailto:astroboy@example.com"},
                                              {"name":"C-3PO", "mbox":"mailto:c3po@example.com"},
                                              {"name":"R2 D2", "mbox":"mailto:r2d2@example.com"},
                                              {"name":"Marvin", "mbox":"mailto:marvin@example.com"},
                                              {"name":"Data", "mbox":"mailto:data@example.com"},
                                              {"name":"Mr. Roboto", "mbox":"mailto:mrroboto@example.com"}
                                             ]
                                   },
                          "context":{"instructor":{"name":"Isaac Asimov", "mbox":"mailto:asimov@example.com"},
                                     "team":{"objectType":"Group", "name":"team kick***", 
                                             "member":[{"name":"lou wolford","mbox":"mailto:louwolford@example.com"},
                                                       {"name":"tom creighton", "mbox":"mailto:tomcreighton@example.com"}
                                                      ]
                                             }
                                     }
                         })
        guid = str(uuid.uuid1())
        param = {"statementId":guid}
        path = "%s?%s" % (reverse(statements), urllib.urlencode(param))
        resp = self.client.put(path, stmt, content_type="application/json", Authorization=self.auth, X_Experience_API_Version="1.0")
        self.assertEqual(resp.status_code, 204)
        
        agent_params = ['name', 'mbox', 'objectType']

        param = {"agent":{"mbox":"mailto:louwolford@example.com"}}
        path = "%s?%s" % (reverse(statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        obj = json.loads(r.content)

        stmts = obj['statements']
        # only expecting the one made at the beginning of this test
        stmt_r = stmts[0]
        # remove the stuff the LRS adds
        stmt_r.pop('stored')
        stmt_r.pop('timestamp')
        stmt_r.pop('version')
        stmt_r.pop('id')
        stmt_r.pop('authority')
        orig_stmt = json.loads(stmt)

        self.assertItemsEqual(orig_stmt.keys(), stmt_r.keys())
        self.assertItemsEqual(agent_params, stmt_r['actor'].keys())
        self.assertItemsEqual(orig_stmt['object'].keys(), stmt_r['object'].keys())
        for m in stmt_r['object']['member']:
            self.assertItemsEqual(m.keys(), agent_params)
        self.assertItemsEqual(orig_stmt['context'].keys(), stmt_r['context'].keys())
        self.assertItemsEqual(agent_params, stmt_r['context']['instructor'].keys())
        self.assertItemsEqual(orig_stmt['context']['team'].keys(), stmt_r['context']['team'].keys())
        for m in stmt_r['context']['team']['member']:
            self.assertItemsEqual(m.keys(), agent_params)

        param = {"agent":{"mbox":"mailto:louwolford@example.com"}, "format":"ids"}
        path = "%s?%s" % (reverse(statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        obj = json.loads(r.content)
        stmts = obj['statements']

        agent_id_param = ['mbox']
        group_id_params = ['objectType', "mbox"]
        anon_id_params = ['objectType', "member"]

        # only expecting the one made at the beginning of this test
        stmt_r = stmts[0]
        # remove the stuff the LRS adds
        stmt_r.pop('stored')
        stmt_r.pop('timestamp')
        stmt_r.pop('version')
        stmt_r.pop('id')
        stmt_r.pop('authority')
        orig_stmt = json.loads(stmt)

        self.assertItemsEqual(orig_stmt.keys(), stmt_r.keys())
        self.assertItemsEqual(agent_id_param, stmt_r['actor'].keys())
        self.assertItemsEqual(group_id_params, stmt_r['object'].keys())
        self.assertItemsEqual(orig_stmt['context'].keys(), stmt_r['context'].keys())
        self.assertItemsEqual(agent_id_param, stmt_r['context']['instructor'].keys())
        self.assertItemsEqual(anon_id_params, stmt_r['context']['team'].keys())
        for m in stmt_r['context']['team']['member']:
            self.assertItemsEqual(m.keys(), agent_id_param)

    def test_agent_account(self):
        account = {"homePage":"http://www.adlnet.gov","name":"freakshow"}
        stmt = json.dumps({"actor": {"name": "freakshow", "account":account},
                           "verb":{"id":"http://tom.com/tested"},
                           "object":{"id":"act:tom.com/accountid"}})

        guid = str(uuid.uuid1())
        param = {"statementId":guid}
        path = "%s?%s" % (reverse(statements), urllib.urlencode(param))
        resp = self.client.put(path, stmt, content_type="application/json", Authorization=self.auth, X_Experience_API_Version="1.0")
        self.assertEqual(resp.status_code, 204)

        param = {"agent":{"account":account}}
        path = "%s?%s" % (reverse(statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        obj = json.loads(r.content)
        ss = obj['statements']
        self.assertEqual(len(ss), 1)
        s = ss[0]
        self.assertEqual(s['id'], guid)
        self.assertEqual(s['actor']['account']['name'], account['name'])
        self.assertEqual(s['actor']['account']['homePage'], account['homePage'])

        
    
    def test_activity_format(self):
        stmt = {"actor":{"name":"chair", "mbox":"mailto:chair@example.com"},
                "verb": {"id": "http://tom.com/tested","display":{"en-US":"tested","es-US":"probado", "fr":"testé"}},
                "object": {"objectType":"Activity", "id":"act:format", 
                           "definition":{"name":{"en-US":"format", "es-US":"formato", "fr":"format"},
                                         "description":{"en-US":"format used to return statement",
                                                        "es-US":"formato utilizado en este statement",
                                                        "fr":"format utilisé pour cette statement"
                                                        },
                                         "type":"type:thing"
                                        }
                          },
                "context": {"contextActivities":{"parent":[{"id":"act:statementfiltertests",
                                                            "definition":{"name":{"en-US":"statement filter", "fr":"statement filter"},
                                                                         "description":{"en-US":"unit tests","fr":"unit tests"},
                                                                         "type":"type:parent-thing"}
                                                          }]
                                                }

                            }
        }

        guid = str(uuid.uuid1())
        param = {"statementId":guid}
        path = "%s?%s" % (reverse(statements), urllib.urlencode(param))
        resp = self.client.put(path, json.dumps(stmt), content_type="application/json", Authorization=self.auth, X_Experience_API_Version="1.0")
        self.assertEqual(resp.status_code, 204)

        param = {"agent":{"mbox":"mailto:chair@example.com"}, "format":"exact"}
        path = "%s?%s" % (reverse(statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        obj = json.loads(r.content)

        exact = obj['statements'][0]
        self.assertEqual(exact['actor']['name'], stmt['actor']['name'])
        self.assertEqual(exact['actor']['mbox'], stmt['actor']['mbox'])
        self.assertEqual(exact['verb']['id'], stmt['verb']['id'])
        self.assertItemsEqual(exact['verb']['display'].keys(), stmt['verb']['display'].keys())
        self.assertEqual(exact['object']['objectType'], stmt['object']['objectType'])
        self.assertEqual(exact['object']['id'], stmt['object']['id'])
        self.assertItemsEqual(exact['object']['definition']['name'].keys(), stmt['object']['definition']['name'].keys())
        self.assertItemsEqual(exact['object']['definition']['description'].keys(), stmt['object']['definition']['description'].keys())
        self.assertEqual(exact['context']['contextActivities']['parent'][0]['id'], stmt['context']['contextActivities']['parent'][0]['id'])
        self.assertItemsEqual(exact['context']['contextActivities']['parent'][0]['definition']['name'].keys(), stmt['context']['contextActivities']['parent'][0]['definition']['name'].keys())
        self.assertItemsEqual(exact['context']['contextActivities']['parent'][0]['definition']['description'].keys(), stmt['context']['contextActivities']['parent'][0]['definition']['description'].keys())
        self.assertEqual(exact['context']['contextActivities']['parent'][0]['definition']['type'], stmt['context']['contextActivities']['parent'][0]['definition']['type'])

        param = {"agent":{"mbox":"mailto:chair@example.com"}, "format":"ids"}
        path = "%s?%s" % (reverse(statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        obj = json.loads(r.content)
        
        ids = obj['statements'][0]
        self.assertNotIn('name', ids['actor'])
        self.assertEqual(ids['actor']['mbox'], stmt['actor']['mbox'])
        self.assertEqual(ids['verb']['id'], stmt['verb']['id'])
        self.assertEqual(len(ids['verb']['display'].keys()), 1)
        self.assertNotIn('objectType', ids['object'])
        self.assertEqual(ids['object']['id'], stmt['object']['id'])
        self.assertNotIn('definition', ids['object'])
        self.assertEqual(ids['context']['contextActivities']['parent'][0]['id'], stmt['context']['contextActivities']['parent'][0]['id'])
        self.assertNotIn('definition', ids['context']['contextActivities']['parent'][0])
        
        param = {"agent":{"mbox":"mailto:chair@example.com"}, "format":"canonical"}
        path = "%s?%s" % (reverse(statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        obj = json.loads(r.content)
        
        canon_enus = obj['statements'][0]
        self.assertEqual(canon_enus['actor']['name'], stmt['actor']['name'])
        self.assertEqual(canon_enus['actor']['mbox'], stmt['actor']['mbox'])
        self.assertEqual(canon_enus['verb']['id'], stmt['verb']['id'])
        self.assertEqual(len(canon_enus['verb']['display'].keys()), 1)
        self.assertEqual(canon_enus['object']['objectType'], stmt['object']['objectType'])
        self.assertEqual(canon_enus['object']['id'], stmt['object']['id'])
        self.assertEqual(len(canon_enus['object']['definition']['name'].keys()), 1)
        self.assertIn(canon_enus['object']['definition']['name'].keys()[0], stmt['object']['definition']['name'].keys())
        self.assertEqual(len(canon_enus['object']['definition']['description'].keys()), 1)
        self.assertIn(canon_enus['object']['definition']['description'].keys()[0], stmt['object']['definition']['description'].keys())
        self.assertEqual(canon_enus['context']['contextActivities']['parent'][0]['id'], stmt['context']['contextActivities']['parent'][0]['id'])
        self.assertEqual(len(canon_enus['context']['contextActivities']['parent'][0]['definition']['name'].keys()), 1)
        self.assertIn(canon_enus['context']['contextActivities']['parent'][0]['definition']['name'].keys()[0], stmt['context']['contextActivities']['parent'][0]['definition']['name'].keys())
        self.assertEqual(len(canon_enus['context']['contextActivities']['parent'][0]['definition']['description'].keys()), 1)
        self.assertIn(canon_enus['context']['contextActivities']['parent'][0]['definition']['description'].keys()[0], stmt['context']['contextActivities']['parent'][0]['definition']['description'].keys())
        self.assertEqual(canon_enus['context']['contextActivities']['parent'][0]['definition']['type'], stmt['context']['contextActivities']['parent'][0]['definition']['type'])

        param = {"agent":{"mbox":"mailto:chair@example.com"}, "format":"canonical"}
        path = "%s?%s" % (reverse(statements),urllib.urlencode(param))
        r = self.client.get(path, Accept_Language="fr", X_Experience_API_Version="1.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        obj = json.loads(r.content)
        
        canon_fr = obj['statements'][0]
        self.assertEqual(canon_fr['actor']['name'], stmt['actor']['name'])
        self.assertEqual(canon_fr['actor']['mbox'], stmt['actor']['mbox'])
        self.assertEqual(canon_fr['verb']['id'], stmt['verb']['id'])
        self.assertEqual(len(canon_fr['verb']['display'].keys()), 1)
        self.assertEqual(canon_fr['object']['objectType'], stmt['object']['objectType'])
        self.assertEqual(canon_fr['object']['id'], stmt['object']['id'])
        self.assertEqual(len(canon_fr['object']['definition']['name'].keys()), 1)
        self.assertIn(canon_fr['object']['definition']['name'].keys()[0], stmt['object']['definition']['name'].keys())
        self.assertEqual(len(canon_fr['object']['definition']['description'].keys()), 1)
        self.assertIn(canon_fr['object']['definition']['description'].keys()[0], stmt['object']['definition']['description'].keys())
        self.assertEqual(canon_fr['context']['contextActivities']['parent'][0]['id'], stmt['context']['contextActivities']['parent'][0]['id'])
        self.assertEqual(len(canon_fr['context']['contextActivities']['parent'][0]['definition']['name'].keys()), 1)
        self.assertIn(canon_fr['context']['contextActivities']['parent'][0]['definition']['name'].keys()[0], stmt['context']['contextActivities']['parent'][0]['definition']['name'].keys())
        self.assertEqual(len(canon_fr['context']['contextActivities']['parent'][0]['definition']['description'].keys()), 1)
        self.assertIn(canon_fr['context']['contextActivities']['parent'][0]['definition']['description'].keys()[0], stmt['context']['contextActivities']['parent'][0]['definition']['description'].keys())
        self.assertEqual(canon_fr['context']['contextActivities']['parent'][0]['definition']['type'], stmt['context']['contextActivities']['parent'][0]['definition']['type'])

        self.assertNotEqual(canon_enus['object']['definition']['name'].keys()[0],canon_fr['object']['definition']['name'].keys()[0])
        self.assertNotEqual(canon_enus['object']['definition']['description'].keys()[0],canon_fr['object']['definition']['description'].keys()[0])
        self.assertNotEqual(canon_enus['context']['contextActivities']['parent'][0]['definition']['name'].keys()[0], canon_fr['context']['contextActivities']['parent'][0]['definition']['name'].keys()[0])
        self.assertNotEqual(canon_enus['context']['contextActivities']['parent'][0]['definition']['description'].keys()[0], canon_fr['context']['contextActivities']['parent'][0]['definition']['description'].keys()[0])
        
    def single_stmt_get_canonical(self):
        ex_stmt = {
            "actor":{"name":"chair", "mbox":"mailto:chair@example.com"},
                "verb": {"id": "http://tom.com/tested","display":{"en-US":"tested","es-US":"probado", "fr":"testé"}},
                "object": {"objectType":"Activity", "id":"act:tom.com/objs/heads", 
                           "definition":{"name":{"en-US":"format", "es-US":"formato", "fr":"format"},
                                         "description":{"en-US":"format used to return statement",
                                                        "es-US":"formato utilizado en este statement",
                                                        "fr":"format utilisé pour cette statement"
                                                        },
                                         "type":"type:thing"
                                        }
                          }
        }

        guid = str(uuid.uuid1())
        param = {"statementId":guid}
        path = "%s?%s" % (reverse(statements), urllib.urlencode(param))
        resp = self.client.put(path, json.dumps(ex_stmt), content_type="application/json", Authorization=self.auth, X_Experience_API_Version="1.0")
        self.assertEqual(resp.status_code, 204)

        stmt_id = str(uuid.uuid1())
        stmt = {
            "id": stmt_id,
            "actor":{"mbox":"mailto:tom@example.com"},
            "verb":{"id":"http://tom.com/verb/butted"},
            "object":{"id":"act:tom.com/objs/heads"}
        }
        
        param = {"statementId": stmt_id}
        path = "%s?%s" % (reverse(statements),urllib.urlencode(param))
        response = self.client.put(path, json.dumps(stmt), content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(response.status_code, 204)

        param["format"] = "canonical"
        path = "%s?%s" % (reverse(statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        stmt_obj = json.loads(r.content)
        self.assertIn('definition', stmt_obj['object'])

        param["format"] = "exact"
        path = "%s?%s" % (reverse(statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        stmt_obj = json.loads(r.content)
        self.assertNotIn('definition', stmt_obj['object'])

    def test_voidedStatementId(self):
        stmt = {"actor":{"mbox":"mailto:dog@example.com"},
                "verb":{"id":"http://tom.com/verb/ate"},
                "object":{"id":"act:my/homework"}
        }
        guid = str(uuid.uuid1())
        param = {"statementId":guid}
        path = "%s?%s" % (reverse(statements), urllib.urlencode(param))
        resp = self.client.put(path, json.dumps(stmt), content_type="application/json", Authorization=self.auth, X_Experience_API_Version="1.0")
        self.assertEqual(resp.status_code, 204)

        param = {"statementId":guid}
        path = "%s?%s" % (reverse(statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        
        obj = json.loads(r.content)
        self.assertEqual(obj['actor']['mbox'], stmt['actor']['mbox'])
        self.assertEqual(obj['verb']['id'], stmt['verb']['id'])
        self.assertEqual(obj['object']['id'], stmt['object']['id'])
        
        stmtv = {"actor":{"mbox":"mailto:darnhonestparents@example.com"},
                 "verb":{"id":"http://adlnet.gov/expapi/verbs/voided"},
                 "object":{"objectType":"StatementRef","id":guid}
        }
        guidv = str(uuid.uuid1())
        paramv = {"statementId":guidv}
        pathv = "%s?%s" % (reverse(statements), urllib.urlencode(paramv))
        respv = self.client.put(pathv, json.dumps(stmtv), content_type="application/json", Authorization=self.auth, X_Experience_API_Version="1.0")
        self.assertEqual(respv.status_code, 204)

        paramv = {"statementId":guidv}
        pathv = "%s?%s" % (reverse(statements),urllib.urlencode(paramv))
        r = self.client.get(pathv, X_Experience_API_Version="1.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        objv = json.loads(r.content)
        self.assertEqual(objv['actor']['mbox'], stmtv['actor']['mbox'])
        self.assertEqual(objv['verb']['id'], stmtv['verb']['id'])
        self.assertEqual(objv['object']['id'], stmtv['object']['id'])

        # first statement is voided now... should get a 404 if we try to request it
        param = {"statementId":guid}
        path = "%s?%s" % (reverse(statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 404)

        # but we can get it using the voidedStatementId param
        param = {"voidedStatementId":guid}
        path = "%s?%s" % (reverse(statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        
        obj = json.loads(r.content)
        self.assertEqual(obj['actor']['mbox'], stmt['actor']['mbox'])
        self.assertEqual(obj['verb']['id'], stmt['verb']['id'])
        self.assertEqual(obj['object']['id'], stmt['object']['id'])

    def test_attachments(self):
        stmt = [{"actor":{"mbox":"mailto:tom@example.com"},
            "verb":{"id":"http://tom.com/verb/butted"},
            "object":{"id":"act:tom.com/objs/heads"},
            "attachments": [
                {"usageType": "http://example.com/attachment-usage/test11",
                "display": {"en-US": "A test attachment11"},
                "description": {"en-US": "A test attachment (description)11"},
                "contentType": "text/plain; charset=utf-8",
                "length": 27,
                "sha2":""},
                {"usageType": "http://example.com/attachment-usage/test12",
                "display": {"en-US": "A test attachment12"},
                "description": {"en-US": "A test attachment (description)12"},
                "contentType": "text/plain; charset=utf-8",
                "length": 27,
                "sha2":""}]},
            {"actor":{"mbox":"mailto:tom2@example.com"},
            "verb":{"id":"http://tom.com/verb/butted"},
            "object":{"id":"act:tom.com/objs/heads2"},
            "attachments": [
                {"usageType": "http://example.com/attachment-usage/test21",
                "display": {"en-US": "A test attachment21"},
                "description": {"en-US": "A test attachment (description)21"},
                "contentType": "text/plain; charset=utf-8",
                "length": 23,
                "sha2":""},
                {"usageType": "http://example.com/attachment-usage/test22",
                "display": {"en-US": "A test attachment22"},
                "description": {"en-US": "A test attachment (description)22"},
                "contentType": "text/plain; charset=utf-8",
                "length": 23,
                "sha2":""}]}
            ]

        message = MIMEMultipart(boundary="myboundary")
        txt11 = u"This is a text attachment11"
        txtsha11 = hashlib.sha256(txt11).hexdigest()
        stmt[0]['attachments'][0]["sha2"] = str(txtsha11)
        
        txt12 = u"This is a text attachment12"
        txtsha12 = hashlib.sha256(txt12).hexdigest()
        stmt[0]['attachments'][1]['sha2'] = str(txtsha12)

        txt21 = u"This is a text attachment21"
        txtsha21 = hashlib.sha256(txt21).hexdigest()
        stmt[1]['attachments'][0]['sha2'] = str(txtsha21)

        txt22 = u"This is a text attachment22"
        txtsha22 = hashlib.sha256(txt22).hexdigest()
        stmt[1]['attachments'][1]['sha2'] = str(txtsha22)

        stmtdata = MIMEApplication(json.dumps(stmt), _subtype="json", _encoder=json.JSONEncoder)
        textdata11 = MIMEText(txt11, 'plain', 'utf-8')
        textdata12 = MIMEText(txt12, 'plain', 'utf-8')
        textdata21 = MIMEText(txt21, 'plain', 'utf-8')
        textdata22 = MIMEText(txt22, 'plain', 'utf-8')
 
        textdata11.add_header('X-Experience-API-Hash', txtsha11)
        textdata12.add_header('X-Experience-API-Hash', txtsha12)
        textdata21.add_header('X-Experience-API-Hash', txtsha21)
        textdata22.add_header('X-Experience-API-Hash', txtsha22)

        message.attach(stmtdata)
        message.attach(textdata11)
        message.attach(textdata12)
        message.attach(textdata21)
        message.attach(textdata22)
        
        r = self.client.post(reverse(statements), message.as_string(), content_type="multipart/mixed",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(r.status_code, 200)

        param = {"attachments": True}
        path = "%s?%s" % (reverse(statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], 'multipart/mixed; boundary=ADL_LRS---------')

    def test_attachments_no_payload(self):
        stmt = {"actor":{"mbox":"mailto:tom@example.com"},
            "verb":{"id":"http://tom.com/verb/butted"},
            "object":{"id":"act:tom.com/objs/heads"},
            "attachments": [
            {"usageType": "http://example.com/attachment-usage/test",
            "display": {"en-US": "A test attachment"},
            "description": {"en-US": "A test attachment (description)"},
            "contentType": "text/plain; charset=utf-8",
            "length": 27,
            "fileUrl": "http://my/file/url"}]}
        
        response = self.client.post(reverse(statements), json.dumps(stmt), content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(response.status_code, 200)

        param = {"attachments": True}
        path = "%s?%s" % (reverse(statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], 'application/json')
        obj_from_json = json.loads(r.content)
        self.assertIn('statements', obj_from_json.keys())
        self.assertIn('more', obj_from_json.keys())
        self.assertIn('attachments', obj_from_json['statements'][0])

    def test_attachments_no_payload_no_attach_param(self):
        stmt = {"actor":{"mbox":"mailto:tom@example.com"},
            "verb":{"id":"http://tom.com/verb/butted"},
            "object":{"id":"act:tom.com/objs/heads"},
            "attachments": [
            {"usageType": "http://example.com/attachment-usage/test",
            "display": {"en-US": "A test attachment"},
            "description": {"en-US": "A test attachment (description)"},
            "contentType": "text/plain; charset=utf-8",
            "length": 27,
            "fileUrl": "http://my/file/url"}]}
        
        response = self.client.post(reverse(statements), json.dumps(stmt), content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(response.status_code, 200)

        r = self.client.get(reverse(statements), X_Experience_API_Version="1.0.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], 'application/json')
        obj_from_json = json.loads(r.content)
        self.assertIn('statements', obj_from_json.keys())
        self.assertIn('more', obj_from_json.keys())
        self.assertIn('attachments', obj_from_json['statements'][0])

    def test_attachments_no_payload_single_stmt_get(self):
        stmt_id = str(uuid.uuid1())
        stmt = {"id": stmt_id,
            "actor":{"mbox":"mailto:tom@example.com"},
            "verb":{"id":"http://tom.com/verb/butted"},
            "object":{"id":"act:tom.com/objs/heads"},
            "attachments": [
            {"usageType": "http://example.com/attachment-usage/test",
            "display": {"en-US": "A test attachment"},
            "description": {"en-US": "A test attachment (description)"},
            "contentType": "text/plain; charset=utf-8",
            "length": 27,
            "fileUrl": "http://my/file/url"}]}
        
        param = {"statementId": stmt_id}
        path = "%s?%s" % (reverse(statements),urllib.urlencode(param))
        response = self.client.put(path, json.dumps(stmt), content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(response.status_code, 204)

        param["attachments"] = True
        path = "%s?%s" % (reverse(statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], 'application/json')

    def test_attachments_payload_single_stmt_get(self):
        stmt_id = str(uuid.uuid1())
        stmt = {"id": stmt_id,
            "actor":{"mbox":"mailto:tom@example.com"},
            "verb":{"id":"http://tom.com/verb/butted"},
            "object":{"id":"act:tom.com/objs/heads"},
            "attachments": [
                {"usageType": "http://example.com/attachment-usage/test11",
                "display": {"en-US": "A test attachment11"},
                "description": {"en-US": "A test attachment (description)11"},
                "contentType": "text/plain; charset=utf-8",
                "length": 27,
                "sha2":""}]}

        message = MIMEMultipart(boundary="myboundary")
        txt11 = u"This is a text attachment11"
        txtsha11 = hashlib.sha256(txt11).hexdigest()
        stmt['attachments'][0]["sha2"] = str(txtsha11)

        stmtdata = MIMEApplication(json.dumps(stmt), _subtype="json", _encoder=json.JSONEncoder)
        textdata11 = MIMEText(txt11, 'plain', 'utf-8')

        textdata11.add_header('X-Experience-API-Hash', txtsha11)

        message.attach(stmtdata)
        message.attach(textdata11)
                
        param = {"statementId": stmt_id}
        path = "%s?%s" % (reverse(statements),urllib.urlencode(param))
        response = self.client.put(path, message.as_string(), content_type="multipart/mixed",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(response.status_code, 204)

        param["attachments"] = True
        path = "%s?%s" % (reverse(statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], 'multipart/mixed; boundary=ADL_LRS---------')

    def test_more_attachments(self):
        settings.SERVER_STMT_LIMIT=2
        stmts =[
            {"actor":{"mbox":"mailto:tom@example.com"},
            "verb":{"id":"http://tom.com/verb/butted"},
            "object":{"id":"act:tom.com/objs/heads1"},
            "attachments": [
                {"usageType": "http://example.com/attachment-usage/test11",
                "display": {"en-US": "A test attachment11"},
                "description": {"en-US": "A test attachment (description)11"},
                "contentType": "text/plain; charset=utf-8",
                "length": 27,
                "fileUrl":"http://my/test/url11"},
                {"usageType": "http://example.com/attachment-usage/test12",
                "display": {"en-US": "A test attachment12"},
                "description": {"en-US": "A test attachment (description)12"},
                "contentType": "text/plain; charset=utf-8",
                "length": 27,
                "fileUrl":"http://my/test/url12"}]},
            {"actor":{"mbox":"mailto:tom2@example.com"},
            "verb":{"id":"http://tom.com/verb/butted"},
            "object":{"id":"act:tom.com/objs/heads2"},
            "attachments": [
                {"usageType": "http://example.com/attachment-usage/test21",
                "display": {"en-US": "A test attachment21"},
                "description": {"en-US": "A test attachment (description)21"},
                "contentType": "text/plain; charset=utf-8",
                "length": 23,
                "fileUrl":"http://my/test/url21"},
                {"usageType": "http://example.com/attachment-usage/test22",
                "display": {"en-US": "A test attachment22"},
                "description": {"en-US": "A test attachment (description)22"},
                "contentType": "text/plain; charset=utf-8",
                "length": 23,
                "fileUrl":"http://my/test/url22"}]},
            {"actor":{"mbox":"mailto:tom@example.com"},
            "verb":{"id":"http://tom.com/verb/butted"},
            "object":{"id":"act:tom.com/objs/heads3"},
            "attachments": [
                {"usageType": "http://example.com/attachment-usage/test31",
                "display": {"en-US": "A test attachment31"},
                "description": {"en-US": "A test attachment (description)31"},
                "contentType": "text/plain; charset=utf-8",
                "length": 27,
                "fileUrl":"http://my/test/url31"},
                {"usageType": "http://example.com/attachment-usage/test32",
                "display": {"en-US": "A test attachment32"},
                "description": {"en-US": "A test attachment (description)32"},
                "contentType": "text/plain; charset=utf-8",
                "length": 27,
                "fileUrl":"http://my/test/url32"}]},
            {"actor":{"mbox":"mailto:tom2@example.com"},
            "verb":{"id":"http://tom.com/verb/butted"},
            "object":{"id":"act:tom.com/objs/heads4"},
            "attachments": [
                {"usageType": "http://example.com/attachment-usage/test41",
                "display": {"en-US": "A test attachment41"},
                "description": {"en-US": "A test attachment (description)41"},
                "contentType": "text/plain; charset=utf-8",
                "length": 23,
                "fileUrl":"http://my/test/url41"},
                {"usageType": "http://example.com/attachment-usage/test42",
                "display": {"en-US": "A test attachment42"},
                "description": {"en-US": "A test attachment (description)42"},
                "contentType": "text/plain; charset=utf-8",
                "length": 23,
                "fileUrl":"http://my/test/url42"}]}
        ]
        response = self.client.post(reverse(statements), json.dumps(stmts), content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(response.status_code, 200)

        param= {"attachments":True}
        path = "%s?%s" % (reverse(statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], 'application/json')
        obj_from_json = json.loads(r.content)
        self.assertEqual(len(obj_from_json['statements']), 2)
        self.assertIn('attachments', obj_from_json['statements'][0].keys())
        self.assertIn('attachments', obj_from_json['statements'][1].keys())        

        resp_url = obj_from_json['more']
        resp_id = resp_url[-32:]

        more_get = self.client.get(reverse(statements_more,kwargs={'more_id':resp_id}),
            X_Experience_API_Version="1.0.0",HTTP_AUTHORIZATION=self.auth)
        self.assertEqual(more_get.status_code, 200)
        self.assertEqual(more_get['Content-Type'], 'application/json')
        more_obj = json.loads(more_get.content)
        self.assertEqual(len(more_obj['statements']), 2)
        self.assertIn('attachments', more_obj['statements'][0].keys())
        self.assertIn('attachments', more_obj['statements'][1].keys())        

    def test_more_attachments_with_payloads(self):
        settings.SERVER_STMT_LIMIT=2
        stmts =[
            {"actor":{"mbox":"mailto:tom@example.com"},
            "verb":{"id":"http://tom.com/verb/butted"},
            "object":{"id":"act:tom.com/objs/heads1"},
            "attachments": [
                {"usageType": "http://example.com/attachment-usage/test1",
                "display": {"en-US": "A test attachment11"},
                "description": {"en-US": "A test attachment (description)1"},
                "contentType": "text/plain; charset=utf-8",
                "length": 27,
                "sha2":""}]},
            {"actor":{"mbox":"mailto:tom2@example.com"},
            "verb":{"id":"http://tom.com/verb/butted"},
            "object":{"id":"act:tom.com/objs/heads2"},
            "attachments": [
                {"usageType": "http://example.com/attachment-usage/test2",
                "display": {"en-US": "A test attachment21"},
                "description": {"en-US": "A test attachment (description)2"},
                "contentType": "text/plain; charset=utf-8",
                "length": 23,
                "sha2":""}]},
            {"actor":{"mbox":"mailto:tom@example.com"},
            "verb":{"id":"http://tom.com/verb/butted"},
            "object":{"id":"act:tom.com/objs/heads3"},
            "attachments": [
                {"usageType": "http://example.com/attachment-usage/test3",
                "display": {"en-US": "A test attachment3"},
                "description": {"en-US": "A test attachment (description)3"},
                "contentType": "text/plain; charset=utf-8",
                "length": 27,
                "sha2":""}]},
            {"actor":{"mbox":"mailto:tom2@example.com"},
            "verb":{"id":"http://tom.com/verb/butted"},
            "object":{"id":"act:tom.com/objs/heads4"},
            "attachments": [
                {"usageType": "http://example.com/attachment-usage/test4",
                "display": {"en-US": "A test attachment4"},
                "description": {"en-US": "A test attachment (description)4"},
                "contentType": "text/plain; charset=utf-8",
                "length": 23,
                "sha2":""}]}
        ]
        message = MIMEMultipart(boundary="myboundary")
        txt1 = u"This is a text attachment1"
        txtsha1 = hashlib.sha256(txt1).hexdigest()
        stmts[0]['attachments'][0]["sha2"] = str(txtsha1)
        
        txt2 = u"This is a text attachment2"
        txtsha2 = hashlib.sha256(txt2).hexdigest()
        stmts[1]['attachments'][0]['sha2'] = str(txtsha2)

        txt3 = u"This is a text attachment3"
        txtsha3 = hashlib.sha256(txt3).hexdigest()
        stmts[2]['attachments'][0]['sha2'] = str(txtsha3)

        txt4 = u"This is a text attachment4"
        txtsha4 = hashlib.sha256(txt4).hexdigest()
        stmts[3]['attachments'][0]['sha2'] = str(txtsha4)

        stmtdata = MIMEApplication(json.dumps(stmts), _subtype="json", _encoder=json.JSONEncoder)
        textdata1 = MIMEText(txt1, 'plain', 'utf-8')
        textdata2 = MIMEText(txt2, 'plain', 'utf-8')
        textdata3 = MIMEText(txt3, 'plain', 'utf-8')
        textdata4 = MIMEText(txt4, 'plain', 'utf-8')
 
        textdata1.add_header('X-Experience-API-Hash', txtsha1)
        textdata2.add_header('X-Experience-API-Hash', txtsha2)
        textdata3.add_header('X-Experience-API-Hash', txtsha3)
        textdata4.add_header('X-Experience-API-Hash', txtsha4)

        message.attach(stmtdata)
        message.attach(textdata1)
        message.attach(textdata2)
        message.attach(textdata3)
        message.attach(textdata4)

        r = self.client.post(reverse(statements), message.as_string(), content_type="multipart/mixed",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(r.status_code, 200)

        param= {"attachments":True}
        path = "%s?%s" % (reverse(statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], 'multipart/mixed; boundary=ADL_LRS---------')
        headers_list= [txtsha1, txtsha2, txtsha3,txtsha4]
        payload_list = [u"This is a text attachment1",u"This is a text attachment2",u"This is a text attachment3",u"This is a text attachment4"]
        msg = message_from_string(r.content)
        parts = []


        for part in msg.walk():
            parts.append(part)

        self.assertEqual(parts[0].get('Content-Type'), 'multipart/mixed; boundary="ADL_LRS---------"')
        self.assertEqual(parts[1].get('Content-Type'), 'application/json')
        returned_json = json.loads(parts[1].get_payload())
        self.assertEqual(len(returned_json['statements']), 2)
        resp_url = returned_json['more']
        resp_id = resp_url[-32:]        

        for part in parts[2:]:
            self.assertIn(part._payload, payload_list)
            self.assertIn(part.get("X-Experience-API-Hash"), headers_list)
            self.assertEqual(part.get('Content-Type'), "application/octet-stream")
            self.assertEqual(part.get('Content-Transfer-Encoding'), 'binary')

        more_get = self.client.get(reverse(statements_more,kwargs={'more_id':resp_id}),
            X_Experience_API_Version="1.0.0",HTTP_AUTHORIZATION=self.auth)
        self.assertEqual(more_get.status_code, 200)
        msg = message_from_string(more_get.content)
        parts = []

        for part in msg.walk():
            parts.append(part)

        self.assertEqual(parts[0].get('Content-Type'), 'multipart/mixed; boundary="ADL_LRS---------"')
        self.assertEqual(parts[1].get('Content-Type'), 'application/json')
        returned_json = json.loads(parts[1].get_payload())
        self.assertEqual(len(returned_json['statements']), 2)

        for part in parts[2:]:
            self.assertIn(part._payload, payload_list)
            self.assertIn(part.get("X-Experience-API-Hash"), headers_list)
            self.assertEqual(part.get('Content-Type'), "application/octet-stream")
            self.assertEqual(part.get('Content-Transfer-Encoding'), 'binary')


    def test_more_attachments_with_payloads_no_attach_param(self):
        settings.SERVER_STMT_LIMIT=2
        stmts =[
            {"actor":{"mbox":"mailto:tom@example.com"},
            "verb":{"id":"http://tom.com/verb/butted"},
            "object":{"id":"act:tom.com/objs/heads1"},
            "attachments": [
                {"usageType": "http://example.com/attachment-usage/test1",
                "display": {"en-US": "A test attachment11"},
                "description": {"en-US": "A test attachment (description)1"},
                "contentType": "text/plain; charset=utf-8",
                "length": 27,
                "sha2":""}]},
            {"actor":{"mbox":"mailto:tom2@example.com"},
            "verb":{"id":"http://tom.com/verb/butted"},
            "object":{"id":"act:tom.com/objs/heads2"},
            "attachments": [
                {"usageType": "http://example.com/attachment-usage/test2",
                "display": {"en-US": "A test attachment21"},
                "description": {"en-US": "A test attachment (description)2"},
                "contentType": "text/plain; charset=utf-8",
                "length": 23,
                "sha2":""}]},
            {"actor":{"mbox":"mailto:tom@example.com"},
            "verb":{"id":"http://tom.com/verb/butted"},
            "object":{"id":"act:tom.com/objs/heads3"},
            "attachments": [
                {"usageType": "http://example.com/attachment-usage/test3",
                "display": {"en-US": "A test attachment3"},
                "description": {"en-US": "A test attachment (description)3"},
                "contentType": "text/plain; charset=utf-8",
                "length": 27,
                "sha2":""}]},
            {"actor":{"mbox":"mailto:tom2@example.com"},
            "verb":{"id":"http://tom.com/verb/butted"},
            "object":{"id":"act:tom.com/objs/heads4"},
            "attachments": [
                {"usageType": "http://example.com/attachment-usage/test4",
                "display": {"en-US": "A test attachment4"},
                "description": {"en-US": "A test attachment (description)4"},
                "contentType": "text/plain; charset=utf-8",
                "length": 23,
                "sha2":""}]}
        ]
        message = MIMEMultipart(boundary="myboundary")
        txt1 = u"This is a text attachment1"
        txtsha1 = hashlib.sha256(txt1).hexdigest()
        stmts[0]['attachments'][0]["sha2"] = str(txtsha1)
        
        txt2 = u"This is a text attachment2"
        txtsha2 = hashlib.sha256(txt2).hexdigest()
        stmts[1]['attachments'][0]['sha2'] = str(txtsha2)

        txt3 = u"This is a text attachment3"
        txtsha3 = hashlib.sha256(txt3).hexdigest()
        stmts[2]['attachments'][0]['sha2'] = str(txtsha3)

        txt4 = u"This is a text attachment4"
        txtsha4 = hashlib.sha256(txt4).hexdigest()
        stmts[3]['attachments'][0]['sha2'] = str(txtsha4)

        stmtdata = MIMEApplication(json.dumps(stmts), _subtype="json", _encoder=json.JSONEncoder)
        textdata1 = MIMEText(txt1, 'plain', 'utf-8')
        textdata2 = MIMEText(txt2, 'plain', 'utf-8')
        textdata3 = MIMEText(txt3, 'plain', 'utf-8')
        textdata4 = MIMEText(txt4, 'plain', 'utf-8')
 
        textdata1.add_header('X-Experience-API-Hash', txtsha1)
        textdata2.add_header('X-Experience-API-Hash', txtsha2)
        textdata3.add_header('X-Experience-API-Hash', txtsha3)
        textdata4.add_header('X-Experience-API-Hash', txtsha4)

        message.attach(stmtdata)
        message.attach(textdata1)
        message.attach(textdata2)
        message.attach(textdata3)
        message.attach(textdata4)

        r = self.client.post(reverse(statements), message.as_string(), content_type="multipart/mixed",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(r.status_code, 200)

        param= {"attachments":False}
        path = "%s?%s" % (reverse(statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version="1.0.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], 'application/json')
        obj_from_json = json.loads(r.content)

        resp_url = obj_from_json['more']
        resp_id = resp_url[-32:]

        more_get = self.client.get(reverse(statements_more,kwargs={'more_id':resp_id}),
            X_Experience_API_Version="1.0.0",HTTP_AUTHORIZATION=self.auth)
        self.assertEqual(more_get.status_code, 200)
        self.assertEqual(more_get['Content-Type'], 'application/json')
         