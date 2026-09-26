import unittest,tempfile,json
from pathlib import Path
from unittest.mock import patch
import secret_store
class SecretReferencesTests(unittest.TestCase):
 def test_rejects_foreign_service(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'references.json';p.write_text(json.dumps([{'id':'custom','service':'ai-control-studio.secret.other'}]))
   with patch.object(secret_store,'REGISTRY',p):
    with self.assertRaises(ValueError):secret_store.entries()
 def test_oauth_cannot_be_read_as_api_key(self):
  with self.assertRaises(ValueError):secret_store.reference('claude-oauth')
 def test_missing_key_does_not_expose_stderr(self):
  from subprocess import CompletedProcess
  with patch.object(secret_store.subprocess,'run',return_value=CompletedProcess([],1,'','private diagnostic')):
   with self.assertRaisesRegex(ValueError,'Secret Manager'):secret_store.read('openrouter')
if __name__=='__main__':unittest.main()
