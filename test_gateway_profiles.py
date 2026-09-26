import unittest,tempfile,json
from pathlib import Path
from unittest.mock import patch
import gateway_profiles as gp
class OllamaProfilesTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.root=Path(self.tmp.name)
  self.p1=patch.object(gp,'ROOT',self.root);self.p2=patch.object(gp,'FILE',self.root/'profiles.json');self.p1.start();self.p2.start();self.addCleanup(self.p1.stop);self.addCleanup(self.p2.stop)
 def request(self):return {'op':'profile-save','name':'Ollama','kind':'Ollama','claudeUrl':'http://localhost:11434','codexUrl':'http://localhost:11434/v1','modelsUrl':'http://localhost:11434/v1/models','auth':'local','claudeModel':'example:latest'}
 def test_local_profile_helper_and_no_keychain(self):
  with patch('switch.inspect',return_value={'desktop_gateway':False,'code_gateway':False}),patch('switch.back_up'),patch('secret_store.read',side_effect=AssertionError('must not read keychain')):
   result=gp.handle(self.request());profile=result['profiles'][0]
   self.assertEqual(gp.token(profile),'ollama');self.assertEqual(profile['claudeModel'],'example:latest')
   self.assertNotIn('secretRef',profile)
 def test_existing_executable_helper_profiles_still_save(self):
  helper=self.root/'existing-helper.sh';helper.write_text('#!/bin/sh\nprintf %s example\n');helper.chmod(0o700)
  req=self.request();req.update(kind='Custom',auth='helper',helper=str(helper))
  with patch('switch.inspect',return_value={}),patch('switch.back_up'):
   result=gp.handle(req)
  self.assertEqual(result['profiles'][0]['helper'],str(helper))
 def test_local_auth_cannot_be_used_remotely(self):
  req=self.request();req['codexUrl']='https://example.com/v1'
  with patch('switch.inspect',return_value={}):
   with self.assertRaisesRegex(ValueError,'localhost'):gp.handle(req)
  self.assertFalse(gp.FILE.exists())
 def test_no_default_model_guess(self):
  req=self.request();req['claudeModel']=''
  with patch('switch.inspect',return_value={}):
   with self.assertRaisesRegex(ValueError,'exact Ollama model'):gp.handle(req)
 def test_desktop_requires_official_gateway_health_marker(self):
  from unittest.mock import MagicMock
  response=MagicMock();response.__enter__.return_value=response;response.status=200;response.headers={}
  with patch('gateway_profiles.urllib.request.urlopen',return_value=response):
   with self.assertRaisesRegex(ValueError,'11435'):gp.check_desktop_gateway('http://localhost:11434')
  response.status=204;response.headers={'X-Ollama-Claude-Gateway':'1'}
  with patch('gateway_profiles.urllib.request.urlopen',return_value=response):gp.check_desktop_gateway('http://127.0.0.1:11435')
 def test_discovery_refuses_remote_url(self):
  with self.assertRaises(ValueError):gp.ollama_models('https://example.com/v1/models')
class RoutingRoundTripTests(unittest.TestCase):
 def test_ollama_routes_restore_original_settings(self):
  import subprocess,os
  with tempfile.TemporaryDirectory() as home:
   script="""import gateway_profiles as gp,switch as r,codex_switch as c,json,importlib
r.CODE_SETTINGS.parent.mkdir(parents=True)
r.CODE_SETTINGS.write_text(json.dumps({'env':{'ANTHROPIC_MODEL':'previous'},'permissions':{'allow':[]}}))
gp.handle({'op':'profile-save','name':'Ollama','kind':'Ollama','claudeUrl':'http://localhost:11434','codexUrl':'http://localhost:11434/v1','auth':'local','claudeModel':'test:latest'})
importlib.reload(r);importlib.reload(c)
from unittest.mock import patch
with patch('gateway_profiles.check_desktop_gateway'):
 r.apply(True,True)
profile=json.loads(r.GATEWAY_PROFILE.read_text())
assert profile['inferenceGatewayApiKey']=='ollama'
assert profile['modelDiscoveryEnabled'] is True
with patch('gateway_profiles.check_desktop_gateway'):
 v=gp.handle({'op':'profile-save','name':'Ollama edited','kind':'Ollama','claudeUrl':'http://localhost:11434','codexUrl':'http://localhost:11434/v1','auth':'local','claudeModel':'test:latest','applyActive':True})
assert v['reloadTargets']==['desktop']
assert v['applied']['code_gateway']
with patch('gateway_profiles.check_desktop_gateway'):
 selected=gp.handle({'op':'profile-select','id':v['selected'],'applyActive':True})
assert selected['applied']['desktop_gateway']
assert selected['applied']['code_gateway']
assert selected['reloadTargets']==['desktop']
assert json.loads(r.PROFILE_META.read_text())['appliedId']==r.GATEWAY_PROFILE_ID
c.apply(True,'test:latest')
assert json.loads(r.CODE_SETTINGS.read_text())['env']['ANTHROPIC_MODEL']=='test:latest'
assert 'http://localhost:11434/v1' in c.CONFIG.read_text()
r.apply(False,False);c.apply(False,'')
assert json.loads(r.CODE_SETTINGS.read_text())['env']['ANTHROPIC_MODEL']=='previous'
assert json.loads(r.CODE_SETTINGS.read_text())['permissions']=={'allow':[]}
"""
   p=subprocess.run(['python3','-c',script],env=dict(os.environ,HOME=home),capture_output=True,text=True)
   self.assertEqual(p.returncode,0,p.stderr)
if __name__=='__main__':unittest.main()
