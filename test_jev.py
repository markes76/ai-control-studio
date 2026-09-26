import unittest,tempfile,json
from pathlib import Path
from unittest.mock import patch
import jev, switch
class JevTests(unittest.TestCase):
 def test_clear_activity_persists_and_preserves_configuration(self):
  config=Path(self.tmp.name)/'config.json';config.write_text('{"model":"example","secretRef":"example"}')
  jev.STATUS.write_text('[{"operation":"Connection test"}]')
  with patch.object(jev,'CONFIG',config):
   result=jev.handle({'op':'jev-clear-activity'})
  self.assertTrue(result['ok'])
  self.assertEqual(json.loads(jev.STATUS.read_text()),[])
  self.assertEqual(json.loads(config.read_text()),{'model':'example','secretRef':'example'})
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.statusPatch=patch.object(jev,"STATUS",Path(self.tmp.name)/"status.json");self.statusPatch.start();self.addCleanup(self.statusPatch.stop)
 def test_activity_has_no_prompt_or_credential(self):
  import time
  jev.record_activity("Skill suggestion",time.monotonic(),{"suggestion":{"name":"PRIVATE"},"prompt":"SECRET", "confidence":.9})
  text=jev.STATUS.read_text();self.assertNotIn("SECRET",text);self.assertNotIn("PRIVATE",text);self.assertIn("local match",text)
 def test_two_stage(self):
  roster=[{'id':'s0','name':'review','description':'Review code','excerpt':'Review changes','path':'/sample','scope':'User','kind':'skills'}]
  calls=[]
  def call(state,questions,*args):
   calls.append(state)
   return {'skill':{'choice':'s0','confidence':.8}} if 'skill' in questions else {'fit':{'choice':'use','confidence':.9}}
  v=jev.suggest('review code',candidates=roster,call=call)
  self.assertEqual(v['suggestion']['name'],'review');self.assertEqual(len(calls),2)
 def test_fallback_and_no_private_query(self):
  calls=[]
  def search(topic):calls.append(topic);return {'candidates':[],'message':'None found.'}
  def call(*args):return {'skill':{'choice':'none','confidence':.9},'topic':{'choice':'security','confidence':.9}}
  roster=[{'id':'s0','name':'other','description':'Other','excerpt':'Other'}]
  with patch.object(jev,'config',return_value={'searchFallback':True}):
   result=jev.suggest('PRIVATE customer content',candidates=roster,call=call,search=search)
  self.assertEqual(calls,['security']);self.assertIn('discovery',result);self.assertNotIn('PRIVATE',jev.context(result))
 def test_no_search_when_disabled(self):
  with patch.object(jev,'config',return_value={'searchFallback':False}):
   result=jev.suggest('request',candidates=[],call=lambda *a:{'topic':{'choice':'general','confidence':.8}},search=lambda _:self.fail('Search disabled'))
  self.assertNotIn('discovery',result)
 def test_search_error_is_nonblocking(self):
  def broken(_):raise ValueError('Sign in again')
  result=jev.suggest('request',candidates=[],call=lambda *a:{'topic':{'choice':'general','confidence':.8}},search=broken)
  self.assertTrue(result['ok']);self.assertIn('searchError',result)
 def test_invalid_answer(self):
  with self.assertRaises(ValueError):jev.selected({'choice':'invented','confidence':.9},{'s0'})
 def test_preserves_settings_and_consent(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);settings=root/'.claude/settings.json';desktop=root/'desktop.json';settings.parent.mkdir()
   settings.write_text(json.dumps({'env':{'OTHER':'value'},'hooks':{'Stop':[{'hooks':[{'type':'command','command':'echo other'}]}]}}));desktop.write_text('{"mcpServers":{"existing":{"command":"other"}}}')
   with patch.object(Path,'home',return_value=root),patch.object(jev,'CONFIG',root/'jev.json'),patch.object(switch,'DESKTOP_SETTINGS',desktop),patch.object(switch,'back_up'):
    with self.assertRaises(ValueError):jev.save({'automatic':True})
    jev.save({'automatic':True,'consent':True,'desktop':True,'decisionSupport':True})
    jev.save({'automatic':True,'consent':True,'desktop':True,'decisionSupport':True})
    data=json.loads(settings.read_text());self.assertEqual(len(data['hooks']['UserPromptSubmit']),1);self.assertIn('Stop',data['hooks']);self.assertEqual(len(data['hooks']['PreToolUse']),1);self.assertEqual(len(data['hooks']['SessionStart']),1);self.assertIn(jev.SERVER,json.loads((root/'.claude.json').read_text())['mcpServers']);self.assertEqual(data['env'],{'OTHER':'value'})
    self.assertIn('existing',json.loads(desktop.read_text())['mcpServers'])
    jev.save({'automatic':False,'desktop':False,'decisionSupport':False})
    self.assertNotIn('UserPromptSubmit',json.loads(settings.read_text())['hooks']);self.assertIn('existing',json.loads(desktop.read_text())['mcpServers'])
if __name__=='__main__':unittest.main()
