import base64
import json

from binascii import a2b_base64
from Crypto.Hash import SHA256, SHA384, SHA512
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5, PKCS1_PSS
from Crypto.Util.asn1 import DerSequence

# https://www.dlitz.net/software/pycrypto/api/current/

fixb64padding = lambda s: s if len(s) % 4 == 0 else s + '=' * (4 - (len(s) % 4))
rmb64padding = lambda s: s.rstrip('=')
algs = {"RS256": SHA256,
        "RS384": SHA384,
        "RS512": SHA512}

class JWS(object):
    """
    Class used to represent a JSON Web Signature (JWS).
    see: http://tools.ietf.org/html/draft-ietf-jose-json-web-signature-08
    Only covers the requirements outlined in the Experience API spec.
    see: https://github.com/adlnet/xAPI-Spec/blob/master/xAPI.md#signature
    """
    def __init__(self, header=None, payload=None, jws=None):
        """
        Init for a JWS object.

        If you want to create a JWS, pass in the header and payload and call 
        :func:`JWS.create`.

        If you want to parse and verify a JWS, pass in the JWS and call 
        :func:`JWS.verify`.

        :param header:
            JWS Header - Optional
        :param payload:
            JWS Payload - Optional
        :param jws:
            JSON Web Signature - Optional
        """
        self.header = header
        if self.header:
            self._parseheader()
        self.payload = payload
        self.jws = jws
        if self.jws:
            self._parsejws()
        
    def verify(self):
        """
        Verifies the JWS Signature can be verified by the public key.
        """
        # free pass for those who don't use x5c
        if not self.should_verify:
            return True
        try:
            pubkey = self._cert_to_key(self.headerobj['x5c'][0])
        except:
            raise JWSException("Error importing public key")
        
        verifier = PKCS1_v1_5.new(pubkey)
        res = verifier.verify(self._hash(), self.jwssignature)
        if not res:
            verifier = PKCS1_PSS.new(pubkey)
            res = verifier.verify(self._hash(), self.jwssignature)
        return res

    def create(self, privatekey):
        """
        Creates a JWS using the privatekey string to sign.

        :param privatekey: 
            String format of the private key to use to sign the JWS Signature Input.
        """
        if not self.jws:
            privkey = RSA.importKey(privatekey)
            # encode header and payload
            self.encheader = rmb64padding(base64.urlsafe_b64encode(self.header))
            self.encpayload = rmb64padding(base64.urlsafe_b64encode(self.payload))
            # hash & sign
            signer = PKCS1_v1_5.new(privkey)
            self.jwssignature = signer.sign(self._hash())
            # encode signature
            self.encjwssignature = rmb64padding(base64.urlsafe_b64encode(self.jwssignature))
            # join 3
            self.jws = '.'.join([self.encheader,self.encpayload,self.encjwssignature])

        return self.jws

    def sha2(self, jwsobj=None, alg=None):
        """
        Hash (SHA256) the JWS according to xAPI attachment rules 
        for the sha2 attribute. Returns the hexdigest value. If 
        a parameter isn't provided, this will use the values provided 
        when creating this jws object.

        :param jwsobj:
            The JWS (header.paylaod.signature) to be hashed (optional)

        :param alg:
            The hashing algorithm to use ['RS256'(default), 'RS384', 'RS512'] (optional)
        """
        thealg = alg if alg else "RS256"
        thejws = jwsobj if jwsobj else self.jws
        return algs[thealg].new(thejws).hexdigest()

    def validate(self, stmt):
        """
        Validate the incoming Statement against the Statement in the JWS payload.

        :param stmt:
            String format of the Statement object to be validated
        """
        # free pass for those who don't use x5c
        if not self.should_verify:
            return True
        if type(stmt) != dict:
            stmtobj = json.loads(stmt)
        else:
            stmtobj = stmt
        atts = stmtobj.pop('attachments', None)
        if atts:
            atts = [a for a in atts if a.get('usageType',None) != "http://adlnet.gov/expapi/attachments/signature"]
            if atts:
                stmtobj['attachments'] = atts

        sortedstmt = json.dumps(stmtobj, sort_keys=True)
        sortedpayload = json.dumps(json.loads(self.payload), sort_keys=True)
        return sortedstmt == sortedpayload

    def _parseheader(self):
        if type(self.header) != dict:
            try:
                self.headerobj = json.loads(self.header)
            except:
                raise JWSException('JWS header was not valid JSON')
        else:
            try:
                self.headerobj = self.header
                self.header = json.dumps(self.header)
            except:
                raise JWSException('JWS header was not valid JSON')
        if 'alg' not in self.headerobj:
            raise JWSException('JWS header did not have an "alg" property')
        self.should_verify = 'x5c' in self.headerobj
        if self.should_verify:
            if type(self.headerobj['x5c']) != list:
                raise JWSException('x5c property was not an array of certificate value strings')

    def _parsejws(self):
        jwsparts = self.jws.split('.')
        if len(jwsparts) != 3:
            raise JWSException('The JWS was not formatted correctly - should be encodedheader.encodedpayload.encodedjwssignature')
        self.encheader = jwsparts[0]
        self.header = base64.urlsafe_b64decode(fixb64padding(self.encheader))
        self._parseheader()
        self.encpayload = jwsparts[1]
        self.payload = base64.urlsafe_b64decode(fixb64padding(self.encpayload))
        self.encjwssignature = jwsparts[2]
        self.jwssignature = base64.urlsafe_b64decode(fixb64padding(jwsparts[2]))

    def _hash(self):
        return algs[self.headerobj['alg']].new('.'.join([self.encheader,self.encpayload]).encode('ascii'))
        
    def _cert_to_key(self, cert):
        # Convert from PEM to DER
        if not cert.startswith('-----BEGIN CERTIFICATE-----') and not cert.endswith('-----END CERTIFICATE-----'):
            cert = "-----BEGIN CERTIFICATE-----\n%s\n-----END CERTIFICATE-----" % cert
        lines = cert.replace(" ",'').split()
        der = a2b_base64(''.join(lines[1:-1]))

        # Extract subjectPublicKeyInfo field from X.509 certificate (see RFC3280)
        cert = DerSequence()
        cert.decode(der)
        tbsCertificate = DerSequence()
        tbsCertificate.decode(cert[0])
        subjectPublicKeyInfo = tbsCertificate[6]

        # Initialize RSA key
        return RSA.importKey(subjectPublicKeyInfo)


class JWSException(Exception):
    """Generic exception class."""
    def __init__(self, message='JWS error occured.'):
        self.message = message
