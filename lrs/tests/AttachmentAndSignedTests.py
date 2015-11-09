import json
import base64
import uuid
import urllib
import hashlib
import os

from datetime import datetime
from email import message_from_string
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

from django.test import TestCase
from django.core.urlresolvers import reverse
from django.utils.timezone import utc
from django.conf import settings

from ..models import Statement, StatementAttachment
from ..views import statements
from ..utils.jws import JWS
from adl_lrs.views import register

class AttachmentAndSignedTests(TestCase):
    @classmethod
    def setUpClass(cls):
        print "\n%s" % __name__

    def setUp(self):
        self.username = "tester1"
        self.email = "test1@tester.com"
        self.password = "test"
        self.auth = "Basic %s" % base64.b64encode("%s:%s" % (self.username, self.password))
        form = {"username":self.username, "email":self.email,"password":self.password,"password2":self.password}
        self.client.post(reverse(register),form, X_Experience_API_Version=settings.XAPI_VERSION)

        self.username2 = "tester2"
        self.email2 = "test2@tester.com"
        self.password2 = "test2"
        self.auth2 = "Basic %s" % base64.b64encode("%s:%s" % (self.username2, self.password2))
        form2 = {"username":self.username2, "email":self.email2,"password":self.password2,"password2":self.password2}
        self.client.post(reverse(register),form2, X_Experience_API_Version=settings.XAPI_VERSION)

        self.firstTime = str(datetime.utcnow().replace(tzinfo=utc).isoformat())
        self.guid1 = str(uuid.uuid1())
       
    def tearDown(self):
        attach_folder_path = os.path.join(settings.MEDIA_ROOT, "attachment_payloads")
        for the_file in os.listdir(attach_folder_path):
            file_path = os.path.join(attach_folder_path, the_file)
            try:
                os.unlink(file_path)
            except Exception, e:
                raise e
    def test_multipart(self):
        stmt = {"actor":{"mbox":"mailto:tom@example.com"},
            "verb":{"id":"http://tom.com/verb/butted"},
            "object":{"id":"act:tom.com/objs/heads"},
            "attachments": [
            {"usageType": "http://example.com/attachment-usage/test",
            "display": {"en-US": "A test attachment"},
            "description": {"en-US": "A test attachment (description)"},
            "contentType": "text/plain; charset=utf-8",
            "length": 27,
            "sha2":""}]}

        message = MIMEMultipart(boundary="myboundary")
        txt = u"howdy.. this is a text attachment"
        txtsha = hashlib.sha256(txt).hexdigest()
        stmt['attachments'][0]["sha2"] = str(txtsha)
        
        stmtdata = MIMEApplication(json.dumps(stmt), _subtype="json", _encoder=json.JSONEncoder)
        textdata = MIMEText(txt, 'plain', 'utf-8')
        textdata.add_header('X-Experience-API-Hash', txtsha)
        message.attach(stmtdata)
        message.attach(textdata)

        r = self.client.post(reverse(statements), message.as_string(),
            content_type='multipart/mixed; boundary=myboundary', Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(r.status_code, 200)

    def test_multiple_stmt_multipart(self):
        stmt = [{"actor":{"mbox":"mailto:tom@example.com"},
            "verb":{"id":"http://tom.com/verb/butted"},
            "object":{"id":"act:tom.com/objs/heads"},
            "attachments": [
            {"usageType": "http://example.com/attachment-usage/test",
            "display": {"en-US": "A test attachment"},
            "description": {"en-US": "A test attachment (description)"},
            "contentType": "text/plain; charset=utf-8",
            "length": 27,
            "sha2":""}]},
            {"actor":{"mbox":"mailto:tom2@example.com"},
            "verb":{"id":"http://tom.com/verb/butted"},
            "object":{"id":"act:tom.com/objs/heads2"},
            "attachments": [
            {"usageType": "http://example.com/attachment-usage/test2",
            "display": {"en-US": "A test attachment2"},
            "description": {"en-US": "A test attachment (description)2"},
            "contentType": "text/plain; charset=utf-8",
            "length": 23,
            "sha2":""}]}
            ]

        message = MIMEMultipart(boundary="myboundary")
        txt = u"howdy.. this is a text attachment"
        txtsha = hashlib.sha256(txt).hexdigest()
        stmt[0]['attachments'][0]["sha2"] = str(txtsha)
        
        txt2 = u"This is second attachment."
        txtsha2 = hashlib.sha256(txt2).hexdigest()
        stmt[1]['attachments'][0]['sha2'] = str(txtsha2)
        stmtdata = MIMEApplication(json.dumps(stmt), _subtype="json", _encoder=json.JSONEncoder)
        textdata = MIMEText(txt, 'plain', 'utf-8')
        textdata2 = MIMEText(txt2, 'plain', 'utf-8')
        
        textdata.add_header('X-Experience-API-Hash', txtsha)
        textdata2.add_header('X-Experience-API-Hash', txtsha2)
        message.attach(stmtdata)
        message.attach(textdata)
        message.attach(textdata2)
        
        r = self.client.post(reverse(statements), message.as_string(), content_type="multipart/mixed",
            Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(r.status_code, 200)
        returned_ids = json.loads(r.content)
        stmt_id1 = returned_ids[0]
        stmt_id2 = returned_ids[1]
        saved_stmt1 = Statement.objects.get(statement_id=stmt_id1)
        saved_stmt2 = Statement.objects.get(statement_id=stmt_id2)
        stmts = Statement.objects.all()
        attachments = StatementAttachment.objects.all()
        self.assertEqual(len(stmts), 2)
        self.assertEqual(len(attachments), 2)

        
        self.assertEqual(saved_stmt1.stmt_attachments.all()[0].payload.read(), base64.b64encode("howdy.. this is a text attachment"))
        self.assertEqual(saved_stmt2.stmt_attachments.all()[0].payload.read(), base64.b64encode("This is second attachment."))

    def test_multiple_stmt_multipart_same_attachment(self):
        stmt = [{"actor":{"mbox":"mailto:tom@example.com"},
            "verb":{"id":"http://tom.com/verb/butted"},
            "object":{"id":"act:tom.com/objs/heads"},
            "attachments": [
            {"usageType": "http://example.com/attachment-usage/test",
            "display": {"en-US": "A test attachment"},
            "description": {"en-US": "A test attachment (description)"},
            "contentType": "text/plain; charset=utf-8",
            "length": 27,
            "sha2":""}]},
            {"actor":{"mbox":"mailto:tom2@example.com"},
            "verb":{"id":"http://tom.com/verb/butted"},
            "object":{"id":"act:tom.com/objs/heads2"},
            "attachments": [
            {"usageType": "http://example.com/attachment-usage/test",
            "display": {"en-US": "A test attachment"},
            "description": {"en-US": "A test attachment (description)"},
            "contentType": "text/plain; charset=utf-8",
            "length": 27,
            "sha2":""}]}
            ]

        message = MIMEMultipart(boundary="myboundary")
        txt = u"howdy.. this is a text attachment"
        txtsha = hashlib.sha256(txt).hexdigest()
        stmt[0]['attachments'][0]["sha2"] = str(txtsha)        
        stmt[1]['attachments'][0]['sha2'] = str(txtsha)
        stmtdata = MIMEApplication(json.dumps(stmt), _subtype="json", _encoder=json.JSONEncoder)
        textdata = MIMEText(txt, 'plain', 'utf-8')
        
        textdata.add_header('X-Experience-API-Hash', txtsha)
        message.attach(stmtdata)
        message.attach(textdata)
        
        r = self.client.post(reverse(statements), message.as_string(), content_type="multipart/mixed",
            Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(r.status_code, 200)
        
        returned_ids = json.loads(r.content)
        stmt_id1 = returned_ids[0]
        stmt_id2 = returned_ids[1]
        saved_stmt1 = Statement.objects.get(statement_id=stmt_id1)
        saved_stmt2 = Statement.objects.get(statement_id=stmt_id2)
        stmts = Statement.objects.all()
        attachments = StatementAttachment.objects.all()
        self.assertEqual(len(stmts), 2)
        self.assertEqual(len(attachments), 2)

        self.assertEqual(saved_stmt1.stmt_attachments.all()[0].payload.read(), base64.b64encode("howdy.. this is a text attachment"))
        self.assertEqual(saved_stmt2.stmt_attachments.all()[0].payload.read(), base64.b64encode("howdy.. this is a text attachment"))

    def test_multiple_stmt_multipart_one_attachment_one_fileurl(self):
        stmt = [{"actor":{"mbox":"mailto:tom@example.com"},
            "verb":{"id":"http://tom.com/verb/butted"},
            "object":{"id":"act:tom.com/objs/heads"},
            "attachments": [
            {"usageType": "http://example.com/attachment-usage/test",
            "display": {"en-US": "A test attachment"},
            "description": {"en-US": "A test attachment (description)"},
            "contentType": "text/plain; charset=utf-8",
            "length": 27,
            "sha2":""}]},
            {"actor":{"mbox":"mailto:tom2@example.com"},
            "verb":{"id":"http://tom.com/verb/butted"},
            "object":{"id":"act:tom.com/objs/heads2"},
            "attachments": [
            {"usageType": "http://example.com/attachment-usage/test",
            "display": {"en-US": "A test attachment"},
            "description": {"en-US": "A test attachment (description)"},
            "contentType": "text/plain; charset=utf-8",
            "length": 27,
            "fileUrl":"http://my/file/url"}]}]

        message = MIMEMultipart(boundary="myboundary")
        txt = u"howdy.. this is a text attachment"
        txtsha = hashlib.sha256(txt).hexdigest()
        stmt[0]['attachments'][0]["sha2"] = str(txtsha)        
        stmtdata = MIMEApplication(json.dumps(stmt), _subtype="json", _encoder=json.JSONEncoder)
        textdata = MIMEText(txt, 'plain', 'utf-8')
        
        textdata.add_header('X-Experience-API-Hash', txtsha)
        message.attach(stmtdata)
        message.attach(textdata)
        
        r = self.client.post(reverse(statements), message.as_string(), content_type="multipart/mixed",
            Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(r.status_code, 200)
        
        returned_ids = json.loads(r.content)
        stmt_id1 = returned_ids[0]
        stmt_id2 = returned_ids[1]
        saved_stmt1 = Statement.objects.get(statement_id=stmt_id1)
        saved_stmt2 = Statement.objects.get(statement_id=stmt_id2)
        stmts = Statement.objects.all()
        attachments = StatementAttachment.objects.all()
        self.assertEqual(len(stmts), 2)
        self.assertEqual(len(attachments), 2)

        self.assertEqual(saved_stmt1.stmt_attachments.all()[0].payload.read(), base64.b64encode("howdy.. this is a text attachment"))
        self.assertEqual(saved_stmt2.stmt_attachments.all()[0].fileUrl, "http://my/file/url")

    def test_multiple_stmt_multipart_multiple_attachments_each(self):
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
            Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(r.status_code, 200)
        
        returned_ids = json.loads(r.content)
        stmt_id1 = returned_ids[0]
        stmt_id2 = returned_ids[1]
        saved_stmt1 = Statement.objects.get(statement_id=stmt_id1)
        saved_stmt2 = Statement.objects.get(statement_id=stmt_id2)

        stmts = Statement.objects.all()
        attachments = StatementAttachment.objects.all()
        self.assertEqual(len(stmts), 2)
        self.assertEqual(len(attachments), 4)

        stmt1_contents = ["This is a text attachment11","This is a text attachment12"]
        stmt2_contents = ["This is a text attachment21","This is a text attachment22"]
        self.assertIn(base64.b64decode(saved_stmt1.stmt_attachments.all()[0].payload.read()), stmt1_contents)
        self.assertIn(base64.b64decode(saved_stmt1.stmt_attachments.all()[1].payload.read()), stmt1_contents)
        self.assertIn(base64.b64decode(saved_stmt2.stmt_attachments.all()[0].payload.read()), stmt2_contents)
        self.assertIn(base64.b64decode(saved_stmt2.stmt_attachments.all()[1].payload.read()), stmt2_contents)

    def test_multipart_wrong_sha(self):
        stmt = {"actor":{"mbox":"mailto:tom@example.com"},
            "verb":{"id":"http://tom.com/verb/butted"},
            "object":{"id":"act:tom.com/objs/heads"},
            "attachments": [
            {"usageType": "http://example.com/attachment-usage/test",
            "display": {"en-US": "A test attachment"},
            "description": {"en-US": "A test attachment (description)"},
            "contentType": "text/plain; charset=utf-8",
            "length": 27,
            "sha2":""}]}

        message = MIMEMultipart(boundary="myboundary")
        txt = u"howdy.. this is a text attachment"
        txtsha = hashlib.sha256(txt).hexdigest()
        wrongtxt = u"blahblahblah this is wrong"
        wrongsha = hashlib.sha256(wrongtxt).hexdigest()
        stmt['attachments'][0]["sha2"] = str(wrongsha)
        
        stmtdata = MIMEApplication(json.dumps(stmt), _subtype="json", _encoder=json.JSONEncoder)
        textdata = MIMEText(txt, 'plain', 'utf-8')
        textdata.add_header('X-Experience-API-Hash', txtsha)
        message.attach(stmtdata)
        message.attach(textdata)

        r = self.client.post(reverse(statements), message.as_string(), content_type="multipart/mixed",
            Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.assertEqual(r.status_code, 400)
        self.assertIn("Could not find attachment payload with sha", r.content)

    def test_multiple_multipart(self):
        stmt = {"actor":{"mbox":"mailto:tom@example.com"},
            "verb":{"id":"http://tom.com/verb/butted"},
            "object":{"id":"act:tom.com/objs/heads"},
            "attachments": [
            {"usageType": "http://example.com/attachment-usage/test",
            "display": {"en-US": "A test attachment"},
            "description": {"en-US": "A test attachment (description)"},
            "contentType": "text/plain; charset=utf-8",
            "length": 27,
            "sha2":""},
            {"usageType": "http://example.com/attachment-usage/test",
            "display": {"en-US": "A test attachment2"},
            "description": {"en-US": "A test attachment (description)2"},
            "contentType": "text/plain; charset=utf-8",
            "length": 28,
            "sha2":""}]}

        message = MIMEMultipart(boundary="myboundary")
        txt = u"howdy.. this is a text attachment"
        txtsha = hashlib.sha256(txt).hexdigest()
        stmt['attachments'][0]["sha2"] = str(txtsha)
        
        txt2 = u"this is second attachment"
        txtsha2 = hashlib.sha256(txt2).hexdigest()
        stmt['attachments'][1]["sha2"] = str(txtsha2)

        stmtdata = MIMEApplication(json.dumps(stmt), _subtype="json", _encoder=json.JSONEncoder)
        textdata = MIMEText(txt, 'plain', 'utf-8')
        textdata.add_header('X-Experience-API-Hash', txtsha)
        textdata2 = MIMEText(txt2, 'plain', 'utf-8')
        textdata2.add_header('X-Experience-API-Hash', txtsha2)
        message.attach(stmtdata)
        message.attach(textdata)
        message.attach(textdata2)

        r = self.client.post(reverse(statements), message.as_string(), content_type="multipart/mixed",
            Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(r.status_code, 200)

    def test_multiple_multipart_wrong(self):
        stmt = {"actor":{"mbox":"mailto:tom@example.com"},
            "verb":{"id":"http://tom.com/verb/butted"},
            "object":{"id":"act:tom.com/objs/heads"},
            "attachments": [
            {"usageType": "http://example.com/attachment-usage/test",
            "display": {"en-US": "A test attachment"},
            "description": {"en-US": "A test attachment (description)"},
            "contentType": "text/plain; charset=utf-8",
            "length": 27,
            "sha2":""},
            {"usageType": "http://example.com/attachment-usage/test",
            "display": {"en-US": "A test attachment2"},
            "description": {"en-US": "A test attachment (description)2"},
            "contentType": "text/plain; charset=utf-8",
            "length": 28,
            "sha2":""}]}

        message = MIMEMultipart(boundary="myboundary")
        txt = u"howdy.. this is a text attachment"
        txtsha = hashlib.sha256(txt).hexdigest()
        stmt['attachments'][0]["sha2"] = str(txtsha)
        
        txt2 = u"this is second attachment"
        txtsha2 = hashlib.sha256(txt2).hexdigest()
        wrongtxt = u"this is some wrong text"
        wrongsha2 = hashlib.sha256(wrongtxt).hexdigest()
        stmt['attachments'][1]["sha2"] = str(wrongsha2)

        stmtdata = MIMEApplication(json.dumps(stmt), _subtype="json", _encoder=json.JSONEncoder)
        textdata = MIMEText(txt, 'plain', 'utf-8')
        textdata.add_header('X-Experience-API-Hash', txtsha)
        textdata2 = MIMEText(txt2, 'plain', 'utf-8')
        textdata2.add_header('X-Experience-API-Hash', txtsha2)
        message.attach(stmtdata)
        message.attach(textdata)
        message.attach(textdata2)

        r = self.client.post(reverse(statements), message.as_string(), content_type="multipart/mixed",
            Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(r.status_code, 400)
        self.assertIn("Could not find attachment payload with sha", r.content)

    def test_app_json_multipart(self):
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
            Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(response.status_code, 200)


    def test_app_json_multipart_wrong_fields(self):
        stmt = {"actor":{"mbox":"mailto:tom@example.com"},
            "verb":{"id":"http://tom.com/verb/butted"},
            "object":{"id":"act:tom.com/objs/heads"},
            "attachments": [
            {"usageType": "http://example.com/attachment-usage/test",
            "display": {"en-US": "A test attachment"},
            "description": {"en-US": "A test attachment (description)"},
            "bad": "foo",
            "contentType": "text/plain; charset=utf-8",
            "length": 27,
            "fileUrl": "http://my/file/url"}]}
        
        response = self.client.post(reverse(statements), json.dumps(stmt), content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, 'Invalid field(s) found in Attachment - bad')

    def test_app_json_multipart_one_fileURL(self):
        stmt = [{"actor":{"mbox":"mailto:tom@example.com"},
            "verb":{"id":"http://tom.com/verb/butted"},
            "object":{"id":"act:tom.com/objs/heads"},
            "attachments": [
                {"usageType": "http://example.com/attachment-usage/test",
                "display": {"en-US": "A test attachment"},
                "description": {"en-US": "A test attachment (description)"},
                "contentType": "text/plain; charset=utf-8",
                "length": 27,
                "fileUrl": "http://my/file/url"}]},
            {"actor":{"mbox":"mailto:tom1@example.com"},
            "verb":{"id":"http://tom.com/verb/butted"},
            "object":{"id":"act:tom.com/objs/heads1"},
            "attachments": [
                {"usageType": "http://example.com/attachment-usage/test",
                "display": {"en-US": "A test attachment"},
                "description": {"en-US": "A test attachment (description)"},
                "contentType": "text/plain; charset=utf-8",
                "length": 27,
                "fileUrl": "http://my/file/url"}]}
            ]
        
        response = self.client.post(reverse(statements), json.dumps(stmt), content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(response.status_code, 200)

        returned_ids = json.loads(response.content)
        stmt_id1 = returned_ids[0]
        stmt_id2 = returned_ids[1]
        saved_stmt1 = Statement.objects.get(statement_id=stmt_id1)
        saved_stmt2 = Statement.objects.get(statement_id=stmt_id2)
        stmts = Statement.objects.all()
        attachments = StatementAttachment.objects.all()
        self.assertEqual(len(stmts), 2)
        self.assertEqual(len(attachments), 2)

        self.assertEqual(saved_stmt1.stmt_attachments.all()[0].fileUrl, "http://my/file/url")
        self.assertEqual(saved_stmt2.stmt_attachments.all()[0].fileUrl, "http://my/file/url")

    def tyler_attachment_snafu(self):
        stmt = {
                "actor": {
                    "mbox": "mailto:tyler.mulligan.ctr@adlnet.gov",
                    "name": "Tyler",
                    "objectType": "Agent"
                },
                "verb": {
                    "id": "http://example.com/verbs/answered",
                    "display": {
                        "en-US": "answered"
                    }
                },
                "object": {
                    "id": "http://adlnet.gov/expapi/activities/example",
                    "definition": {
                        "name": {
                            "en-US": "Example Activity"
                        },
                        "description": {
                            "en-US": "Example activity description"
                        }
                    },
                    "objectType": "Activity"
                },
                "attachments": [
                    {
                        "usageType": "http://cool.com/cool/cool",
                        "display": {
                            "en-US": "My attachment"
                        },
                        "contentType": "image/jpeg",
                        "length": 12345,
                        "sha2": "f522a694d7fc5c38d7c604f63c87c9f74dcd002e"
                    }
                ]
            }

        response = self.client.post(reverse(statements), json.dumps(stmt), content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, "Missing X-Experience-API-Hash field in header")

    def test_app_json_multipart_no_fileUrl(self):
        stmt = {"actor":{"mbox":"mailto:tom@example.com"},
            "verb":{"id":"http://tom.com/verb/butted"},
            "object":{"id":"act:tom.com/objs/heads"},
            "attachments": [
            {"usageType": "http://example.com/attachment-usage/test",
            "display": {"en-US": "A test attachment"},
            "description": {"en-US": "A test attachment (description)"},
            "contentType": "text/plain; charset=utf-8",
            "length": 27}]}
        
        response = self.client.post(reverse(statements), json.dumps(stmt), content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(response.status_code, 400)
        self.assertIn('Attachment sha2 is required when no fileUrl is given', response.content)

    def test_multiple_app_json_multipart_no_fileUrl(self):
        stmt = {"actor":{"mbox":"mailto:tom@example.com"},
            "verb":{"id":"http://tom.com/verb/butted"},
            "object":{"id":"act:tom.com/objs/heads"},
            "attachments": [
            {"usageType": "http://example.com/attachment-usage/test",
            "display": {"en-US": "A test attachment"},
            "description": {"en-US": "A test attachment (description)"},
            "contentType": "text/plain; charset=utf-8",
            "length": 27,
            "fileUrl":"http://some/url"},
            {"usageType": "http://example.com/attachment-usage/test",
            "display": {"en-US": "A test attachment2"},
            "description": {"en-US": "A test attachment (description)2"},
            "contentType": "text/plain; charset=utf-8",
            "length": 28,
            "fileUrl":""}]}

        response = self.client.post(reverse(statements), json.dumps(stmt), content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(response.status_code, 400)
        self.assertIn('Attachments fileUrl with value  was not a valid IRI', response.content)

    def test_multipart_put(self):
        stmt_id = str(uuid.uuid1())
        stmt = {"id":stmt_id,
            "actor":{"mbox":"mailto:tom@example.com"},
            "verb":{"id":"http://tom.com/verb/butted"},
            "object":{"id":"act:tom.com/objs/heads"},
            "attachments": [
            {"usageType": "http://example.com/attachment-usage/test",
            "display": {"en-US": "A test attachment"},
            "description": {"en-US": "A test attachment (description)"},
            "contentType": "text/plain; charset=utf-8",
            "length": 27,
            "sha2":""}]}

        message = MIMEMultipart(boundary="myboundary")
        txt = u"howdy.. this is a text attachment"
        txtsha = hashlib.sha256(txt).hexdigest()
        stmt['attachments'][0]["sha2"] = str(txtsha)
        
        stmtdata = MIMEApplication(json.dumps(stmt), _subtype="json", _encoder=json.JSONEncoder)
        textdata = MIMEText(txt, 'plain', 'utf-8')
        textdata.add_header('X-Experience-API-Hash', txtsha)
        message.attach(stmtdata)
        message.attach(textdata)

        param = {"statementId":stmt_id}
        path = "%s?%s" % (reverse(statements), urllib.urlencode(param))
        r = self.client.put(path, message.as_string(), content_type="multipart/mixed", Authorization=self.auth,
            X_Experience_API_Version=settings.XAPI_VERSION)

        self.assertEqual(r.status_code, 204)

    def test_multipart_wrong_sha_put(self):
        stmt_id = str(uuid.uuid1())
        stmt = {"id":stmt_id,
            "actor":{"mbox":"mailto:tom@example.com"},
            "verb":{"id":"http://tom.com/verb/butted"},
            "object":{"id":"act:tom.com/objs/heads"},
            "attachments": [
            {"usageType": "http://example.com/attachment-usage/test",
            "display": {"en-US": "A test attachment"},
            "description": {"en-US": "A test attachment (description)"},
            "contentType": "text/plain; charset=utf-8",
            "length": 27,
            "sha2":""}]}

        message = MIMEMultipart(boundary="myboundary")
        txt = u"howdy.. this is a text attachment"
        txtsha = hashlib.sha256(txt).hexdigest()
        wrongtxt = u"blahblahblah this is wrong"
        wrongsha = hashlib.sha256(wrongtxt).hexdigest()
        stmt['attachments'][0]["sha2"] = str(wrongsha)
        
        stmtdata = MIMEApplication(json.dumps(stmt), _subtype="json", _encoder=json.JSONEncoder)
        textdata = MIMEText(txt, 'plain', 'utf-8')
        textdata.add_header('X-Experience-API-Hash', txtsha)
        message.attach(stmtdata)
        message.attach(textdata)

        param = {"statementId":stmt_id}
        path = "%s?%s" % (reverse(statements), urllib.urlencode(param))
        r = self.client.put(path, message.as_string(), content_type="multipart/mixed",
            Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.assertEqual(r.status_code, 400)
        self.assertIn("Could not find attachment payload with sha", r.content)

    def test_multiple_multipart_put(self):
        stmt_id = str(uuid.uuid1())
        stmt = {"id":stmt_id,
            "actor":{"mbox":"mailto:tom@example.com"},
            "verb":{"id":"http://tom.com/verb/butted"},
            "object":{"id":"act:tom.com/objs/heads"},
            "attachments": [
            {"usageType": "http://example.com/attachment-usage/test",
            "display": {"en-US": "A test attachment"},
            "description": {"en-US": "A test attachment (description)"},
            "contentType": "text/plain; charset=utf-8",
            "length": 27,
            "sha2":""},
            {"usageType": "http://example.com/attachment-usage/test",
            "display": {"en-US": "A test attachment2"},
            "description": {"en-US": "A test attachment (description)2"},
            "contentType": "text/plain; charset=utf-8",
            "length": 28,
            "sha2":""}]}

        message = MIMEMultipart(boundary="myboundary")
        txt = u"howdy.. this is a text attachment"
        txtsha = hashlib.sha256(txt).hexdigest()
        stmt['attachments'][0]["sha2"] = str(txtsha)
        
        txt2 = u"this is second attachment"
        txtsha2 = hashlib.sha256(txt2).hexdigest()
        stmt['attachments'][1]["sha2"] = str(txtsha2)

        stmtdata = MIMEApplication(json.dumps(stmt), _subtype="json", _encoder=json.JSONEncoder)
        textdata = MIMEText(txt, 'plain', 'utf-8')
        textdata.add_header('X-Experience-API-Hash', txtsha)
        textdata2 = MIMEText(txt2, 'plain', 'utf-8')
        textdata2.add_header('X-Experience-API-Hash', txtsha2)
        message.attach(stmtdata)
        message.attach(textdata)
        message.attach(textdata2)

        param = {"statementId":stmt_id}
        path = "%s?%s" % (reverse(statements), urllib.urlencode(param))
        r = self.client.put(path, message.as_string(), content_type="multipart/mixed" , Authorization=self.auth,
            X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(r.status_code, 204)

    def test_multiple_multipart_put_wrong_attachment(self):
        stmt_id = str(uuid.uuid1())
        stmt = {"id":stmt_id,
            "actor":{"mbox":"mailto:tom@example.com"},
            "verb":{"id":"http://tom.com/verb/butted"},
            "object":{"id":"act:tom.com/objs/heads"},
            "attachments": [
            {"usageType": "http://example.com/attachment-usage/test",
            "display": {"en-US": "A test attachment"},
            "description": {"en-US": "A test attachment (description)"},
            "contentType": "text/plain; charset=utf-8",
            "length": 27,
            "sha2":""},
            {"usageType": "http://example.com/attachment-usage/test",
            "display": {"en-US": "A test attachment2"},
            "description": {"en-US": "A test attachment (description)2"},
            "contentType": "text/plain; charset=utf-8",
            "length": 28,
            "sha2":""}]}

        message = MIMEMultipart(boundary="myboundary")
        txt = u"howdy.. this is a text attachment"
        txtsha = hashlib.sha256(txt).hexdigest()
        stmt['attachments'][0]["sha2"] = str(txtsha)
        
        txt2 = u"this is second attachment"
        txtsha2 = hashlib.sha256(txt2).hexdigest()
        wrongtxt = u"this is some wrong text"
        wrongsha2 = hashlib.sha256(wrongtxt).hexdigest()
        stmt['attachments'][1]["sha2"] = str(wrongsha2)

        stmtdata = MIMEApplication(json.dumps(stmt), _subtype="json", _encoder=json.JSONEncoder)
        textdata = MIMEText(txt, 'plain', 'utf-8')
        textdata.add_header('X-Experience-API-Hash', txtsha)
        textdata2 = MIMEText(txt2, 'plain', 'utf-8')
        textdata2.add_header('X-Experience-API-Hash', txtsha2)
        message.attach(stmtdata)
        message.attach(textdata)
        message.attach(textdata2)

        param = {"statementId":stmt_id}
        path = "%s?%s" % (reverse(statements), urllib.urlencode(param))
        r = self.client.put(path, message.as_string(), content_type="multipart/mixed",
            Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(r.status_code, 400)
        self.assertIn("Could not find attachment payload with sha", r.content)

    def test_app_json_multipart_put(self):
        stmt_id = str(uuid.uuid1())
        stmt = {"id":stmt_id,
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
        
        param = {"statementId":stmt_id}
        path = "%s?%s" % (reverse(statements), urllib.urlencode(param))        
        response = self.client.put(path, json.dumps(stmt), content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(response.status_code, 204)

    def test_app_json_multipart_not_array(self):
        stmt_id = str(uuid.uuid1())
        stmt = {"id":stmt_id,
            "actor":{"mbox":"mailto:tom@example.com"},
            "verb":{"id":"http://tom.com/verb/butted"},
            "object":{"id":"act:tom.com/objs/heads"},
            "attachments": "wrong"}
        
        param = {"statementId":stmt_id}
        path = "%s?%s" % (reverse(statements), urllib.urlencode(param))        
        response = self.client.put(path, json.dumps(stmt), content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, 'Attachments is not a properly formatted array')

    def test_app_json_multipart_no_fileUrl_put(self):
        stmt_id = str(uuid.uuid1())
        stmt = {"id":stmt_id,
            "actor":{"mbox":"mailto:tom@example.com"},
            "verb":{"id":"http://tom.com/verb/butted"},
            "object":{"id":"act:tom.com/objs/heads"},
            "attachments": [
            {"usageType": "http://example.com/attachment-usage/test",
            "display": {"en-US": "A test attachment"},
            "description": {"en-US": "A test attachment (description)"},
            "contentType": "text/plain; charset=utf-8",
            "length": 27}]}

        param = {"statementId":stmt_id}
        path = "%s?%s" % (reverse(statements), urllib.urlencode(param))        
        response = self.client.put(path, json.dumps(stmt), content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(response.status_code, 400)
        self.assertIn( 'Attachment sha2 is required when no fileUrl is given', response.content)

    def test_app_json_invalid_fileUrl(self):
        stmt_id = str(uuid.uuid1())
        stmt = {"id":stmt_id,
            "actor":{"mbox":"mailto:tom@example.com"},
            "verb":{"id":"http://tom.com/verb/butted"},
            "object":{"id":"act:tom.com/objs/heads"},
            "attachments": [
            {"usageType": "http://example.com/attachment-usage/test",
            "display": {"en-US": "A test attachment"},
            "description": {"en-US": "A test attachment (description)"},
            "contentType": "text/plain; charset=utf-8",
            "length": 27,
            "fileUrl": "blah"}]}

        param = {"statementId":stmt_id}
        path = "%s?%s" % (reverse(statements), urllib.urlencode(param))        
        response = self.client.put(path, json.dumps(stmt), content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(response.status_code, 400)
        self.assertIn('Attachments fileUrl with value blah was not a valid IRI', response.content)



    def test_multiple_app_json_multipart_no_fileUrl_put(self):
        stmt_id = str(uuid.uuid1())

        stmt = {"id":stmt_id,
            "actor":{"mbox":"mailto:tom@example.com"},
            "verb":{"id":"http://tom.com/verb/butted"},
            "object":{"id":"act:tom.com/objs/heads"},
            "attachments": [
            {"usageType": "http://example.com/attachment-usage/test",
            "display": {"en-US": "A test attachment"},
            "description": {"en-US": "A test attachment (description)"},
            "contentType": "text/plain; charset=utf-8",
            "length": 27,
            "fileUrl":"http://some/url"},
            {"usageType": "http://example.com/attachment-usage/test",
            "display": {"en-US": "A test attachment2"},
            "description": {"en-US": "A test attachment (description)2"},
            "contentType": "text/plain; charset=utf-8",
            "length": 28,
            "fileUrl":""}]}

        param = {"statementId":stmt_id}
        path = "%s?%s" % (reverse(statements), urllib.urlencode(param))
        response = self.client.put(path, json.dumps(stmt), content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(response.status_code, 400)
        self.assertIn('Attachments fileUrl with value  was not a valid IRI', response.content)

    def test_multipart_non_text_file(self):
        stmt = {"actor":{"mbox":"mailto:tom@example.com"},
            "verb":{"id":"http://tom.com/verb/butted"},
            "object":{"id":"act:tom.com/objs/heads"},
            "attachments": [
            {"usageType": "http://example.com/attachment-usage/test",
            "display": {"en-US": "A test picture"},
            "description": {"en-US": "A test picture (description)"},
            "contentType": "image/png",
            "length": 27,
            "sha2":""}]}

        message = MIMEMultipart(boundary="myboundary")
        img_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'adl_lrs','static','img', 'example.png'))
        img = open(img_path, 'rb')
        img_data = img.read()
        img.close()
        imgsha = hashlib.sha256(img_data).hexdigest()
        stmt['attachments'][0]["sha2"] = str(imgsha)
        
        stmtdata = MIMEApplication(json.dumps(stmt), _subtype="json", _encoder=json.JSONEncoder)
        imgdata = MIMEImage(img_data)

        imgdata.add_header('X-Experience-API-Hash', imgsha)
        message.attach(stmtdata)
        message.attach(imgdata)

        r = self.client.post(reverse(statements), message.as_string(),
            content_type='multipart/mixed', Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(r.status_code, 200)
        
        param= {"attachments":True}
        path = "%s?%s" % (reverse(statements),urllib.urlencode(param))
        r = self.client.get(path, X_Experience_API_Version=settings.XAPI_VERSION, Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], 'multipart/mixed; boundary=======ADL_LRS======')
        # Have to add the header to the top of the body else the email lib won't parse it correctly
        msg = message_from_string("Content-Type:multipart/mixed; boundary=======ADL_LRS======" + r.content)
        self.assertTrue(msg.is_multipart())

        parts = []
        for part in msg.walk():
            parts.append(part)
  
        self.assertEqual(parts[1]['Content-Type'], "application/json")
        self.assertTrue(isinstance(json.loads(parts[1].get_payload()), dict))
        # MIMEImage automatically b64 encodes data to be transfered
        self.assertEqual(parts[2].get_payload(), img_data)
        self.assertEqual(parts[2].get("X-Experience-API-Hash"), imgsha)
        self.assertEqual(imgsha, hashlib.sha256(parts[2].get_payload()).hexdigest())
        self.assertEqual(parts[2].get('Content-Type'), 'image/png')
        self.assertEqual(parts[2].get('Content-Transfer-Encoding'), 'binary')

    def test_example_signed_statement(self):
        header = base64.urlsafe_b64decode(fixpad(encodedhead))
        payload = base64.urlsafe_b64decode(fixpad(encodedpayload))

        stmt = json.loads(exstmt)
        
        jwso = JWS(header, payload)
        thejws = jwso.create(privatekey)
        self.assertEqual(thejws,sig)

        message = MIMEMultipart()
        stmt['attachments'][0]["sha2"] = jwso.sha2(thejws)
        
        stmtdata = MIMEApplication(json.dumps(stmt), _subtype="json", _encoder=json.JSONEncoder)
        jwsdata = MIMEApplication(thejws, _subtype="octet-stream")

        jwsdata.add_header('X-Experience-API-Hash', jwso.sha2(thejws))
        message.attach(stmtdata)
        message.attach(jwsdata)
        
        r = self.client.post(reverse(statements), message.as_string(),
            content_type='multipart/mixed', Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(r.status_code, 200)

    def test_example_signed_statement_bad(self):
        header = base64.urlsafe_b64decode(fixpad(encodedhead))
        payload = base64.urlsafe_b64decode(fixpad(encodedpayload))

        stmt = json.loads(exstmt)
        stmt['actor'] = {"mbox": "mailto:sneaky@example.com", "name": "Cheater", "objectType": "Agent"}
        
        jwso = JWS(header, payload)
        thejws = jwso.create(privatekey)
        self.assertEqual(thejws,sig)

        message = MIMEMultipart()
        stmt['attachments'][0]["sha2"] = jwso.sha2(thejws)
        
        stmtdata = MIMEApplication(json.dumps(stmt), _subtype="json", _encoder=json.JSONEncoder)
        jwsdata = MIMEApplication(thejws, _subtype="octet-stream")

        jwsdata.add_header('X-Experience-API-Hash', jwso.sha2(thejws))
        message.attach(stmtdata)
        message.attach(jwsdata)
        
        r = self.client.post(reverse(statements), message.as_string(),
            content_type='multipart/mixed', Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.content, 'The JSON Web Signature is not valid')

    def test_example_signed_statements(self):
        header = base64.urlsafe_b64decode(fixpad(encodedhead))
        payload = base64.urlsafe_b64decode(fixpad(encodedpayload))

        stmt1 = json.loads(exstmt)

        stmt2 = {"actor": {"mbox" : "mailto:otherguy@example.com"},
                 "verb" : {"id":"http://verbs.com/did"},
                 "object" : {"id":"act:stuff"} }

        stmt = [stmt1, stmt2]
        
        jwso = JWS(header, payload)
        thejws = jwso.create(privatekey)
        self.assertEqual(thejws,sig)

        message = MIMEMultipart()
        stmt1['attachments'][0]["sha2"] = jwso.sha2()
        
        stmtdata = MIMEApplication(json.dumps(stmt), _subtype="json", _encoder=json.JSONEncoder)
        jwsdata = MIMEApplication(thejws, _subtype="octet-stream")

        jwsdata.add_header('X-Experience-API-Hash', jwso.sha2(thejws))
        message.attach(stmtdata)
        message.attach(jwsdata)
        
        r = self.client.post(reverse(statements), message.as_string(),
            content_type='multipart/mixed', Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(r.status_code, 200)

fixpad = lambda s: s if len(s) % 4 == 0 else s + '=' * (4 - (len(s) % 4))

exstmt = """{
    "version": "1.0.0",
    "id": "33cff416-e331-4c9d-969e-5373a1756120",
    "actor": {
        "mbox": "mailto:example@example.com",
        "name": "Example Learner",
        "objectType": "Agent"
    },
    "verb": {
        "id": "http://adlnet.gov/expapi/verbs/experienced",
        "display": {
            "en-US": "experienced"
        }
    },
    "object": {
        "id": "https://www.youtube.com/watch?v=xh4kIiH3Sm8",
        "objectType": "Activity",
        "definition": {
            "name": {
                "en-US": "Tax Tips & Information : How to File a Tax Return "
            },
            "description": {
                "en-US": "Filing a tax return will require filling out either a 1040, 1040A or 1040EZ form"
            }
        }
    },
    "timestamp": "2013-04-01T12:00:00Z",
    "attachments": [
        {
            "usageType": "http://adlnet.gov/expapi/attachments/signature",
            "display": { "en-US": "Signature" },
            "description": { "en-US": "A test signature" },
            "contentType": "application/octet-stream",
            "length": 4235,
            "sha2": "dc9589e454ff375dd5dfd6f556d2583e231e8cafe55ef40102ddd988b79f86f0"
        }
    ]
}"""

sig = "ew0KICAgICJhbGciOiAiUlMyNTYiLA0KICAgICJ4NWMiOiBbDQogICAgICAgICJNSUlEQVRDQ0FtcWdBd0lCQWdJSkFNQjFjc051QTYra01BMEdDU3FHU0liM0RRRUJCUVVBTUhFeEN6QUpCZ05WQkFZVEFsVlRNUkl3RUFZRFZRUUlFd2xVWlc1dVpYTnpaV1V4R0RBV0JnTlZCQW9URDBWNFlXMXdiR1VnUTI5dGNHRnVlVEVRTUE0R0ExVUVBeE1IUlhoaGJYQnNaVEVpTUNBR0NTcUdTSWIzRFFFSkFSWVRaWGhoYlhCc1pVQmxlR0Z0Y0d4bExtTnZiVEFlRncweE16QTBNRFF4TlRJNE16QmFGdzB4TkRBME1EUXhOVEk0TXpCYU1JR1dNUXN3Q1FZRFZRUUdFd0pWVXpFU01CQUdBMVVFQ0JNSlZHVnVibVZ6YzJWbE1SRXdEd1lEVlFRSEV3aEdjbUZ1YTJ4cGJqRVlNQllHQTFVRUNoTVBSWGhoYlhCc1pTQkRiMjF3WVc1NU1SQXdEZ1lEVlFRTEV3ZEZlR0Z0Y0d4bE1SQXdEZ1lEVlFRREV3ZEZlR0Z0Y0d4bE1TSXdJQVlKS29aSWh2Y05BUWtCRmhObGVHRnRjR3hsUUdWNFlXMXdiR1V1WTI5dE1JR2ZNQTBHQ1NxR1NJYjNEUUVCQVFVQUE0R05BRENCaVFLQmdRRGp4dlpYRjMwV0w0b0tqWllYZ1IwWnlhWCt1M3k2K0pxVHFpTmtGYS9WVG5ldDZMeTJPVDZabW1jSkVQbnEzVW5ld3BIb09RK0dmaGhUa1cxM2owNmo1aU5uNG9iY0NWV1RMOXlYTnZKSCtLbyt4dTRZbC95U1BScklQeVRqdEhkRzBNMlh6SWxtbUxxbStDQVMrS0NiSmVINHRmNTQza0lXQzVwQzVwM2NWUUlEQVFBQm8zc3dlVEFKQmdOVkhSTUVBakFBTUN3R0NXQ0dTQUdHK0VJQkRRUWZGaDFQY0dWdVUxTk1JRWRsYm1WeVlYUmxaQ0JEWlhKMGFXWnBZMkYwWlRBZEJnTlZIUTRFRmdRVVZzM3Y1YWZFZE9lb1llVmFqQVFFNHYwV1MxUXdId1lEVlIwakJCZ3dGb0FVeVZJYzN5dnJhNEVCejIwSTRCRjM5SUFpeEJrd0RRWUpLb1pJaHZjTkFRRUZCUUFEZ1lFQWdTL0ZGNUQwSG5qNDRydlQ2a2duM2tKQXZ2MmxqL2Z5anp0S0lyWVMzM2xqWEduNmdHeUE0cXRiWEEyM1ByTzR1Yy93WUNTRElDRHBQb2JoNjJ4VENkOXFPYktoZ3dXT2kwNVBTQkxxVXUzbXdmQWUxNUxKQkpCcVBWWjRLMGtwcGVQQlU4bTZhSVpvSDU3TC85dDRPb2FMOHlLcy9xaktGZUkxT0ZXWnh2QT0iLA0KICAgICAgICAiTUlJRE56Q0NBcUNnQXdJQkFnSUpBTUIxY3NOdUE2K2pNQTBHQ1NxR1NJYjNEUUVCQlFVQU1IRXhDekFKQmdOVkJBWVRBbFZUTVJJd0VBWURWUVFJRXdsVVpXNXVaWE56WldVeEdEQVdCZ05WQkFvVEQwVjRZVzF3YkdVZ1EyOXRjR0Z1ZVRFUU1BNEdBMVVFQXhNSFJYaGhiWEJzWlRFaU1DQUdDU3FHU0liM0RRRUpBUllUWlhoaGJYQnNaVUJsZUdGdGNHeGxMbU52YlRBZUZ3MHhNekEwTURReE5USTFOVE5hRncweU16QTBNREl4TlRJMU5UTmFNSEV4Q3pBSkJnTlZCQVlUQWxWVE1SSXdFQVlEVlFRSUV3bFVaVzV1WlhOelpXVXhHREFXQmdOVkJBb1REMFY0WVcxd2JHVWdRMjl0Y0dGdWVURVFNQTRHQTFVRUF4TUhSWGhoYlhCc1pURWlNQ0FHQ1NxR1NJYjNEUUVKQVJZVFpYaGhiWEJzWlVCbGVHRnRjR3hsTG1OdmJUQ0JuekFOQmdrcWhraUc5dzBCQVFFRkFBT0JqUUF3Z1lrQ2dZRUExc0JuQldQWjBmN1dKVUZUSnk1KzAxU2xTNVo2RERENlV5ZTl2SzlBeWNnVjVCMytXQzhIQzV1NWg5MU11akFDMUFSUFZVT3RzdlBSczQ1cUtORklnSUdSWEtQQXdaamF3RUkyc0NKUlNLVjQ3aTZCOGJEdjRXa3VHdlFhdmVaR0kwcWxtTjVSMUVpbTJnVUl0UmoxaGdjQzlyUWF2amxuRktEWTJybFhHdWtDQXdFQUFhT0IxakNCMHpBZEJnTlZIUTRFRmdRVXlWSWMzeXZyYTRFQnoyMEk0QkYzOUlBaXhCa3dnYU1HQTFVZEl3U0JtekNCbUlBVXlWSWMzeXZyYTRFQnoyMEk0QkYzOUlBaXhCbWhkYVJ6TUhFeEN6QUpCZ05WQkFZVEFsVlRNUkl3RUFZRFZRUUlFd2xVWlc1dVpYTnpaV1V4R0RBV0JnTlZCQW9URDBWNFlXMXdiR1VnUTI5dGNHRnVlVEVRTUE0R0ExVUVBeE1IUlhoaGJYQnNaVEVpTUNBR0NTcUdTSWIzRFFFSkFSWVRaWGhoYlhCc1pVQmxlR0Z0Y0d4bExtTnZiWUlKQU1CMWNzTnVBNitqTUF3R0ExVWRFd1FGTUFNQkFmOHdEUVlKS29aSWh2Y05BUUVGQlFBRGdZRUFEaHdUZWJHazczNXlLaG04RHFDeHZObkVaME54c1lFWU9qZ1JHMXlYVGxXNXBFNjkxZlNINUFaK1Q2ZnB3cFpjV1k1UVlrb042RG53ak94R2tTZlFDMy95R21jVURLQlB3aVo1TzJzOUMrZkUxa1VFbnJYMlhlYTRhZ1ZuZ016UjhEUTZvT2F1TFdxZWhEQitnMkVOV1JMb1ZnUyttYTUvWWNzMEdUeXJFQ1k9Ig0KICAgIF0NCn0.ew0KICAgICJ2ZXJzaW9uIjogIjEuMC4wIiwNCiAgICAiaWQiOiAiMzNjZmY0MTYtZTMzMS00YzlkLTk2OWUtNTM3M2ExNzU2MTIwIiwNCiAgICAiYWN0b3IiOiB7DQogICAgICAgICJtYm94IjogIm1haWx0bzpleGFtcGxlQGV4YW1wbGUuY29tIiwNCiAgICAgICAgIm5hbWUiOiAiRXhhbXBsZSBMZWFybmVyIiwNCiAgICAgICAgIm9iamVjdFR5cGUiOiAiQWdlbnQiDQogICAgfSwNCiAgICAidmVyYiI6IHsNCiAgICAgICAgImlkIjogImh0dHA6Ly9hZGxuZXQuZ292L2V4cGFwaS92ZXJicy9leHBlcmllbmNlZCIsDQogICAgICAgICJkaXNwbGF5Ijogew0KICAgICAgICAgICAgImVuLVVTIjogImV4cGVyaWVuY2VkIg0KICAgICAgICB9DQogICAgfSwNCiAgICAib2JqZWN0Ijogew0KICAgICAgICAiaWQiOiAiaHR0cHM6Ly93d3cueW91dHViZS5jb20vd2F0Y2g_dj14aDRrSWlIM1NtOCIsDQogICAgICAgICJvYmplY3RUeXBlIjogIkFjdGl2aXR5IiwNCiAgICAgICAgImRlZmluaXRpb24iOiB7DQogICAgICAgICAgICAibmFtZSI6IHsNCiAgICAgICAgICAgICAgICAiZW4tVVMiOiAiVGF4IFRpcHMgJiBJbmZvcm1hdGlvbiA6IEhvdyB0byBGaWxlIGEgVGF4IFJldHVybiAiDQogICAgICAgICAgICB9LA0KICAgICAgICAgICAgImRlc2NyaXB0aW9uIjogew0KICAgICAgICAgICAgICAgICJlbi1VUyI6ICJGaWxpbmcgYSB0YXggcmV0dXJuIHdpbGwgcmVxdWlyZSBmaWxsaW5nIG91dCBlaXRoZXIgYSAxMDQwLCAxMDQwQSBvciAxMDQwRVogZm9ybSINCiAgICAgICAgICAgIH0NCiAgICAgICAgfQ0KICAgIH0sDQogICAgInRpbWVzdGFtcCI6ICIyMDEzLTA0LTAxVDEyOjAwOjAwWiINCn0.FWuwaPhwUbkk7h9sKW5zSvjsYNugvxJ-TrVaEgt_DCUT0bmKhQScRrjMB6P9O50uznPwT66oF1NnU_G0HVhRzS5voiXE-y7tT3z0M3-8A6YK009Bk_digVUul-HA4Fpd5IjoBBGe3yzaQ2ZvzarvRuipvNEQCI0onpfuZZJQ0d8"

encodedhead = """ew0KICAgICJhbGciOiAiUlMyNTYiLA0KICAgICJ4NWMiOiBbDQogICAgICAgICJNSUlEQVRDQ0FtcWdBd0lCQWdJSkFNQjFjc051QTYra01BMEdDU3FHU0liM0RRRUJCUVVBTUhFeEN6QUpCZ05WQkFZVEFsVlRNUkl3RUFZRFZRUUlFd2xVWlc1dVpYTnpaV1V4R0RBV0JnTlZCQW9URDBWNFlXMXdiR1VnUTI5dGNHRnVlVEVRTUE0R0ExVUVBeE1IUlhoaGJYQnNaVEVpTUNBR0NTcUdTSWIzRFFFSkFSWVRaWGhoYlhCc1pVQmxlR0Z0Y0d4bExtTnZiVEFlRncweE16QTBNRFF4TlRJNE16QmFGdzB4TkRBME1EUXhOVEk0TXpCYU1JR1dNUXN3Q1FZRFZRUUdFd0pWVXpFU01CQUdBMVVFQ0JNSlZHVnVibVZ6YzJWbE1SRXdEd1lEVlFRSEV3aEdjbUZ1YTJ4cGJqRVlNQllHQTFVRUNoTVBSWGhoYlhCc1pTQkRiMjF3WVc1NU1SQXdEZ1lEVlFRTEV3ZEZlR0Z0Y0d4bE1SQXdEZ1lEVlFRREV3ZEZlR0Z0Y0d4bE1TSXdJQVlKS29aSWh2Y05BUWtCRmhObGVHRnRjR3hsUUdWNFlXMXdiR1V1WTI5dE1JR2ZNQTBHQ1NxR1NJYjNEUUVCQVFVQUE0R05BRENCaVFLQmdRRGp4dlpYRjMwV0w0b0tqWllYZ1IwWnlhWCt1M3k2K0pxVHFpTmtGYS9WVG5ldDZMeTJPVDZabW1jSkVQbnEzVW5ld3BIb09RK0dmaGhUa1cxM2owNmo1aU5uNG9iY0NWV1RMOXlYTnZKSCtLbyt4dTRZbC95U1BScklQeVRqdEhkRzBNMlh6SWxtbUxxbStDQVMrS0NiSmVINHRmNTQza0lXQzVwQzVwM2NWUUlEQVFBQm8zc3dlVEFKQmdOVkhSTUVBakFBTUN3R0NXQ0dTQUdHK0VJQkRRUWZGaDFQY0dWdVUxTk1JRWRsYm1WeVlYUmxaQ0JEWlhKMGFXWnBZMkYwWlRBZEJnTlZIUTRFRmdRVVZzM3Y1YWZFZE9lb1llVmFqQVFFNHYwV1MxUXdId1lEVlIwakJCZ3dGb0FVeVZJYzN5dnJhNEVCejIwSTRCRjM5SUFpeEJrd0RRWUpLb1pJaHZjTkFRRUZCUUFEZ1lFQWdTL0ZGNUQwSG5qNDRydlQ2a2duM2tKQXZ2MmxqL2Z5anp0S0lyWVMzM2xqWEduNmdHeUE0cXRiWEEyM1ByTzR1Yy93WUNTRElDRHBQb2JoNjJ4VENkOXFPYktoZ3dXT2kwNVBTQkxxVXUzbXdmQWUxNUxKQkpCcVBWWjRLMGtwcGVQQlU4bTZhSVpvSDU3TC85dDRPb2FMOHlLcy9xaktGZUkxT0ZXWnh2QT0iLA0KICAgICAgICAiTUlJRE56Q0NBcUNnQXdJQkFnSUpBTUIxY3NOdUE2K2pNQTBHQ1NxR1NJYjNEUUVCQlFVQU1IRXhDekFKQmdOVkJBWVRBbFZUTVJJd0VBWURWUVFJRXdsVVpXNXVaWE56WldVeEdEQVdCZ05WQkFvVEQwVjRZVzF3YkdVZ1EyOXRjR0Z1ZVRFUU1BNEdBMVVFQXhNSFJYaGhiWEJzWlRFaU1DQUdDU3FHU0liM0RRRUpBUllUWlhoaGJYQnNaVUJsZUdGdGNHeGxMbU52YlRBZUZ3MHhNekEwTURReE5USTFOVE5hRncweU16QTBNREl4TlRJMU5UTmFNSEV4Q3pBSkJnTlZCQVlUQWxWVE1SSXdFQVlEVlFRSUV3bFVaVzV1WlhOelpXVXhHREFXQmdOVkJBb1REMFY0WVcxd2JHVWdRMjl0Y0dGdWVURVFNQTRHQTFVRUF4TUhSWGhoYlhCc1pURWlNQ0FHQ1NxR1NJYjNEUUVKQVJZVFpYaGhiWEJzWlVCbGVHRnRjR3hsTG1OdmJUQ0JuekFOQmdrcWhraUc5dzBCQVFFRkFBT0JqUUF3Z1lrQ2dZRUExc0JuQldQWjBmN1dKVUZUSnk1KzAxU2xTNVo2RERENlV5ZTl2SzlBeWNnVjVCMytXQzhIQzV1NWg5MU11akFDMUFSUFZVT3RzdlBSczQ1cUtORklnSUdSWEtQQXdaamF3RUkyc0NKUlNLVjQ3aTZCOGJEdjRXa3VHdlFhdmVaR0kwcWxtTjVSMUVpbTJnVUl0UmoxaGdjQzlyUWF2amxuRktEWTJybFhHdWtDQXdFQUFhT0IxakNCMHpBZEJnTlZIUTRFRmdRVXlWSWMzeXZyYTRFQnoyMEk0QkYzOUlBaXhCa3dnYU1HQTFVZEl3U0JtekNCbUlBVXlWSWMzeXZyYTRFQnoyMEk0QkYzOUlBaXhCbWhkYVJ6TUhFeEN6QUpCZ05WQkFZVEFsVlRNUkl3RUFZRFZRUUlFd2xVWlc1dVpYTnpaV1V4R0RBV0JnTlZCQW9URDBWNFlXMXdiR1VnUTI5dGNHRnVlVEVRTUE0R0ExVUVBeE1IUlhoaGJYQnNaVEVpTUNBR0NTcUdTSWIzRFFFSkFSWVRaWGhoYlhCc1pVQmxlR0Z0Y0d4bExtTnZiWUlKQU1CMWNzTnVBNitqTUF3R0ExVWRFd1FGTUFNQkFmOHdEUVlKS29aSWh2Y05BUUVGQlFBRGdZRUFEaHdUZWJHazczNXlLaG04RHFDeHZObkVaME54c1lFWU9qZ1JHMXlYVGxXNXBFNjkxZlNINUFaK1Q2ZnB3cFpjV1k1UVlrb042RG53ak94R2tTZlFDMy95R21jVURLQlB3aVo1TzJzOUMrZkUxa1VFbnJYMlhlYTRhZ1ZuZ016UjhEUTZvT2F1TFdxZWhEQitnMkVOV1JMb1ZnUyttYTUvWWNzMEdUeXJFQ1k9Ig0KICAgIF0NCn0"""
encodedpayload = """ew0KICAgICJ2ZXJzaW9uIjogIjEuMC4wIiwNCiAgICAiaWQiOiAiMzNjZmY0MTYtZTMzMS00YzlkLTk2OWUtNTM3M2ExNzU2MTIwIiwNCiAgICAiYWN0b3IiOiB7DQogICAgICAgICJtYm94IjogIm1haWx0bzpleGFtcGxlQGV4YW1wbGUuY29tIiwNCiAgICAgICAgIm5hbWUiOiAiRXhhbXBsZSBMZWFybmVyIiwNCiAgICAgICAgIm9iamVjdFR5cGUiOiAiQWdlbnQiDQogICAgfSwNCiAgICAidmVyYiI6IHsNCiAgICAgICAgImlkIjogImh0dHA6Ly9hZGxuZXQuZ292L2V4cGFwaS92ZXJicy9leHBlcmllbmNlZCIsDQogICAgICAgICJkaXNwbGF5Ijogew0KICAgICAgICAgICAgImVuLVVTIjogImV4cGVyaWVuY2VkIg0KICAgICAgICB9DQogICAgfSwNCiAgICAib2JqZWN0Ijogew0KICAgICAgICAiaWQiOiAiaHR0cHM6Ly93d3cueW91dHViZS5jb20vd2F0Y2g_dj14aDRrSWlIM1NtOCIsDQogICAgICAgICJvYmplY3RUeXBlIjogIkFjdGl2aXR5IiwNCiAgICAgICAgImRlZmluaXRpb24iOiB7DQogICAgICAgICAgICAibmFtZSI6IHsNCiAgICAgICAgICAgICAgICAiZW4tVVMiOiAiVGF4IFRpcHMgJiBJbmZvcm1hdGlvbiA6IEhvdyB0byBGaWxlIGEgVGF4IFJldHVybiAiDQogICAgICAgICAgICB9LA0KICAgICAgICAgICAgImRlc2NyaXB0aW9uIjogew0KICAgICAgICAgICAgICAgICJlbi1VUyI6ICJGaWxpbmcgYSB0YXggcmV0dXJuIHdpbGwgcmVxdWlyZSBmaWxsaW5nIG91dCBlaXRoZXIgYSAxMDQwLCAxMDQwQSBvciAxMDQwRVogZm9ybSINCiAgICAgICAgICAgIH0NCiAgICAgICAgfQ0KICAgIH0sDQogICAgInRpbWVzdGFtcCI6ICIyMDEzLTA0LTAxVDEyOjAwOjAwWiINCn0"""

privatekey = """-----BEGIN RSA PRIVATE KEY-----
MIICXAIBAAKBgQDjxvZXF30WL4oKjZYXgR0ZyaX+u3y6+JqTqiNkFa/VTnet6Ly2
OT6ZmmcJEPnq3UnewpHoOQ+GfhhTkW13j06j5iNn4obcCVWTL9yXNvJH+Ko+xu4Y
l/ySPRrIPyTjtHdG0M2XzIlmmLqm+CAS+KCbJeH4tf543kIWC5pC5p3cVQIDAQAB
AoGAOejdvGq2XKuddu1kWXl0Aphn4YmdPpPyCNTaxplU6PBYMRjY0aNgLQE6bO2p
/HJiU4Y4PkgzkEgCu0xf/mOq5DnSkX32ICoQS6jChABAe20ErPfm5t8h9YKsTfn9
40lAouuwD9ePRteizd4YvHtiMMwmh5PtUoCbqLefawNApAECQQD1mdBW3zL0okUx
2pc4tttn2qArCG4CsEZMLlGRDd3FwPWJz3ZPNEEgZWXGSpA9F1QTZ6JYXIfejjRo
UuvRMWeBAkEA7WvzDBNcv4N+xeUKvH8ILti/BM58LraTtqJlzjQSovek0srxtmDg
5of+xrxN6IM4p7yvQa+7YOUOukrVXjG+1QJBAI2mBrjzxgm9xTa5odn97JD7UMFA
/WHjlMe/Nx/35V52qaav1sZbluw+TvKMcqApYj5G2SUpSNudHLDGkmd2nQECQFfc
lBRK8g7ZncekbGW3aRLVGVOxClnLLTzwOlamBKOUm8V6XxsMHQ6TE2D+fKJoNUY1
2HGpk+FWwy2D1hRGuoUCQAXfaLSxtaWdPtlZTPVueF7ZikQDsVg+vtTFgpuHloR2
6EVc1RbHHZm32yvGDY8IkcoMfJQqLONDdLfS/05yoNU=
-----END RSA PRIVATE KEY-----"""