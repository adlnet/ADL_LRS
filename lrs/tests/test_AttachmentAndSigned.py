import json
import base64
import uuid
import urllib
import hashlib
import os
from jose import jws

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

from adl_lrs.views import register

class AttachmentAndSignedTests(TestCase):
    @classmethod
    def setUpClass(cls):
        print "\n%s" % __name__
        super(AttachmentAndSignedTests, cls).setUpClass()

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
        textdata.replace_header('Content-Transfer-Encoding', 'binary')
        textdata.set_payload(txt, 'utf-8')

        message.attach(stmtdata)
        message.attach(textdata)

        r = self.client.post(reverse('lrs:statements'), message.as_string(),
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
        textdata.replace_header('Content-Transfer-Encoding', 'binary')
        textdata2.replace_header('Content-Transfer-Encoding', 'binary')
        textdata.set_payload(txt, 'utf-8')
        textdata2.set_payload(txt2, 'utf-8')
        message.attach(stmtdata)
        message.attach(textdata)
        message.attach(textdata2)
        
        r = self.client.post(reverse('lrs:statements'), message.as_string(), content_type="multipart/mixed",
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

        
        self.assertEqual(saved_stmt1.stmt_attachments.all()[0].payload.read(), "howdy.. this is a text attachment")
        self.assertEqual(saved_stmt2.stmt_attachments.all()[0].payload.read(), "This is second attachment.")

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
        textdata.replace_header('Content-Transfer-Encoding', 'binary')
        textdata.set_payload(txt, 'utf-8')
        message.attach(stmtdata)
        message.attach(textdata)
        
        r = self.client.post(reverse('lrs:statements'), message.as_string(), content_type="multipart/mixed",
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

        self.assertEqual(saved_stmt1.stmt_attachments.all()[0].payload.read(), "howdy.. this is a text attachment")
        self.assertEqual(saved_stmt2.stmt_attachments.all()[0].payload.read(), "howdy.. this is a text attachment")

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
        textdata.replace_header('Content-Transfer-Encoding', 'binary')
        textdata.set_payload(txt, 'utf-8')
        message.attach(stmtdata)
        message.attach(textdata)
        
        r = self.client.post(reverse('lrs:statements'), message.as_string(), content_type="multipart/mixed",
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

        self.assertEqual(saved_stmt1.stmt_attachments.all()[0].payload.read(), "howdy.. this is a text attachment")
        self.assertEqual(saved_stmt2.stmt_attachments.all()[0].canonical_data['fileUrl'], "http://my/file/url")

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

        textdata11.replace_header('Content-Transfer-Encoding', 'binary')
        textdata12.replace_header('Content-Transfer-Encoding', 'binary')
        textdata21.replace_header('Content-Transfer-Encoding', 'binary')
        textdata22.replace_header('Content-Transfer-Encoding', 'binary')

        textdata11.set_payload(txt11, 'utf-8')
        textdata12.set_payload(txt12, 'utf-8')
        textdata21.set_payload(txt21, 'utf-8')
        textdata22.set_payload(txt22, 'utf-8')

        message.attach(stmtdata)
        message.attach(textdata11)
        message.attach(textdata12)
        message.attach(textdata21)
        message.attach(textdata22)
        
        r = self.client.post(reverse('lrs:statements'), message.as_string(), content_type="multipart/mixed",
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
        self.assertIn(saved_stmt1.stmt_attachments.all()[0].payload.read(), stmt1_contents)
        self.assertIn(saved_stmt1.stmt_attachments.all()[1].payload.read(), stmt1_contents)
        self.assertIn(saved_stmt2.stmt_attachments.all()[0].payload.read(), stmt2_contents)
        self.assertIn(saved_stmt2.stmt_attachments.all()[1].payload.read(), stmt2_contents)

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
        textdata.replace_header('Content-Transfer-Encoding', 'binary')
        textdata.set_payload(txt, 'utf-8')
        message.attach(stmtdata)
        message.attach(textdata)

        r = self.client.post(reverse('lrs:statements'), message.as_string(), content_type="multipart/mixed",
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
        textdata.replace_header('Content-Transfer-Encoding', 'binary')
        textdata.set_payload(txt, 'utf-8')
        textdata2 = MIMEText(txt2, 'plain', 'utf-8')
        textdata2.add_header('X-Experience-API-Hash', txtsha2)
        textdata2.replace_header('Content-Transfer-Encoding', 'binary')
        textdata2.set_payload(txt2, 'utf-8')
        message.attach(stmtdata)
        message.attach(textdata)
        message.attach(textdata2)

        r = self.client.post(reverse('lrs:statements'), message.as_string(), content_type="multipart/mixed",
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
        textdata.replace_header('Content-Transfer-Encoding', 'binary')
        textdata.set_payload(txt, 'utf-8')
        textdata2 = MIMEText(txt2, 'plain', 'utf-8')
        textdata2.add_header('X-Experience-API-Hash', txtsha2)
        textdata2.replace_header('Content-Transfer-Encoding', 'binary')
        textdata2.set_payload(txt2, 'utf-8')
        message.attach(stmtdata)
        message.attach(textdata)
        message.attach(textdata2)

        r = self.client.post(reverse('lrs:statements'), message.as_string(), content_type="multipart/mixed",
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
        
        response = self.client.post(reverse('lrs:statements'), json.dumps(stmt), content_type="application/json",
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
        
        response = self.client.post(reverse('lrs:statements'), json.dumps(stmt), content_type="application/json",
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
        
        response = self.client.post(reverse('lrs:statements'), json.dumps(stmt), content_type="application/json",
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

        self.assertEqual(saved_stmt1.stmt_attachments.all()[0].canonical_data['fileUrl'], "http://my/file/url")
        self.assertEqual(saved_stmt2.stmt_attachments.all()[0].canonical_data['fileUrl'], "http://my/file/url")

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

        response = self.client.post(reverse('lrs:statements'), json.dumps(stmt), content_type="application/json",
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
        
        response = self.client.post(reverse('lrs:statements'), json.dumps(stmt), content_type="application/json",
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

        response = self.client.post(reverse('lrs:statements'), json.dumps(stmt), content_type="application/json",
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
        textdata.replace_header('Content-Transfer-Encoding', 'binary')
        textdata.set_payload(txt, 'utf-8')

        message.attach(stmtdata)
        message.attach(textdata)

        param = {"statementId":stmt_id}
        path = "%s?%s" % (reverse('lrs:statements'), urllib.urlencode(param))
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
        textdata.replace_header('Content-Transfer-Encoding', 'binary')
        textdata.set_payload(txt, 'utf-8')
        message.attach(stmtdata)
        message.attach(textdata)

        param = {"statementId":stmt_id}
        path = "%s?%s" % (reverse('lrs:statements'), urllib.urlencode(param))
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
        textdata.replace_header('Content-Transfer-Encoding', 'binary')
        textdata.set_payload(txt, 'utf-8')
        textdata2 = MIMEText(txt2, 'plain', 'utf-8')
        textdata2.add_header('X-Experience-API-Hash', txtsha2)
        textdata2.replace_header('Content-Transfer-Encoding', 'binary')
        textdata2.set_payload(txt2, 'utf-8')
        message.attach(stmtdata)
        message.attach(textdata)
        message.attach(textdata2)

        param = {"statementId":stmt_id}
        path = "%s?%s" % (reverse('lrs:statements'), urllib.urlencode(param))
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
        textdata.replace_header('Content-Transfer-Encoding', 'binary')
        textdata.set_payload(txt, 'utf-8')
        textdata2 = MIMEText(txt2, 'plain', 'utf-8')
        textdata2.add_header('X-Experience-API-Hash', txtsha2)
        textdata2.replace_header('Content-Transfer-Encoding', 'binary')
        textdata2.set_payload(txt2, 'utf-8')
        message.attach(stmtdata)
        message.attach(textdata)
        message.attach(textdata2)

        param = {"statementId":stmt_id}
        path = "%s?%s" % (reverse('lrs:statements'), urllib.urlencode(param))
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
        path = "%s?%s" % (reverse('lrs:statements'), urllib.urlencode(param))        
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
        path = "%s?%s" % (reverse('lrs:statements'), urllib.urlencode(param))        
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
        path = "%s?%s" % (reverse('lrs:statements'), urllib.urlencode(param))        
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
        path = "%s?%s" % (reverse('lrs:statements'), urllib.urlencode(param))        
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
        path = "%s?%s" % (reverse('lrs:statements'), urllib.urlencode(param))
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
        imgdata.replace_header('Content-Transfer-Encoding', 'binary')
        imgdata.set_payload(img_data)

        message.attach(stmtdata)
        message.attach(imgdata)

        r = self.client.post(reverse('lrs:statements'), message.as_string(),
            content_type='multipart/mixed', Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(r.status_code, 200)
        
        param= {"attachments":True}
        path = "%s?%s" % (reverse('lrs:statements'),urllib.urlencode(param))
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
        payload = json.loads(exstmt)
        signature = jws.sign(payload, privatekey, algorithm='RS256')
        self.assertTrue(jws.verify(signature, privatekey, algorithms=['RS256']))
        sha2 = hashlib.sha256(signature).hexdigest()
        payload['attachments'][0]["sha2"] = sha2

        message = MIMEMultipart()        
        stmtdata = MIMEApplication(json.dumps(payload), _subtype="json", _encoder=json.JSONEncoder)
        jwsdata = MIMEApplication(signature, _subtype="octet-stream")

        jwsdata.add_header('X-Experience-API-Hash', sha2)
        jwsdata.replace_header('Content-Transfer-Encoding', 'binary')
        jwsdata.set_payload(signature)
        message.attach(stmtdata)
        message.attach(jwsdata)
        
        r = self.client.post(reverse('lrs:statements'), message.as_string(),
            content_type='multipart/mixed', Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(r.status_code, 200)

    def test_example_signed_statement_sha2s_no_match(self):
        stmt = json.loads(exstmt)
        stmt['actor'] = {"mbox": "mailto:sneaky@example.com", "name": "Cheater", "objectType": "Agent"}
        signature = jws.sign(stmt, privatekey, algorithm='RS384')
        self.assertTrue(jws.verify(signature, privatekey, algorithms=['RS384']))
        sha2 = hashlib.sha384(signature).hexdigest()
        stmt['attachments'][0]["sha2"] = sha2
        
        message = MIMEMultipart()
        stmtdata = MIMEApplication(exstmt, _subtype="json", _encoder=json.JSONEncoder)
        jwsdata = MIMEApplication(signature, _subtype="octet-stream")

        jwsdata.add_header('X-Experience-API-Hash', sha2)
        jwsdata.replace_header('Content-Transfer-Encoding', 'binary')
        jwsdata.set_payload(signature)
        message.attach(stmtdata)
        message.attach(jwsdata)
        
        r = self.client.post(reverse('lrs:statements'), message.as_string(),
            content_type='multipart/mixed', Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.content, 'Signature attachment is missing from request')

    def test_example_signed_statement_payloads_no_match(self):
        bad_stmt = json.loads(exstmt)
        bad_stmt['actor'] = {"mbox": "mailto:sneaky@example.com", "name": "Cheater", "objectType": "Agent"}
        signature = jws.sign(bad_stmt, privatekey, algorithm='RS512')
        self.assertTrue(jws.verify(signature, privatekey, algorithms=['RS512']))
        sha2 = hashlib.sha512(signature).hexdigest()
        bad_stmt['attachments'][0]["sha2"] = sha2

        good_stmt = json.loads(exstmt)
        good_stmt['attachments'][0]["sha2"] = sha2

        message = MIMEMultipart()
        stmtdata = MIMEApplication(json.dumps(good_stmt), _subtype="json", _encoder=json.JSONEncoder)
        jwsdata = MIMEApplication(signature, _subtype="octet-stream")

        jwsdata.add_header('X-Experience-API-Hash', sha2)
        jwsdata.replace_header('Content-Transfer-Encoding', 'binary')
        jwsdata.set_payload(signature)
        message.attach(stmtdata)
        message.attach(jwsdata)
        
        r = self.client.post(reverse('lrs:statements'), message.as_string(),
            content_type='multipart/mixed', Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.content, 'The JWS is not valid - payload and body statements do not match')

    def test_example_signed_statement_with_x509_cert(self):
        payload = json.loads(exstmt)
        signature = jws.sign(payload, privatekey, {'x5c': [base64.b64encode(publickey)]}, 'RS256')
        self.assertTrue(jws.verify(signature, privatekey, algorithms=['RS256']))
        sha2 = hashlib.sha256(signature).hexdigest()
        payload['attachments'][0]["sha2"] = sha2

        message = MIMEMultipart()
        stmtdata = MIMEApplication(json.dumps(payload), _subtype="json", _encoder=json.JSONEncoder)
        jwsdata = MIMEApplication(signature, _subtype="octet-stream")

        jwsdata.add_header('X-Experience-API-Hash', sha2)
        jwsdata.replace_header('Content-Transfer-Encoding', 'binary')
        jwsdata.set_payload(signature)
        message.attach(stmtdata)
        message.attach(jwsdata)
        
        r = self.client.post(reverse('lrs:statements'), message.as_string(),
            content_type='multipart/mixed', Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(r.status_code, 200)

    def test_example_signed_statement_with_x509_cert_wrong(self):
        payload = json.loads(exstmt)
        signature = jws.sign(payload, privatekey, {'x5c': [base64.b64encode(wrongpublickey)]}, 'RS256')
        self.assertTrue(jws.verify(signature, privatekey, algorithms=['RS256']))
        sha2 = hashlib.sha256(signature).hexdigest()
        payload['attachments'][0]["sha2"] = sha2

        message = MIMEMultipart()
        stmtdata = MIMEApplication(json.dumps(payload), _subtype="json", _encoder=json.JSONEncoder)
        jwsdata = MIMEApplication(signature, _subtype="octet-stream")

        jwsdata.add_header('X-Experience-API-Hash', sha2)
        jwsdata.replace_header('Content-Transfer-Encoding', 'binary')
        jwsdata.set_payload(signature)
        message.attach(stmtdata)
        message.attach(jwsdata)
        
        r = self.client.post(reverse('lrs:statements'), message.as_string(),
            content_type='multipart/mixed', Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.content, 'The JWS is not valid: Signature verification failed.')

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

publickey = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAopcIphKtEI/Ong+kU0pm
kR5ajkPlcoiRHcmRbLPIq5wvTQufwZ9oGhhXbsj/M7UMvvviBNCdecT21rK1ZCbh
IHeobjYM0J7ZY7StZhPL7IPUaN1Mt77uR5Oowj3iZjXgG4jwpJ0O8xpqSRZFsR2d
7qjvTTJLFQxNLEznrQshiO4da357T8XfWFsn5hqj1SibGzFnfktAbZ9B9BuMVJuT
HDRgcgrIMf3Ct3/fstOKxo4rb25uXyqAdM24k6Rd+QJc3HZpOQ5Yfgk8DPR5X3YR
Lx1YCLZKPeah0HCQiB3kGD4Wn/Pc4hU29O7c4YhwjCUJAgqiPEHYvuzLmiBcOGzz
hQIDAQAB
-----END PUBLIC KEY-----"""

wrongpublickey = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAzO/eUZPksFpU6E0BBTbp
F1T66Mnq3DJK06hKzyhLfI9L9bGzEQVCa7YNmHdDaGXgmmlT8hdbLeAspfeItKyI
tIzkBLCElHZ1UdIA2ibs3DrH1OH9TWk+ANpVJULY5O73NDb7yx29mDbUdHeBD4kR
R+eTc7HYHf5d5RbZLtZ17gpSf46PncPp+JkyRcAc895BboY7cpAWyGX1tlcWfizk
tT0+h89PoJw8cbKG8hQQfzztCdEkKOgs+4LEAvBWPyhgYRxqFPUcxIxtukZpociD
7i8ZuKIZP9ERCemi1Trniw6iot4DMhtwbT3/nhYGeG1dm011tX0ClKqhiIzJs7n0
8QIDAQAB
-----END PUBLIC KEY-----"""

privatekey = """-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQCilwimEq0Qj86e
D6RTSmaRHlqOQ+VyiJEdyZFss8irnC9NC5/Bn2gaGFduyP8ztQy+++IE0J15xPbW
srVkJuEgd6huNgzQntljtK1mE8vsg9Ro3Uy3vu5Hk6jCPeJmNeAbiPCknQ7zGmpJ
FkWxHZ3uqO9NMksVDE0sTOetCyGI7h1rfntPxd9YWyfmGqPVKJsbMWd+S0Btn0H0
G4xUm5McNGByCsgx/cK3f9+y04rGjitvbm5fKoB0zbiTpF35Alzcdmk5Dlh+CTwM
9HlfdhEvHVgItko95qHQcJCIHeQYPhaf89ziFTb07tzhiHCMJQkCCqI8Qdi+7Mua
IFw4bPOFAgMBAAECggEAUx6jbUNe9niOSH/2oh4HEWlTIifTxRnMFk5V6hx/Gjxe
ciTfJz03GyAWkqxuyyBjw79BbPS5jOcEyf3SfcDilpaVpMI9CuoqeK6Fdwnn1qIO
lQ2NiuIxLqZuP98jPt2MFIeNfppMaju22mZoeoOJmdkDfZOYjsobKeqnBfAK1NUV
qpewRkgYLLlI/tM+H77ihpOVvQlNH2uuLtjtRP+EpbvkZ0hpH5Qk7wi4ODtQVKeq
qJjUjSu16PrAOX40ce8Cjh7LF1GP1zaRYdfODVKSbFJNvmKReF/trGNOegjiLZP5
pOWss4V7rop5dFdlt4MWRZ2gQi1eFPCnv+teDUBsAQKBgQDU9ZM7VQBaSxwd3uIt
sOsdqWZnbGdc5KN+YyULftUjg/ELDO/hXINnAPXhnBYS/ToKdsYoW0KX24OOkNy9
VLX0Lo+N+J0mhZDjYspg63uWBi+KUkeUWRcb2esjoZf4iT5ugIntpOddA4tZ7wNO
vm7ELydnu1X1GQJWHvacQ026LQKBgQDDc18vnPBSCPTJidEO0GWSbjNu8xbp015w
9t5Tne3499yQDXkoDngfii3B7rxsqVv1UxlCDqmJFSDFm5v/odO1uKZbsazM6/OD
RGD9B2l9XnCpJ0VEewzZPwKnHR1Ms4Fvc4ehSvok2po4YaR5d9KGxkQCRKsXtfDX
ZvekI9WtuQKBgGkWVfUtWOM1tUY4Ojx51Uvp0BKxN8BrQxKXMiyeBedksInXdHgt
AtrNaohOUcZFF2MagWZgwlfVhvHPIl57ct5wK37PdB0SRBExKtTw3yeFHeiP+aqG
3BRuUM5ga3HFp/03iNiwS0tm+FkEzQkKh/Zfnn5dv2kXUkPVO7SYsb5xAoGAJztq
WOFUr/LSR/4c869LJChwtI2hBNCDvYMgP4KM+ROvt06tCihVXmdbJflo4xrftY+3
mzXcPAL8sA27M4XlPC3TXsZ8XCnkmG3KVh/9wceKL7oNQmC8xILMYoUKk5HYoml7
SRoGug0TNcwLusIdhSYZEqd7/Gdt757giJcU1ikCgYEAwZBBLEdF+oSDfEy5ixYb
r9IsERRoDLD7f+C9vf1ilivVsAY8E9uTF+olHzESPhEndlNDwMU3NHzMUsqGf05d
bNxWAKDGyKQSwyb9CbUBMl4ErfkduQAHaJXK7gTF8Pvgr9OehajDT4sQi3H6gg0a
qjOL3XOZ+ZNpW0h9JM/jrF0=
-----END PRIVATE KEY-----"""