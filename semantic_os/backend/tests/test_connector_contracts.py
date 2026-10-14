import unittest
from pydantic import ValidationError
from semantic_os.backend.assistant.connector_contracts import PlatformOAuthApplication,CustomerConnectionConfig,RedactedConnection

class ConnectorContracts(unittest.TestCase):
    def test_customer_never_supplies_secret_tenant_or_unsupported_actions(self):
        valid={'provider':'google','actions':['availability'],'revision':1}
        config=CustomerConnectionConfig(**valid)
        self.assertIn('https://www.googleapis.com/auth/calendar.freebusy',config.consent_scopes())
        for extra in ({'client_secret':'bad'},{'tenant_id':'other'},{'actions':['contact_write']}):
            with self.assertRaises(ValidationError):CustomerConnectionConfig(**{**valid,**extra})
    def test_exact_platform_redirect_and_provider_secret_reference(self):
        uri='https://staging.example.invalid/backend/api/connectors/oauth/google/callback'
        valid={'provider':'google','client_id':'synthetic-id','secret_reference':'platform:oauth:google:client_secret','redirect_uri':uri,'allowed_redirects':[uri]}
        self.assertEqual(PlatformOAuthApplication(**valid).redirect_uri,uri)
        for extra in ({'redirect_uri':uri+'?code=bad'},{'allowed_redirects':['https://other.example.invalid']},{'secret_reference':'platform:oauth:hubspot:client_secret'}):
            with self.assertRaises(ValidationError):PlatformOAuthApplication(**{**valid,**extra})
    def test_offline_evidence_cannot_claim_live_connected(self):
        valid={'id':'synthetic','provider':'google','state':'connected','revision':1,'actions':['availability'],'verification':'OFFLINE_PASS'}
        with self.assertRaises(ValidationError):RedactedConnection(**valid)
        self.assertEqual(RedactedConnection(**{**valid,'state':'disconnected'}).verification,'OFFLINE_PASS')
